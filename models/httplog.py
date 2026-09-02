import math
import json
import logging
from datetime import datetime, timedelta
from urllib.parse import urlencode

from database import db
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.postgresql import JSONB

from util import statictext, util as Util

logger = logging.getLogger("worker")


class HttpLog(db.Model):
    """Outbound HTTP delivery log (Services -> HTTP, design slide 18).

    One row per payload sent to a station's HTTP service: queued the moment new
    station data arrives (StationData.ingest -> enqueue_for_station), delivered
    by the background worker (services/http_sender.py) which stores the full URL,
    request body, response code / body and retry attempts.
    Status: 0 Queue, 1 Sent (Success), 2 Failed (statictext.HttpLogStatuses).
    """

    __tablename__ = "tbl_httplog"

    STATUS_QUEUE = 0
    STATUS_SENT = 1
    STATUS_FAILED = 2

    sort = [
        {"column": "ID", "field": "ID", "dir": "desc"},
    ]

    searchFields = ["DeviceID", "URL"]

    ID = db.Column(db.Integer, primary_key=True)

    HttpID = db.Column(
        db.Integer,
        db.ForeignKey("tbl_http.ID", onupdate="CASCADE", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    StationID = db.Column(
        db.Integer,
        db.ForeignKey("tbl_station.StationID", onupdate="CASCADE", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    DeviceID = db.Column(db.String(100), index=True)

    Method = db.Column(db.String(10))
    URL = db.Column(db.Text)  # full URL as sent (query string included for GET)
    Request = db.Column(db.Text)  # request body as sent (POST / PUT)
    Content = db.Column(JSONB, nullable=True, default=dict)  # mapped payload
    ResponseCode = db.Column(db.Integer)
    Response = db.Column(db.Text)  # response body or transport error

    Attempts = db.Column(db.SmallInteger, default=0, nullable=False)
    NextAttempt = db.Column(db.DateTime)
    SentDate = db.Column(db.DateTime)
    Status = db.Column(db.SmallInteger, default=0, nullable=False)

    CreateDate = db.Column(db.DateTime)
    UpdateDate = db.Column(db.DateTime)

    http = db.relationship("Http")
    station = db.relationship("Station")

    # Worker queue scan: Status = Queue AND NextAttempt <= now.
    __table_args__ = (db.Index("ix_tbl_httplog_status_next", "Status", "NextAttempt"),)

    def __repr__(self):
        return f"<HttpLog {self.ID}:{self.DeviceID}:{self.Status}>"

    def serialize(self):
        data = {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }

        data["SiteName"] = self.station.SiteName if self.station else None
        data["StatusText"] = statictext.HttpLogStatuses.get(self.Status, {}).get("text")

        return data

    # ------------------------------------------------------------------ queue
    @classmethod
    def enqueue_for_station(cls, station, record):
        """Create one Queue row per enabled HTTP service of `station`, with the
        payload built from the service's Parameter Mapping and the freshly
        received StationData `record`. Never raises: a mapping problem in one
        service must not break the inbound request."""
        from models.http import Http

        now = datetime.now()
        created = 0

        services = Http.query.filter(
            Http.StationID == station.StationID, Http.Status == 1
        ).all()
        for service in services:
            request_cfg = (service.Meta or {}).get("Request") or {}
            if not isinstance(request_cfg, dict) or not request_cfg.get("status"):
                continue
            cfg = request_cfg.get("configs") or {}
            if not isinstance(cfg, dict):
                continue

            try:
                payload = Util.build_http_payload(
                    cfg.get("Mapping"), record.Raw, record.Data, now
                )
                method = (cfg.get("Method") or "post").lower()
                content_type = cfg.get("ContentType") or "json"

                url = service.URL or ""
                body = None
                if method == "get":
                    if payload:
                        url = url + ("&" if "?" in url else "?") + urlencode(payload)
                elif content_type == "json":
                    body = json.dumps(payload, ensure_ascii=False)
                else:
                    body = urlencode(payload)

                db.session.add(
                    cls(
                        HttpID=service.ID,
                        StationID=station.StationID,
                        DeviceID=station.DeviceID,
                        Method=method,
                        URL=url,
                        Request=body,
                        Content=payload,
                        Attempts=0,
                        NextAttempt=now,
                        Status=cls.STATUS_QUEUE,
                        CreateDate=now,
                        UpdateDate=now,
                    )
                )
                created += 1
            except Exception as e:
                logger.warning("HttpLog enqueue skipped (Http %s): %s", service.ID, e)

        if created:
            db.session.commit()

        return created

    def mark_sent(self, code, body):
        now = datetime.now()
        self.Attempts = (self.Attempts or 0) + 1
        self.ResponseCode = code
        self.Response = body
        self.Status = self.STATUS_SENT
        self.SentDate = now
        self.NextAttempt = None
        self.UpdateDate = now
        db.session.commit()

    def mark_attempt_failed(self, code, body, cfg):
        """Record a failed attempt; keep the row queued until the configured
        retries are used up (Attempts counts the first try as well)."""
        now = datetime.now()
        retry_attempts = Util.safe_int((cfg or {}).get("RetryAttempts"), 2)
        retry_delay = Util.safe_int((cfg or {}).get("RetryDelay"), 10)

        self.Attempts = (self.Attempts or 0) + 1
        self.ResponseCode = code
        self.Response = body
        self.UpdateDate = now

        if self.Attempts >= 1 + max(retry_attempts, 0):
            self.Status = self.STATUS_FAILED
            self.NextAttempt = None
        else:
            self.NextAttempt = now + timedelta(seconds=max(retry_delay, 1))

        db.session.commit()

    # ------------------------------------------------------------ class methods
    @classmethod
    def getData(cls, id):
        object = cls.query.filter(cls.ID == id).first()

        if object is None:
            return None

        return object.serialize()

    @staticmethod
    def _parse_date(value):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(str(value).strip(), fmt)
            except (TypeError, ValueError):
                continue
        return None

    @classmethod
    def _filtered_query(cls, params, include_status=True):
        """Shared filtering for list() and counters(): Status, StationID,
        DeviceID, ProjectID / RiverBasinID (via the station), DateFrom / DateTo
        (CreateDate, inclusive days) and free-text search."""
        from models.station import Station

        query = cls.query
        filters = params.get("filters") or {}
        search = params.get("search")

        if search:
            query = query.filter(
                db.or_(
                    *[getattr(cls, f).ilike(f"%{search}%") for f in cls.searchFields]
                )
            )

        if isinstance(filters, dict):
            if include_status and filters.get("Status") not in (None, ""):
                query = query.filter(
                    cls.Status == Util.safe_int(filters.get("Status"), -1)
                )

            for key in ("StationID", "HttpID", "DeviceID"):
                if filters.get(key) not in (None, ""):
                    value = filters.get(key)
                    query = query.filter(
                        getattr(cls, key).in_(value)
                        if isinstance(value, list)
                        else getattr(cls, key) == value
                    )

            if filters.get("ProjectID") or filters.get("RiverBasinID"):
                query = query.join(Station, Station.StationID == cls.StationID)
                if filters.get("ProjectID"):
                    query = query.filter(Station.ProjectID == filters.get("ProjectID"))
                if filters.get("RiverBasinID"):
                    query = query.filter(
                        Station.RiverBasinID == filters.get("RiverBasinID")
                    )

            date_from = (
                cls._parse_date(filters.get("DateFrom"))
                if filters.get("DateFrom")
                else None
            )
            date_to = (
                cls._parse_date(filters.get("DateTo"))
                if filters.get("DateTo")
                else None
            )
            if date_from:
                query = query.filter(cls.CreateDate >= date_from)
            if date_to:
                query = query.filter(cls.CreateDate < date_to + timedelta(days=1))

        return query

    @classmethod
    def counters(cls, params={}):
        """{status: count} for the current filters (status filter ignored) -
        the Queue / Sent / Failed tiles on the http logs page."""
        query = cls._filtered_query(params, include_status=False)
        rows = (
            query.with_entities(cls.Status, db.func.count(cls.ID))
            .group_by(cls.Status)
            .all()
        )
        result = {status: 0 for status in statictext.HttpLogStatuses}
        for status, count in rows:
            result[status] = count
        return result

    @classmethod
    def list(cls, params={}):
        total = cls.query.count()
        query = cls._filtered_query(params)

        page = params.get("page", None)
        size = params.get("size", None)
        sort = params.get("sort", []) or cls.sort

        filtered = query.count()

        order_clauses = []
        for s in sort:
            field = s.get("field")
            direction = s.get("dir", "asc").lower()
            if field and hasattr(cls, field):
                col = getattr(cls, field)
                order_clauses.append(col.asc() if direction == "asc" else col.desc())
        if order_clauses:
            query = query.order_by(*order_clauses)

        if size is None:
            arrayObj = query.all()
        else:
            if page is None:
                page = 1
            arrayObj = query.offset((page - 1) * size).limit(size).all()

        result = {
            "data": [object.serialize() for object in arrayObj],
            "sort": sort,
            "last_row": total,
            "last_page": math.ceil(filtered / size) if size else 1,
            "filtered": filtered,
        }

        return result

    @classmethod
    def fix_sequence(cls):
        try:
            # begin() commits on exit; connect() would roll the setval back, leaving the sequence unchanged.
            with db.engine.begin() as conn:
                conn.execute(text("""
                        SELECT setval(
                            pg_get_serial_sequence('tbl_httplog', 'ID'),
                            (SELECT MAX("ID") FROM "tbl_httplog")
                        )
                    """))
        except SQLAlchemyError as e:
            print(f"An error occurred while updating the sequence: {e}")
