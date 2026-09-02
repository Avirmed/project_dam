import math
import logging
from datetime import datetime, timedelta

from database import db
from sqlalchemy import text, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import contains_eager
from sqlalchemy.dialects.postgresql import JSONB

from util import statictext, util as Util


class StationData(db.Model):
    """One payload received by a station's REST API server (POST
    /api/inbound/<DeviceID>). `Data` holds the values after the station's
    Inbound Data Mapping was applied; `Raw` keeps the original payload."""

    __tablename__ = "tbl_station_data"

    sort = [
        {"column": "ID", "field": "ID", "dir": "desc"},
    ]

    searchFields = ["DeviceID"]

    ID = db.Column(db.Integer, primary_key=True)

    StationID = db.Column(
        db.Integer,
        db.ForeignKey("tbl_station.StationID", onupdate="CASCADE", ondelete="RESTRICT"),
        index=True,
        nullable=True,
    )
    DeviceID = db.Column(db.String(100), index=True)
    RecordTime = db.Column(db.DateTime, index=True)

    Data = db.Column(JSONB, nullable=True, default=dict)
    Raw = db.Column(JSONB, nullable=True, default=dict)

    CreateDate = db.Column(db.DateTime)

    station = db.relationship("Station")

    def __repr__(self):
        return f"<StationData {self.ID}:{self.DeviceID}>"

    def serialize(self):
        data = {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }

        data["SiteName"] = self.station.SiteName if self.station else None

        return data

    ################################ Class methods ################################

    @classmethod
    def getData(cls, id):
        object = cls.query.filter(cls.ID == id).first()

        if object is None:
            return None

        return object.serialize()

    @classmethod
    def ingest(cls, device_id, payload, remote_addr, scheme, headers):
        """Validate and store one inbound device payload.

        Enforces, in order: station lookup by DeviceID, API status switch,
        source allow-list (HTTP or HTTPS rule depending on `scheme`),
        authentication, JSON-object body, then applies the mapping and saves.
        Returns the usual {Result, Title, Message, Code[, Data]} result.
        """
        from models.station import Station

        jsonResult = {
            "Result": False,
            "Title": statictext.Messages["Title"],
            "Message": statictext.Messages["InvalidAccess"],
            "Code": 400,
        }

        station = Station.query.filter(Station.DeviceID == device_id).first()
        if station is None:
            jsonResult.update(
                {"Message": statictext.Messages["InboundStationNotFound"], "Code": 404}
            )
            return jsonResult

        api = (station.Meta or {}).get("API") or {}
        if not isinstance(api, dict) or not api.get("status"):
            jsonResult.update(
                {"Message": statictext.Messages["InboundDisabled"], "Code": 403}
            )
            return jsonResult

        cfg = api.get("configs") or {}
        if not isinstance(cfg, dict):
            cfg = {}

        if scheme == "https":
            mode, custom = cfg.get("HTTPS_Source"), cfg.get("HTTPS_Source_Custom")
        else:
            mode, custom = cfg.get("HTTP_Source"), cfg.get("HTTP_Source_Custom")

        if not Util.is_source_allowed(remote_addr, mode, custom):
            jsonResult.update(
                {"Message": statictext.Messages["InboundForbiddenSource"], "Code": 403}
            )
            return jsonResult

        if not Util.check_inbound_auth(cfg, headers):
            jsonResult.update(
                {"Message": statictext.Messages["InboundUnauthorized"], "Code": 401}
            )
            return jsonResult

        if not isinstance(payload, dict):
            jsonResult.update(
                {"Message": statictext.Messages["InboundInvalidPayload"], "Code": 400}
            )
            return jsonResult

        mapped = Util.apply_key_mapping(payload, cfg.get("Keys"))
        now = datetime.now()

        try:
            record = cls(
                StationID=station.StationID,
                DeviceID=device_id,
                RecordTime=now,
                Data=mapped,
                Raw=payload,
                CreateDate=now,
            )
            db.session.add(record)
            db.session.commit()

            # New data hit the DB: queue the station's outbound HTTP deliveries
            # (design slide 3). Delivery itself runs in the background worker.
            try:
                from models.httplog import HttpLog

                HttpLog.enqueue_for_station(station, record)
            except Exception as e:
                db.session.rollback()
                logging.getLogger("worker").warning("HttpLog enqueue failed: %s", e)

            jsonResult.update(
                {
                    "Result": True,
                    "Message": statictext.Messages["InboundReceived"],
                    "Code": 200,
                    "Data": {"ID": record.ID, "RecordTime": now, "Mapped": mapped},
                }
            )
        except Exception as e:
            db.session.rollback()
            cls.fix_sequence()

            error_code = 500
            jsonResult.update(
                {
                    "Message": f"{statictext.ResponseCode[error_code]}: {str(e)}",
                    "Code": error_code,
                }
            )

        return jsonResult

    @classmethod
    def latest_by_station(cls, station_ids):
        """Newest payload per station -> {StationID: StationData}. One query:
        max(RecordTime) per station joined back to the rows."""
        ids = [i for i in (station_ids or []) if i is not None]
        if not ids:
            return {}

        newest = (
            db.session.query(cls.StationID, func.max(cls.RecordTime).label("maxtime"))
            .filter(cls.StationID.in_(ids))
            .group_by(cls.StationID)
            .subquery()
        )
        rows = cls.query.join(
            newest,
            (cls.StationID == newest.c.StationID)
            & (cls.RecordTime == newest.c.maxtime),
        ).all()

        return {row.StationID: row for row in rows}

    @classmethod
    def evaluate_status(cls, meta, latest, timeout_minutes):
        """Public-site status for one station from its newest payload.

        Returns (WaterLevelType, WaterLevelData) where WaterLevelType indexes
        statictext.WaterLevelTypes: 0 normal, 1 warning, 2 critical, 3 no
        connection (no payload, or the newest one is older than
        `timeout_minutes`). Water level values are read from StationData.Data
        under statictext.StationDataKeys and compared with the station's
        StationConfigures thresholds (Point 1 -> *_UP, Point 2 -> *_DOWN);
        the worse of the two points wins.
        """
        if latest is None or latest.RecordTime is None:
            return 3, {}

        age = datetime.now() - latest.RecordTime
        data = latest.Data if isinstance(latest.Data, dict) else {}
        water_data = {"RecordTime": latest.RecordTime, "Values": data}

        if age > timedelta(minutes=max(int(timeout_minutes), 1)):
            return 3, water_data

        cfg = ((meta or {}).get("StationConfigures") or {}).get("configs") or {}
        keys = statictext.StationDataKeys
        checks = (
            (keys["WaterLevel"], "WARNING_UP", "CRITICAL_UP"),
            (keys["WaterLevel2"], "WARNING_DOWN", "CRITICAL_DOWN"),
        )

        level = 0
        for data_key, warning_key, critical_key in checks:
            value = Util.safe_float(data.get(data_key))
            if value is None:
                continue
            critical = Util.safe_float(cfg.get(critical_key))
            warning = Util.safe_float(cfg.get(warning_key))
            if critical is not None and value >= critical:
                level = max(level, 2)
            elif warning is not None and value >= warning:
                level = max(level, 1)

        return level, water_data

    @classmethod
    def list(cls, params={}):
        arrayObj = []
        query = cls.query
        total = query.count()

        page = params.get("page", None)
        size = params.get("size", None)
        sort = params.get("sort", [])
        search = params.get("search", None)
        filters = params.get("filters", {})
        joined_relations = set()

        if search:
            search_conditions = [
                getattr(cls, field).ilike(f"%{search}%")
                for field in cls.searchFields
                if hasattr(cls, field)
            ]
            if search_conditions:
                query = query.filter(db.or_(*search_conditions))

        if filters and isinstance(filters, dict):
            for key, value in filters.items():
                if hasattr(cls, key) and value not in [None, ""]:
                    col = getattr(cls, key)

                    if isinstance(value, list):
                        query = query.filter(col.in_(value))
                    else:
                        query = query.filter(col == value)

        filtered = query.count()

        if not sort:
            sort = cls.sort

        if sort:
            order_clauses = []
            for s in sort:
                field = s.get("field")
                direction = s.get("dir", "asc").lower()

                if not field:
                    continue

                if "__" in field:
                    parts = field.split("__")
                    rel_name = parts[0]
                    col_name = parts[1]

                    if hasattr(cls, rel_name.lower()):
                        rel_attr = getattr(cls, rel_name.lower())

                        if rel_name not in joined_relations:
                            query = query.outerjoin(rel_attr).options(
                                contains_eager(rel_attr)
                            )
                            joined_relations.add(rel_name)

                        target_model = rel_attr.property.mapper.class_
                        if hasattr(target_model, col_name):
                            col = getattr(target_model, col_name)
                            order_clauses.append(
                                col.asc() if direction == "asc" else col.desc()
                            )

                elif hasattr(cls, field):
                    col = getattr(cls, field)
                    order_clauses.append(
                        col.asc() if direction == "asc" else col.desc()
                    )

            if order_clauses:
                query = query.order_by(*order_clauses)

        if size is None:
            arrayObj = query.all()
        else:
            if page is None:
                page = 1
            arrayObj = query.offset((page - 1) * size).limit(size).all()

        result = {
            "data": [],
            "sort": sort,
            "last_row": total,
            "last_page": math.ceil(total / size) if size is not None else 1,
            "filtered": filtered,
        }

        for object in arrayObj:
            result["data"].append(object.serialize())

        return result

    @classmethod
    def fix_sequence(cls):
        try:
            # begin() commits on exit; connect() would roll the setval back, leaving the sequence unchanged.
            with db.engine.begin() as conn:
                conn.execute(text("""
                        SELECT setval(
                            pg_get_serial_sequence('tbl_station_data', 'ID'),
                            (SELECT MAX("ID") FROM "tbl_station_data")
                        )
                    """))
        except SQLAlchemyError as e:
            print(f"An error occurred while updating the sequence: {e}")
