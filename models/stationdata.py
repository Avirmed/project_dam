import math
from datetime import datetime

from database import db
from sqlalchemy import text
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
