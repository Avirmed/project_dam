import math
import logging
from datetime import datetime, timedelta

from database import db
from sqlalchemy import text, func, cast, case, Float
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.postgresql import JSONB

from util import statictext, util as Util, hydro


class StationData(db.Model):
    """One payload received by a station's REST API server (POST
    /api/inbound/<DeviceID>). `Data` holds the values after the station's
    Inbound Data Mapping was applied; `Raw` keeps the original payload."""

    __tablename__ = "tbl_station_data"

    # newest payload first (composite index StationID + RecordTime)
    sort = [
        {"column": "RecordTime", "field": "RecordTime", "dir": "desc"},
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

    # Time-series access pattern: one station, a time range / its newest row.
    __table_args__ = (
        db.Index("ix_tbl_station_data_station_time", "StationID", "RecordTime"),
    )

    def __repr__(self):
        return f"<StationData {self.ID}:{self.DeviceID}>"

    def serialize(self):
        data = {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }

        data["SiteName"] = self.station.SiteName if self.station else None
        data["SiteCode"] = self.station.SiteCode if self.station else None

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
        cls.apply_flow(station, mapped)
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
    def apply_flow(cls, station, mapped):
        """Discharge from the station's Flow sensor (design slide 9):
        FLOW = Area(WL) * k(WL) * VELOCITY, using the sensor's Profile and
        FLOW CAL. TABLE. Only fills FLOW when the device did not send one;
        AREA is stored alongside for traceability. Never raises."""
        keys = statictext.StationDataKeys
        if not isinstance(mapped, dict) or mapped.get(keys["Flow"]) not in (None, ""):
            return False
        try:
            sensor = station.flow_sensor()
            if sensor is None:
                return False
            flow_cfg = ((sensor.Meta or {}).get("Flow") or {}).get("configs") or {}
            result = hydro.compute_flow(
                flow_cfg.get("Profile"),
                flow_cfg.get("FlowCalcTable"),
                mapped.get(keys["WaterLevel"]),
                mapped.get(keys["Velocity"]),
            )
            if result is None:
                return False
            flow, area, _k = result
            mapped[keys["Flow"]] = f"{flow:.4f}"
            mapped[keys["Area"]] = f"{area:.4f}"
            return True
        except Exception as e:  # a bad table must never block the inbound request
            logging.getLogger("worker").warning("Flow computation skipped: %s", e)
            return False

    @classmethod
    def rain_accumulation(cls, station_id, days=1, now=None):
        """Rain (statictext.StationDataKeys["Rainfall"], per-payload amount)
        accumulated over `days` hydrological days ending at the last 07:00
        boundary (design front slide 8: "07:00 08/10 - 07:00 09/10").
        Returns {"days", "from", "to", "value"} (value None when no numeric rows)."""
        now = now or datetime.now()
        boundary = now.replace(hour=7, minute=0, second=0, microsecond=0)
        if now < boundary:
            boundary -= timedelta(days=1)
        start = boundary - timedelta(days=days)
        expr = cls.value_expr(statictext.StationDataKeys["Rainfall"])
        total = (
            db.session.query(func.sum(expr))
            .filter(
                cls.StationID == station_id,
                cls.RecordTime >= start,
                cls.RecordTime < boundary,
            )
            .scalar()
        )
        return {
            "days": days,
            "from": start,
            "to": boundary,
            "value": round(float(total), 2) if total is not None else None,
        }

    @classmethod
    def latest_rainfall(cls, station_id):
        """Time of the newest payload whose rain amount is > 0 (None when never)."""
        expr = cls.value_expr(statictext.StationDataKeys["Rainfall"])
        return (
            db.session.query(func.max(cls.RecordTime))
            .filter(cls.StationID == station_id, expr > 0)
            .scalar()
        )

    @classmethod
    def series_multi(cls, params, keys):
        """series() for several Data columns at once (Station Data chart):
        {"series": {key: {bucket, count, points}}, "bucket": <bucket of the
        first non-empty series>}. Every series uses the same requested bucket,
        so aggregated points line up on the time axis."""
        params = dict(params or {})
        filters = dict(params.get("filters") or {})
        bucket = str(params.get("bucket") or "auto").lower()
        out, common = {}, None
        for key in keys:
            filters["Parameter"] = key
            params["filters"] = filters
            if common is not None:
                params["bucket"] = common
            res = cls.series(params)
            if res["points"] and common is None and bucket == "auto":
                common = res["bucket"]  # lock the auto-chosen resolution for the rest
            out[key] = res
        return {
            "series": out,
            "bucket": common or (bucket if bucket != "auto" else None),
        }

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

    MAX_RAW_POINTS = 3000  # chart: raw values up to this many rows, else aggregated

    @classmethod
    def _parse_datetime(cls, value):
        """'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM[:SS]' -> datetime, None when invalid."""
        if isinstance(value, datetime):
            return value
        value = str(value or "").strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        return None

    @classmethod
    def time_range(cls, filters):
        """(from, to_exclusive) from the quick Range (statictext.StationDataRanges)
        or the DateFrom / DateTo filters; a date-only DateTo covers the whole day."""
        rng = str(filters.get("Range") or "").strip()
        seconds = (statictext.StationDataRanges.get(rng) or {}).get("seconds") or 0
        if seconds > 0:
            return datetime.now() - timedelta(seconds=seconds), None
        date_from = (
            cls._parse_datetime(filters.get("DateFrom"))
            if filters.get("DateFrom")
            else None
        )
        date_to = (
            cls._parse_datetime(filters.get("DateTo"))
            if filters.get("DateTo")
            else None
        )
        if date_to is not None and len(str(filters.get("DateTo")).strip()) <= 10:
            date_to = date_to + timedelta(days=1)
        return date_from, date_to

    @classmethod
    def value_expr(cls, key):
        """SQL expression for Data->>key as a float; NULL when the text is not
        numeric (device payloads may carry "-", "NaN" or empty strings)."""
        text_value = cls.Data[key].astext
        return case(
            (text_value.op("~")(r"^-?[0-9]+(\.[0-9]+)?$"), cast(text_value, Float)),
            else_=None,
        )

    @classmethod
    def _filtered_query(cls, params):
        """Shared filtering for list() / summary() / series(): StationID, DeviceID,
        ProjectID / RiverBasinID (via the station), the period (Range or
        DateFrom / DateTo on RecordTime), a numeric Parameter Min / Max window and
        the free-text search."""
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
            for key in ("StationID", "DeviceID"):
                value = filters.get(key)
                if value in (None, "", []):
                    continue
                col = getattr(cls, key)
                query = query.filter(
                    col.in_(value) if isinstance(value, list) else col == value
                )

            if filters.get("ProjectID") or filters.get("RiverBasinID"):
                query = query.join(Station, Station.StationID == cls.StationID)
                if filters.get("ProjectID"):
                    query = query.filter(Station.ProjectID == filters.get("ProjectID"))
                if filters.get("RiverBasinID"):
                    query = query.filter(
                        Station.RiverBasinID == filters.get("RiverBasinID")
                    )

            date_from, date_to = cls.time_range(filters)
            if date_from:
                query = query.filter(cls.RecordTime >= date_from)
            if date_to:
                query = query.filter(cls.RecordTime < date_to)

            key = str(filters.get("Parameter") or "").strip()
            low, high = Util.safe_float(filters.get("Min")), Util.safe_float(
                filters.get("Max")
            )
            if key and (low is not None or high is not None):
                expr = cls.value_expr(key)
                if low is not None:
                    query = query.filter(expr >= low)
                if high is not None:
                    query = query.filter(expr <= high)

        return query

    @classmethod
    def list(cls, params={}):
        query = cls._filtered_query(params)

        page = params.get("page", None)
        size = params.get("size", None)
        sort = params.get("sort", []) or cls.sort

        filtered = query.count()

        order_clauses = []
        for s in sort:
            field = s.get("field")
            direction = str(s.get("dir", "asc")).lower()
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
            "data": [row.serialize() for row in arrayObj],
            "sort": sort,
            "last_row": filtered,
            "last_page": math.ceil(filtered / size) if size else 1,
            "filtered": filtered,
        }

    @classmethod
    def summary(cls, params={}):
        """Tiles of the Station Data page for the current filters."""
        row = (
            cls._filtered_query(params)
            .with_entities(
                func.count(cls.ID),
                func.count(func.distinct(cls.StationID)),
                func.min(cls.RecordTime),
                func.max(cls.RecordTime),
            )
            .first()
        )
        return {
            "total": row[0] or 0,
            "stations": row[1] or 0,
            "first": row[2],
            "last": row[3],
        }

    @classmethod
    def series(cls, params={}):
        """Time series of one Data column for the chart: {parameter, bucket,
        count, points}. bucket = auto | raw | hour | day; auto keeps raw values
        up to MAX_RAW_POINTS rows, then hourly, then daily averages (with
        min / max / n per bucket). Needs a single StationID filter."""
        filters = params.get("filters") or {}
        key = str(
            filters.get("Parameter") or statictext.StationDataKeys["WaterLevel"]
        ).strip()
        bucket = str(params.get("bucket") or "auto").lower()
        station = filters.get("StationID")
        if isinstance(station, list):
            station = station[0] if len(station) == 1 else None
        result = {"parameter": key, "bucket": None, "count": 0, "points": []}
        if station in (None, "", -1):
            return result

        query = cls._filtered_query(params)
        expr = cls.value_expr(key)
        count = query.filter(expr.isnot(None)).count()
        result["count"] = count
        if bucket not in statictext.StationDataBuckets or bucket == "auto":
            bucket = (
                "raw"
                if count <= cls.MAX_RAW_POINTS
                else ("hour" if count <= cls.MAX_RAW_POINTS * 24 else "day")
            )
        result["bucket"] = bucket

        if bucket == "raw":
            rows = (
                query.with_entities(cls.RecordTime, expr)
                .filter(expr.isnot(None))
                .order_by(cls.RecordTime.asc())
                .limit(cls.MAX_RAW_POINTS)
                .all()
            )
            result["points"] = [{"t": t, "v": v} for t, v in rows]
        else:
            slot = func.date_trunc(bucket, cls.RecordTime).label("slot")
            rows = (
                query.with_entities(
                    slot,
                    func.avg(expr),
                    func.min(expr),
                    func.max(expr),
                    func.count(expr),
                )
                .filter(expr.isnot(None))
                .group_by(slot)
                .order_by(slot.asc())
                .all()
            )
            result["points"] = [
                {"t": t, "v": round(float(avg), 4), "min": lo, "max": hi, "n": n}
                for t, avg, lo, hi, n in rows
            ]
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
