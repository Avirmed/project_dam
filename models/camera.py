import os
import math
import json

from flask_login import current_user

from database import db
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import contains_eager
from sqlalchemy.dialects.postgresql import JSONB

from util import statictext, util as Util


class Camera(db.Model):
    __tablename__ = "tbl_camera"

    # Worker folders (deployment constants, same pattern as Station.drfFilePath).
    # Private, per camera, under the station's RTU Data folder (see
    # statictext.APP_DATA_PATH; data_folder() below):
    #   images/       snapshot archive  (services/snapshot.py)
    #   images_temp/  1..N.jpg frames of the AI worker's RTSP clip
    #   raw_temp/     that clip (raw.mp4 + raw.json), overwritten each run
    #   images_out/   images to send via the camera's Upload JPG (FTP) settings
    #                 (services/image_uploader.py)
    # Security CCTVs drop event snapshots into the shared eventWatchPath
    # (services/event_watcher.py).
    eventWatchPath = os.path.join(
        statictext.APP_DATA_PATH, statictext.APP_DATA_SECURITY_DIR
    )
    # Public: <snapshotPath>/<CameraID>/image.gif (animation of images_temp) and
    # image.jpg (newest picture) for the front CCTV page and the camera form.
    snapshotPath = os.path.join(statictext.APP_STATIC_PATH, "data", "cameras")
    snapshotUrl = "/static/data/cameras"
    snapshotGif = "image.gif"
    snapshotStill = "image.jpg"
    # Trained YOLO weights for the AI water-level detector (ai/detect.py):
    # <modelPath>/<CameraID>.pt, uploaded from the camera form; the file name is
    # kept in Meta.CameraConfigures.configs.TrainedModel. Not web-served.
    modelPath = statictext.APP_MODEL_PATH

    sort = [
        {"column": "CameraID", "field": "CameraID", "dir": "asc"},
        {"column": "CameraName", "field": "CameraName", "dir": "asc"},
    ]

    searchFields = ["CameraID", "CameraName"]

    required_fields = ["CameraID", "CameraName"]

    ID = db.Column(db.Integer, primary_key=True)

    CameraID = db.Column(db.String(100), nullable=False)
    CameraName = db.Column(db.String(250), nullable=False)

    Meta = db.Column(JSONB, nullable=True, default=dict)

    Status = db.Column(db.SmallInteger, default=1, nullable=False)
    Remark = db.Column(db.Text)

    # Outcome of the last image upload run (services/image_uploader.py)
    LastUploadRun = db.Column(db.DateTime)
    LastUploadResult = db.Column(db.String(500))

    CreateUserID = db.Column(db.Integer)
    CreateDate = db.Column(db.DateTime)
    UpdateUserID = db.Column(db.Integer)
    UpdateDate = db.Column(db.DateTime)

    def __repr__(self):
        return f"<Camera {self.ID}:{self.CameraID}-{self.CameraName}>"

    def configs(self, block="CameraConfigures"):
        """Config dict of one Meta block ({} when missing)."""
        data = (self.Meta or {}).get(block) or {}
        cfg = data.get("configs") if isinstance(data, dict) else None
        return cfg if isinstance(cfg, dict) else {}

    def safe_id(self):
        """CameraID usable as a file name (same rule as services/snapshot.py)."""
        import re

        return re.sub(r"[\\/:*?\"<>|]", "_", str(self.CameraID or self.ID))

    def station_code(self):
        """SiteCode of the station chosen on the camera form, or None."""
        from models.station import Station

        station_id = Util.safe_int(self.configs().get("StationID"), None)
        if station_id is None:
            return None
        station = Station.query.get(station_id)
        return station.SiteCode if station else None

    def data_folder(self):
        """Private RTU Data/<SiteCode or _unassigned>/<CameraID> folder (not created)."""
        from models.station import Station

        return os.path.join(
            Station.data_folder_for(self.station_code()), self.safe_id()
        )

    def images_folder(self):
        return os.path.join(self.data_folder(), "images")

    def images_temp_folder(self):
        return os.path.join(self.data_folder(), "images_temp")

    def images_out_folder(self):
        return os.path.join(self.data_folder(), "images_out")

    def raw_temp_folder(self):
        """Last RTSP clip recorded by the AI worker (raw.mp4 + raw.json)."""
        return os.path.join(self.data_folder(), "raw_temp")

    def public_folder(self):
        """static/data/cameras/<CameraID> - web-served animation / newest picture."""
        return os.path.join(self.snapshotPath, self.safe_id())

    def remove_files(self):
        """Delete everything stored for this camera on disk: the RTU Data
        folder (images, images_temp, images_out), the public pictures and the
        uploaded model. Used when the camera row is deleted; never raises."""
        import shutil

        for folder in (self.data_folder(), self.public_folder()):
            shutil.rmtree(folder, ignore_errors=True)
        self._remove_model_files()

    def set_config(self, key, value, block="CameraConfigures"):
        """Write one value into Meta[block]["configs"] (new dict so SQLAlchemy
        notices the JSONB change); caller commits."""
        import copy

        meta = copy.deepcopy(self.Meta) if isinstance(self.Meta, dict) else {}
        data = meta.get(block) if isinstance(meta.get(block), dict) else {}
        cfg = data.get("configs") if isinstance(data.get("configs"), dict) else {}
        cfg[key] = value
        data["configs"] = cfg
        data.setdefault("status", True)
        meta[block] = data
        self.Meta = meta

    def model_file(self):
        """Absolute path of the uploaded weights, or None when none is stored."""
        name = str(self.configs().get("TrainedModel") or "").strip()
        if not name or os.path.basename(name) != name:
            return None
        return os.path.join(self.modelPath, name)

    def store_model(self, file):
        """Save an uploaded weights file as <modelPath>/<CameraID>.<ext>, drop
        any previous file of this camera and record the name in Meta.
        Returns the stored file name; raises ValueError on a bad extension."""
        ext = Util.get_safe_extension(
            file.filename, allowed=Util.ALLOWED_MODEL_EXTENSIONS
        )
        if not ext:
            raise ValueError(statictext.Messages["InvalidFileType"])
        filename = f"{self.safe_id()}.{ext}"
        os.makedirs(self.modelPath, exist_ok=True)
        self._remove_model_files()
        file.save(os.path.join(self.modelPath, filename))
        self.set_config("TrainedModel", filename)
        self.UpdateUserID = current_user.UserID
        self.UpdateDate = db.func.now()
        db.session.commit()
        self.export_onnx(filename)
        return filename

    def export_onnx(self, filename):
        """Start `ai/export_onnx.py <file>` in the background so the ONNX twin
        (OpenCV DNN fallback backend of the AI worker) appears next to the
        weights; needs a working torch, so failures are silently ignored
        (the export can be run on another PC and the .onnx copied over)."""
        import subprocess
        import sys

        script = os.path.join(statictext.APP_DIRECTORY, "ai", "export_onnx.py")
        size = str(Util.safe_int(self.configs().get("ModelImageSize"), 0) or "")
        args = [os.getenv("AI_PYTHON") or sys.executable, script, filename]
        if size:
            args += ["--imgsz", size]
        try:
            subprocess.Popen(
                args,
                cwd=statictext.APP_DIRECTORY,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            pass

    def remove_model(self):
        """Delete the stored weights file(s) and clear the Meta reference."""
        self._remove_model_files()
        self.set_config("TrainedModel", "")
        self.UpdateUserID = current_user.UserID
        self.UpdateDate = db.func.now()
        db.session.commit()

    def _remove_model_files(self):
        """Remove every file named <CameraID>.* under modelPath (any extension)."""
        stem = self.safe_id()
        if not os.path.isdir(self.modelPath):
            return
        for name in os.listdir(self.modelPath):
            if os.path.splitext(name)[0] == stem:
                try:
                    os.remove(os.path.join(self.modelPath, name))
                except OSError:
                    pass

    def build_links(self):
        """RTSP stream and ISAPI snapshot URLs from the camera settings
        (design slides 4-5), e.g.
        rtsp://admin:pass@147.30.93.37:554/Streaming/Channels/101 and
        http://admin:pass@147.50.93.37:64/ISAPI/Streaming/channels/101/picture.
        Mirrors renderCameraLinks() in static/js/dashboard/cameras.js."""
        from urllib.parse import quote

        cfg = self.configs()
        host = str(cfg.get("RSTP_IP") or "").strip()
        host = host.split("://")[-1].split("/")[0].split("@")[-1].split(":")[0]
        if not host:
            return {"StreamURL": "", "SnapshotURL": ""}

        user = quote(str(cfg.get("Username") or ""), safe="")
        password = quote(str(cfg.get("Password") or ""), safe="")
        auth = f"{user}:{password}@" if user else ""
        channel = str(cfg.get("ChannelsID") or "101").strip() or "101"
        rtsp_port = Util.safe_int(cfg.get("Port"), 554) or 554
        isapi_port = Util.safe_int(cfg.get("ISAPI_Port"), 80) or 80

        return {
            "StreamURL": f"rtsp://{auth}{host}:{rtsp_port}/Streaming/Channels/{channel}",
            "SnapshotURL": f"http://{auth}{host}:{isapi_port}/ISAPI/Streaming/channels/{channel}/picture",
        }

    def snapshot(self):
        """Public pictures for the CCTV page / camera form:
        {SnapshotImage: animation URL (falls back to the still, then the blank
        image), SnapshotStill: newest picture URL or None, SnapshotTime: taken-at
        of the newest archived picture or None}. The files are rewritten in
        place by services/snapshot.py, so the URLs carry ?t=<mtime> as a
        cache-buster (plus a no-store header, util/handlers.py)."""
        from services.snapshot import snapshot_file, snapshot_time

        folder = self.public_folder()
        base = f"{self.snapshotUrl}/{os.path.basename(folder)}"
        urls = {}
        for key, name in (("gif", self.snapshotGif), ("still", self.snapshotStill)):
            path = os.path.join(folder, name)
            try:
                urls[key] = f"{base}/{name}?t={int(os.path.getmtime(path))}"
            except OSError:
                urls[key] = None
        newest = snapshot_file(self)
        return {
            "SnapshotImage": urls["gif"] or urls["still"] or statictext.Images["Blank"],
            "SnapshotStill": urls["still"],
            "SnapshotTime": snapshot_time(newest) if newest else None,
        }

    def serialize(self):
        data = {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }

        data.update(self.build_links())
        data.update(self.snapshot())

        return data

    def remove(self, commit=True):
        try:
            db.session.delete(self)
            if commit:
                db.session.commit()
            # row gone: drop the camera's folders and model file as well
            self.remove_files()
            return True
        except Exception:
            db.session.rollback()
            return False

    ################################ Class methods ################################

    @classmethod
    def getData(cls, id):
        object = cls.query.filter(cls.ID == id).first()

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

        objID = params.get("ID")

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

        objID = params.get("ID")
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
                            pg_get_serial_sequence('tbl_camera', 'ID'),
                            (SELECT MAX("ID") FROM "tbl_camera")
                        )
                    """))
        except SQLAlchemyError as e:
            print(f"An error occurred while updating the sequence: {e}")
