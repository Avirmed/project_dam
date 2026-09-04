import os
import math
import time
import shutil
import hashlib
import json
from datetime import datetime

from flask_login import current_user

from database import db
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import contains_eager
from sqlalchemy.dialects.postgresql import JSONB

from util import statictext, util as Util


class Station(db.Model):
    __tablename__ = "tbl_station"

    drfFilePath = os.path.join(statictext.APP_STATIC_PATH, "data", "station")
    filePath = os.path.join("/static", "data", "station")
    img_size = {
        "lg": {"width": None, "height": 800, "fldr": "md"},
        "md": {"width": None, "height": 400, "fldr": "md"},
        "sm": {"width": None, "height": 100, "fldr": "sm"},
    }

    sort = [
        {"column": "Project__SortOrder", "field": "Project__SortOrder", "dir": "asc"},
        {
            "column": "RiverBasin__SortOrder",
            "field": "RiverBasin__SortOrder",
            "dir": "asc",
        },
        {"column": "SiteCode", "field": "SiteCode", "dir": "asc"},
    ]

    searchFields = ["SiteCode", "SiteName", "Address"]

    required_fields = ["ProjectID", "RiverBasinID", "SiteCode", "SiteName"]

    StationID = db.Column(db.Integer, primary_key=True)

    ProjectID = db.Column(
        db.Integer,
        db.ForeignKey("tbl_project.ProjectID", onupdate="CASCADE", ondelete="RESTRICT"),
        index=True,
        nullable=True,
    )
    RiverBasinID = db.Column(
        db.Integer,
        db.ForeignKey(
            "tbl_riverbasin.RiverBasinID", onupdate="CASCADE", ondelete="RESTRICT"
        ),
        index=True,
        nullable=True,
    )
    Region = db.Column(db.SmallInteger, default=1, nullable=False)

    SiteCode = db.Column(db.String(100), nullable=False)
    SiteName = db.Column(db.String(250), nullable=False)
    DeviceID = db.Column(db.String(100), nullable=False)
    SiteInstall = db.Column(db.SmallInteger, default=1, nullable=False)
    MeasuredValue = db.Column(db.SmallInteger, default=1, nullable=False)

    Address = db.Column(db.String(500))
    Latitude = db.Column(db.String(100))
    Longitude = db.Column(db.String(100))
    Zoom = db.Column(db.SmallInteger, default=6)

    Meta = db.Column(JSONB, nullable=True, default=dict)

    Status = db.Column(db.SmallInteger, default=1, nullable=False)
    ImageSource = db.Column(db.String(250))
    Remark = db.Column(db.Text)

    CreateUserID = db.Column(db.Integer)
    CreateDate = db.Column(db.DateTime)
    UpdateUserID = db.Column(db.Integer)
    UpdateDate = db.Column(db.DateTime)

    project = db.relationship("Project", back_populates="project_station")
    riverbasin = db.relationship("RiverBasin", back_populates="riverbasin_station")

    def __repr__(self):
        return f"<Station {self.StationID}:{self.SiteCode}-{self.SiteName}>"

    @classmethod
    def data_folder_for(cls, site_code):
        """Private RTU Data/<SiteCode> folder of a station (statictext.APP_DATA_PATH);
        cameras without a station use RTU Data/_unassigned. Not created here."""
        import re

        code = re.sub(r"[\/:*?\"<>|]", "_", str(site_code or "").strip())
        return os.path.join(
            statictext.APP_DATA_PATH, code or statictext.APP_DATA_UNASSIGNED_DIR
        )

    def data_folder(self):
        return self.data_folder_for(self.SiteCode)

    def flow_sensor(self):
        """The Flow sensor mapped on the Water configures tab ("Flow Rate" row:
        checked + text = SensorID code or numeric ID), or None."""
        from models.sensor import Sensor

        block = (self.Meta or {}).get("WaterConfigures") or {}
        cfg = block.get("configs") if isinstance(block, dict) else None
        entry = cfg.get("FlowRate") if isinstance(cfg, dict) else None
        if not isinstance(entry, dict) or not entry.get("checked"):
            return None
        code = str(entry.get("text") or "").strip()
        if not code:
            return None
        sensor = Sensor.query.filter(Sensor.SensorID == code).first()
        if sensor is None and code.isdigit():
            sensor = Sensor.query.get(int(code))
        return sensor

    @classmethod
    def live_status(cls, requestData):
        """Active stations in the current user's scope with their live status:
        each row gets WaterLevelType / WaterLevelData from its newest inbound
        payload (StationData.evaluate_status; older than DATA_TIMEOUT_MINUTES
        = "No connection"). Used by the public map (/api/stations/sites) and
        the dashboard overview (/main/summary)."""
        from models.settings import Settings
        from models.stationdata import StationData
        from models.team import Team

        requestData = dict(requestData or {})
        if not isinstance(requestData.get("filters"), dict):
            requestData["filters"] = {}
        requestData["filters"]["Status"] = 1

        # Staff / Guest only see their teams' stations (fail-closed without a team).
        Team.apply_station_scope(requestData)

        jsonResult = cls.list(requestData)

        timeout_minutes = Util.safe_int(
            Settings.load_settings().get("DATA_TIMEOUT_MINUTES"),
            statictext.DATA_TIMEOUT_MINUTES,
        )
        latest = StationData.latest_by_station(
            [row["StationID"] for row in jsonResult["data"]]
        )
        for row in jsonResult["data"]:
            row["WaterLevelType"], row["WaterLevelData"] = StationData.evaluate_status(
                row.get("Meta"), latest.get(row["StationID"]), timeout_minutes
            )
            # The map is public: never ship the station configuration (REST API
            # credentials, FTP settings) to the browser - thresholds are applied here.
            row.pop("Meta", None)
        # server clock: the browser computes "x ago" against it (time zones differ)
        jsonResult["generated_at"] = datetime.now()
        return jsonResult

    @classmethod
    def public_detail(cls, station_id):
        """Everything the public station page shows (front design slide 8):
        identity, specifications (Point 1 / 2 thresholds), the newest measured
        values with their status, and rain accumulated over 1 / 2 / 3 days.
        None when the station does not exist / is inactive."""
        from models.settings import Settings
        from models.stationdata import StationData

        station = cls.query.filter(cls.StationID == station_id, cls.Status == 1).first()
        if station is None:
            return None

        meta = station.Meta or {}
        configures = (meta.get("StationConfigures") or {}).get("configs") or {}
        timeout_minutes = Util.safe_int(
            Settings.load_settings().get("DATA_TIMEOUT_MINUTES"),
            statictext.DATA_TIMEOUT_MINUTES,
        )
        latest = StationData.latest_by_station([station.StationID]).get(
            station.StationID
        )
        level, water_data = StationData.evaluate_status(meta, latest, timeout_minutes)
        keys = statictext.StationDataKeys

        values = (water_data or {}).get("Values") or {}
        return {
            "StationID": station.StationID,
            "SiteCode": station.SiteCode,
            "SiteName": station.SiteName,
            "DeviceID": station.DeviceID,
            "ProjectName": station.project.ProjectName if station.project else None,
            "WatershedName": (
                station.riverbasin.WatershedName if station.riverbasin else None
            ),
            "Region": statictext.Regions.get(station.Region),
            "SiteInstall": statictext.SiteInstalls.get(station.SiteInstall),
            "MeasuredValue": statictext.MeasuredValues.get(station.MeasuredValue),
            "Address": station.Address,
            "Latitude": station.Latitude,
            "Longitude": station.Longitude,
            "Image": station.getImage("lg"),
            "ImageMD": station.getImage("md"),
            "Specifications": {
                key: configures.get(key)
                for block in statictext.StationConfigures
                for key in block.get("fields", {})
            },
            "WaterLevelType": level,
            "RecordTime": (water_data or {}).get("RecordTime"),
            "Values": {
                "WaterLevel": values.get(keys["WaterLevel"]),
                "WaterLevel2": values.get(keys["WaterLevel2"]),
                "FlowRate": values.get(keys["Flow"]),
                "Velocity": values.get(keys["Velocity"]),
                "Rainfall": values.get(keys["Rainfall"]),
            },
            "RainAccumulation": [
                StationData.rain_accumulation(station.StationID, days)
                for days in (1, 2, 3)
            ],
            "LatestRainfall": StationData.latest_rainfall(station.StationID),
        }

    @classmethod
    def with_cameras(cls, requestData):
        """Active stations in scope, each with its enabled cameras (matched by
        Camera.Meta.CameraConfigures.configs.StationID), for the CCTV page.
        Only public camera fields are returned (no stream / ISAPI credentials).
        filters: ProjectID, RiverBasinID, Region, CameraType; search."""
        from models.camera import Camera

        requestData = dict(requestData or {})
        filters = (
            requestData.get("filters")
            if isinstance(requestData.get("filters"), dict)
            else {}
        )
        camera_type = str(filters.pop("CameraType", "") or "").strip()
        requestData["filters"] = filters
        stations = cls.live_status(requestData)["data"]

        by_station = {}
        for camera in (
            Camera.query.filter(Camera.Status == 1).order_by(Camera.CameraID).all()
        ):
            cfg = camera.configs()
            station_id = Util.safe_int(cfg.get("StationID"), None)
            if station_id is None:
                continue
            if camera_type and str(cfg.get("CameraType") or "") != camera_type:
                continue
            snap = camera.snapshot()
            by_station.setdefault(station_id, []).append(
                {
                    "ID": camera.ID,
                    "CameraID": camera.CameraID,
                    "CameraName": camera.CameraName,
                    "CameraType": cfg.get("CameraType"),
                    "CameraTypeText": statictext.CameraTypes.get(
                        cfg.get("CameraType"), cfg.get("CameraType")
                    ),
                    "CCTV_NO": cfg.get("CCTV_NO"),
                    "SnapshotImage": snap["SnapshotImage"],
                    "SnapshotStill": snap["SnapshotStill"],
                    "SnapshotTime": snap["SnapshotTime"],
                }
            )

        rows = []
        for st in stations:
            cameras = by_station.get(st["StationID"], [])
            if camera_type and not cameras:
                continue
            rows.append(
                {
                    "StationID": st["StationID"],
                    "SiteCode": st["SiteCode"],
                    "SiteName": st["SiteName"],
                    "WatershedName": st.get("WatershedName"),
                    "ProjectName": st.get("ProjectName"),
                    "WaterLevelType": st.get("WaterLevelType"),
                    "RecordTime": (st.get("WaterLevelData") or {}).get("RecordTime"),
                    "Image": st.get("ImageMD"),
                    "Cameras": cameras,
                    "SnapshotTime": max(
                        (c["SnapshotTime"] for c in cameras if c["SnapshotTime"]),
                        default=None,
                    ),
                }
            )
        rows.sort(
            key=lambda r: (
                str(r.get("WatershedName") or ""),
                str(r.get("SiteCode") or ""),
            )
        )
        return rows

    def serialize(self):
        data = {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }

        data["ProjectName"] = self.project.ProjectName if self.project else None
        data["Project__SortOrder"] = self.project.SortOrder if self.project else None
        data["WatershedName"] = (
            self.riverbasin.WatershedName if self.riverbasin else None
        )
        data["RiverBasin__SortOrder"] = (
            self.riverbasin.SortOrder if self.riverbasin else None
        )
        data["Image"] = self.getImage()
        data["ImageMD"] = self.getImage("md")
        data["ImageLG"] = self.getImage("lg")

        return data

    def getImage(self, size="sm"):
        if self.ImageSource is not None and self.ImageSource != "":
            image_path = os.path.join(self.filePath, size, self.ImageSource)

            if os.path.exists(os.path.join(self.drfFilePath, size, self.ImageSource)):
                return image_path

        return statictext.Images["Blank"]

    def updateImage(self, filename):
        self.deleteImage()

        source_path = os.path.join(self.drfFilePath, filename)
        for size in self.img_size:
            dest_path = os.path.join(self.drfFilePath, size, filename)
            Util.cropImage(
                self.img_size[size]["width"],
                self.img_size[size]["height"],
                source_path,
                dest_path,
            )

        try:
            os.remove(source_path)
        except Exception as e:
            print(f"Error deleting image: {source_path} -> {e}")

        self.ImageSource = filename
        self.UpdateUserID = current_user.UserID
        self.UpdateDate = db.func.now()
        db.session.commit()

    def rotateImage(self, direction):
        if self.ImageSource:
            file_real_name = self.ImageSource

            file_ext = os.path.splitext(file_real_name)[1].lstrip(".")
            upload_time = time.time()

            hash_str = hashlib.md5(
                (file_real_name + str(upload_time)).encode()
            ).hexdigest()
            filename = f"{upload_time}_{hash_str}.{file_ext}"

            for size in self.img_size:
                source_path = os.path.join(self.drfFilePath, size, self.ImageSource)

                dest_path = os.path.join(self.drfFilePath, size, filename)

                try:
                    Util.rotateImage(source_path, dest_path, direction)
                    os.remove(source_path)
                except Exception as e:
                    print(f"Error deleting image: {source_path} -> {e}")

            self.ImageSource = filename
            db.session.commit()

        return self.serialize()

    def deleteImage(self):
        if self.ImageSource:
            for size in self.img_size:
                image_path = os.path.join(self.drfFilePath, size, self.ImageSource)
                if os.path.exists(image_path):
                    try:
                        os.remove(image_path)
                    except Exception as e:
                        print(f"Error deleting image: {image_path} -> {e}")
                        return False

            self.ImageSource = None
            db.session.commit()

        return True

    def remove(self, commit=True):
        if not self.deleteImage():
            return False

        cert_dir = os.path.join(statictext.APP_CERT_PATH, str(self.StationID))

        try:
            db.session.delete(self)
            if commit:
                db.session.commit()
        except Exception as e:
            db.session.rollback()
            return False

        # Only after the row is gone: drop the station's TLS certificate folder.
        shutil.rmtree(cert_dir, ignore_errors=True)
        return True

    ################################ Class methods ################################

    @classmethod
    def getData(cls, id):
        object = cls.query.filter(cls.StationID == id).first()

        if object is None:
            return None

        return object.serialize()

    @classmethod
    def _parse_json_fields(cls, params):
        jsonb_fields = {
            col.name
            for col in cls.__table__.columns
            if isinstance(col.type, (db.JSON, JSONB))  # хоёуланг тодорхой заана
        }

        for field in jsonb_fields:
            if field in params and isinstance(params[field], str):
                try:
                    params[field] = json.loads(params[field])
                except (json.JSONDecodeError, ValueError):
                    params[field] = None

        return params

    @classmethod
    def save(cls, params={}):
        jsonResult = {
            "Result": False,
            "Title": statictext.Messages["Title"],
            "Message": statictext.Messages["InvalidAccess"],
            "Code": 400,
        }

        if not params:
            error_code = 400

            jsonResult.update(
                {"Message": statictext.ResponseCode[error_code], "Code": error_code}
            )

            return jsonResult

        missing_fields = [
            field
            for field in cls.required_fields
            if field not in params or not str(params[field]).strip()
        ]

        if missing_fields:
            error_code = 422

            jsonResult.update(
                {"Message": statictext.ResponseCode[error_code], "Code": error_code}
            )

            return jsonResult

        params = cls._parse_json_fields(params)

        # REST API Server settings must be coherent before they are stored.
        meta = params.get("Meta")
        if isinstance(meta, dict) and "API" in meta:
            api_error = Util.validate_api_config(meta.get("API"))
            if api_error:
                jsonResult.update(
                    {"Message": statictext.Messages[api_error], "Code": 422}
                )
                return jsonResult

        params.pop("ImageSource", None)

        objID = params.get("StationID")
        deleteimage = params.get("deleteimage", False)

        try:
            object = None
            resultMsg = jsonResult["Message"]

            if objID:  # Update
                object = cls.query.get(objID)

                if not object:
                    error_code = 404

                    jsonResult.update(
                        {
                            "Message": statictext.ResponseCode[error_code],
                            "Code": error_code,
                        }
                    )

                    return jsonResult

                for key, value in params.items():
                    if hasattr(object, key):
                        new_value = value.strip() if isinstance(value, str) else value
                        new_value = None if new_value == "" else new_value
                        old_value = getattr(object, key)

                        if isinstance(old_value, (list, dict)):
                            if old_value != new_value:
                                setattr(object, key, new_value)
                        elif str(old_value) != str(new_value):
                            setattr(object, key, new_value)

                if deleteimage:
                    object.deleteImage()

                object.UpdateUserID = current_user.UserID
                object.UpdateDate = db.func.now()

                db.session.commit()
                resultMsg = statictext.Messages["SuccessUpdated"]

            else:  # Insert
                object_fields = {col.name for col in cls.__table__.columns}
                new_data = {
                    k: (v.strip() if isinstance(v, str) else v)
                    for k, v in params.items()
                    if k in object_fields
                    and v not in [None, ""]
                    and (v.strip() if isinstance(v, str) else v) not in [None, ""]
                }

                object = cls(**new_data)
                object.CreateUserID = current_user.UserID
                object.CreateDate = db.func.now()

                db.session.add(object)
                db.session.commit()
                resultMsg = statictext.Messages["SuccessCreated"]

            jsonResult.update(
                {
                    "Result": True,
                    "Data": object.serialize(),
                    "Message": resultMsg,
                    "Code": 200,
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
    def delete(cls, params={}):
        jsonResult = {
            "Result": False,
            "Title": statictext.Messages["Title"],
            "Message": statictext.Messages["InvalidAccess"],
            "Code": 400,
        }

        objID = params.get("StationID")
        if not objID:
            error_code = 400
            jsonResult.update(
                {
                    "Message": f"{statictext.ResponseCode[error_code]}",
                    "Code": error_code,
                }
            )
            return jsonResult

        try:
            object = cls.query.get(objID)

            if not object:
                jsonResult.update(
                    {"Message": statictext.Messages["InvalidAccess"], "Code": 404}
                )
                return jsonResult

            if object.remove():
                jsonResult.update(
                    {
                        "Result": True,
                        "Message": statictext.Messages["SuccessDeleted"],
                        "Code": 200,
                    }
                )
            else:
                error_code = 500
                jsonResult.update(
                    {
                        "Message": statictext.Messages["UnsuccessDeleted"],
                        "Code": error_code,
                    }
                )

        except Exception as e:
            db.session.rollback()

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
                        rel_attr = getattr(cls, rel_name.lower())  # cls.project

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
            objData = object.serialize()
            objData["Remark"] = Util.strip_html(object.Remark) if object.Remark else ""

            result["data"].append(objData)

        return result

    @classmethod
    def fix_sequence(cls):
        try:
            # begin() commits on exit; connect() would roll the setval back, leaving the sequence unchanged.
            with db.engine.begin() as conn:
                conn.execute(text("""
                        SELECT setval(
                            pg_get_serial_sequence('tbl_station', 'StationID'),
                            (SELECT MAX("StationID") FROM "tbl_station")
                        )
                    """))
        except SQLAlchemyError as e:
            print(f"An error occurred while updating the sequence: {e}")
