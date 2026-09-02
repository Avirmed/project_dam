import os
import math
from datetime import datetime, timedelta

from database import db
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from util import statictext, util as Util


class EventLog(db.Model):
    """Security camera events (design slide 10 / public Event Log page).

    Rows are created by the worker (services/event_watcher.py) from image files
    that Security CCTVs drop into the watch folder, named
    <IP>_<channel>_<yyyymmddHHMMSS[ms]>_<EVENT>.jpg. The image is moved under
    static/data/events/ and an operator approves / rejects the event.
    Status: 0 pending, 1 approve, 2 reject (statictext.EventLogStatuses).
    """

    __tablename__ = "tbl_eventlog"

    # Event images: stored under drfFilePath/<yyyymm>/, served from filePath
    # (same pattern as Station.drfFilePath / filePath).
    drfFilePath = os.path.join(statictext.APP_STATIC_PATH, "data", "events")
    filePath = "/static/data/events"

    STATUS_PENDING = 0
    STATUS_APPROVE = 1
    STATUS_REJECT = 2

    sort = [
        {"column": "EventTime", "field": "EventTime", "dir": "desc"},
    ]

    searchFields = ["Event", "IP", "Filename"]

    ID = db.Column(db.Integer, primary_key=True)

    CameraID = db.Column(
        db.Integer,
        db.ForeignKey("tbl_camera.ID", onupdate="CASCADE", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    StationID = db.Column(
        db.Integer,
        db.ForeignKey("tbl_station.StationID", onupdate="CASCADE", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    IP = db.Column(db.String(50), index=True)
    Channel = db.Column(db.String(10))
    EventTime = db.Column(db.DateTime, index=True)
    Event = db.Column(db.String(100))
    Filename = db.Column(db.String(250), unique=True)
    ImageSource = db.Column(db.String(250))  # path relative to static/data/events

    Status = db.Column(db.SmallInteger, default=0, nullable=False)
    Remark = db.Column(db.Text)

    CreateDate = db.Column(db.DateTime)
    UpdateUserID = db.Column(db.Integer)
    UpdateDate = db.Column(db.DateTime)

    camera = db.relationship("Camera")
    station = db.relationship("Station")

    def __repr__(self):
        return f"<EventLog {self.ID}:{self.Event}>"

    def serialize(self):
        data = {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }

        data["CameraName"] = self.camera.CameraName if self.camera else None
        data["SiteName"] = self.station.SiteName if self.station else None
        data["SiteCode"] = self.station.SiteCode if self.station else None
        data["WatershedName"] = (
            self.station.riverbasin.WatershedName
            if self.station and self.station.riverbasin
            else None
        )
        data["Image"] = (
            f"{self.filePath}/{self.ImageSource}"
            if self.ImageSource
            else statictext.Images["Blank"]
        )
        data["StatusText"] = statictext.EventLogStatuses.get(self.Status, {}).get(
            "text"
        )

        return data

    ################################ Class methods ################################

    @classmethod
    def getData(cls, id):
        object = cls.query.filter(cls.ID == id).first()

        if object is None:
            return None

        return object.serialize()

    @classmethod
    def set_status(cls, params, user_id=None):
        """Approve / reject one event (public Event Log page action)."""
        jsonResult = {
            "Result": False,
            "Title": statictext.Messages["Title"],
            "Message": statictext.Messages["InvalidAccess"],
            "Code": 400,
        }

        object = cls.query.get(Util.safe_int(params.get("ID"), 0))
        status = Util.safe_int(params.get("Status"), -1)
        if object is None or status not in statictext.EventLogStatuses:
            jsonResult.update({"Message": statictext.ResponseCode[404], "Code": 404})
            return jsonResult

        try:
            object.Status = status
            object.UpdateUserID = user_id
            object.UpdateDate = datetime.now()
            if params.get("Remark") is not None:
                object.Remark = str(params.get("Remark"))
            db.session.commit()
            jsonResult.update(
                {
                    "Result": True,
                    "Data": object.serialize(),
                    "Message": statictext.Messages["EventUpdated"],
                    "Code": 200,
                }
            )
        except Exception as e:
            db.session.rollback()
            jsonResult.update(
                {"Message": f"{statictext.ResponseCode[500]}: {str(e)}", "Code": 500}
            )

        return jsonResult

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

            for key in ("StationID", "CameraID"):
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
                query = query.filter(cls.EventTime >= date_from)
            if date_to:
                query = query.filter(cls.EventTime < date_to + timedelta(days=1))

        return query

    @classmethod
    def counters(cls, params={}):
        query = cls._filtered_query(params, include_status=False)
        rows = (
            query.with_entities(cls.Status, db.func.count(cls.ID))
            .group_by(cls.Status)
            .all()
        )
        result = {status: 0 for status in statictext.EventLogStatuses}
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

        return {
            "data": [object.serialize() for object in arrayObj],
            "sort": sort,
            "last_row": total,
            "last_page": math.ceil(filtered / size) if size else 1,
            "filtered": filtered,
        }

    @classmethod
    def fix_sequence(cls):
        try:
            # begin() commits on exit; connect() would roll the setval back, leaving the sequence unchanged.
            with db.engine.begin() as conn:
                conn.execute(text("""
                        SELECT setval(
                            pg_get_serial_sequence('tbl_eventlog', 'ID'),
                            (SELECT MAX("ID") FROM "tbl_eventlog")
                        )
                    """))
        except SQLAlchemyError as e:
            print(f"An error occurred while updating the sequence: {e}")
