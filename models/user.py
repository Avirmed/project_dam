import os
import math
import time
import hashlib
import json
from flask_login import login_user, logout_user, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token

from database import db
from sqlalchemy import text, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import contains_eager
from sqlalchemy.dialects.postgresql import JSONB

from util import statictext, util as Util


class User(UserMixin, db.Model):
    __tablename__ = "tbl_user"

    drfFilePath = os.path.join(statictext.APP_STATIC_PATH, "data", "user")
    filePath = os.path.join("/static", "data", "user")
    img_size = {
        "sm": {"width": 600, "height": 600, "fldr": "md"},
        "xs": {"width": 200, "height": 200, "fldr": "sm"},
    }

    sort = [{"column": "UserID", "field": "UserID", "dir": "asc"}]

    searchFields = ["UserName", "FirstName", "LastName", "Email"]

    required_fields = ["UserName", "LastName", "FirstName", "Email"]

    UserID = db.Column(db.Integer, primary_key=True)
    UserName = db.Column(db.String(250), unique=True, nullable=False)
    _password = db.Column("Password", db.String(250), nullable=False)
    Email = db.Column(db.String(250), nullable=False)

    FirstName = db.Column(db.String(250))
    LastName = db.Column(db.String(250))
    ImageSource = db.Column(db.String(250))
    UserType = db.Column(db.SmallInteger, default=1, nullable=False)
    Status = db.Column(db.SmallInteger, default=1, nullable=False)
    MultiLogin = db.Column(db.SmallInteger, default=1, nullable=False)
    Remark = db.Column(db.Text)
    Theme = db.Column(db.SmallInteger, default=1, nullable=False)

    AccessToken = db.Column(db.String(500))
    LastLogin = db.Column(db.DateTime)

    CreateUserID = db.Column(db.Integer)
    CreateDate = db.Column(db.DateTime)
    UpdateUserID = db.Column(db.Integer)
    UpdateDate = db.Column(db.DateTime)

    def __repr__(self):
        return f"<User {self.UserID}:{self.UserName}>"

    def get_id(self):
        return self.UserID

    def serialize(self):
        data = {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }
        data["Image"] = self.getImage()
        data["ImageSM"] = self.getImage("sm")
        data["self"] = (
            current_user.is_authenticated and self.UserID == current_user.UserID
        )

        data.pop("Password", None)
        data.pop("AccessToken", None)

        return data

    def getTheme(self):
        return "light" if self.Theme == 1 else "dark"

    @property
    def Password(self):
        return self._password

    @Password.setter
    def Password(self, plain_text_password):
        if plain_text_password:
            plain_text_password = plain_text_password.strip()
            if plain_text_password != "":
                self._password = generate_password_hash(plain_text_password)

    def check_password(self, plain_text_password):
        return check_password_hash(self._password, plain_text_password)

    def update_token(self):
        if self.MultiLogin == 0 or self.AccessToken is None or self.AccessToken == "":
            self.AccessToken = create_access_token(identity=self.UserID)

        self.LastLogin = db.func.now()
        db.session.commit()

    def logout(self):
        if self.MultiLogin == 0:
            self.AccessToken = None
            db.session.commit()

        logout_user()

    def getImage(self, size="xs"):
        if self.ImageSource is not None and self.ImageSource != "":
            image_path = os.path.join(self.filePath, size, self.ImageSource)

            if os.path.exists(os.path.join(self.drfFilePath, size, self.ImageSource)):
                return image_path

        return statictext.Images["Profile"]

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

        try:
            db.session.delete(self)
            if commit:
                db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            return False

    ################################ Class methods ################################

    @classmethod
    def getData(cls, id):
        object = cls.query.get(int(id))

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

        params.pop("ImageSource", None)

        objID = params.get("UserID")
        username = params.get("UserName")
        deleteimage = params.get("deleteimage", False)

        existing_user = cls.query.filter(
            func.lower(cls.UserName) == func.lower(username)
        ).first()
        if existing_user and str(existing_user.UserID) != str(objID or ""):
            error_code = 400

            jsonResult.update(
                {
                    "Message": f"'{username}' : {statictext.Messages['UserAlreadyExists']}",
                    "Code": error_code,
                }
            )

            return jsonResult

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
                    if key == "Password" and value == "":
                        continue

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
                resultMsg = statictext.Messages["UserUpdated"]

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
                resultMsg = statictext.Messages["UserCreated"]

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

        objID = params.get("UserID")
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
                    {"Message": statictext.Messages["UserNotFound"], "Code": 404}
                )
                return jsonResult

            if object.UserName.lower() == "admin":
                jsonResult.update(
                    {"Message": statictext.Messages["UserNotDeleted"], "Code": 403}
                )
                return jsonResult

            if str(object.UserID) == str(current_user.UserID):
                jsonResult.update(
                    {"Message": statictext.Messages["UserNotDeleted"], "Code": 403}
                )
                return jsonResult

            if object.remove():
                jsonResult.update(
                    {
                        "Result": True,
                        "Message": statictext.Messages["UserDeleted"],
                        "Code": 200,
                    }
                )
            else:
                error_code = 500
                jsonResult.update(
                    {
                        "Message": statictext.Messages["UserNotDeleted"],
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
            objData["UserType"] = statictext.UserTypes.get(object.UserType, "Unknown")

            result["data"].append(objData)

        return result

    @classmethod
    def check(cls, params={}):
        jsonResult = {
            "Result": False,
            "Title": statictext.Messages["Title"],
            "Message": statictext.Messages["InvalidAccess"],
            "Code": 400,
        }

        required_fields = ["Auth", "Token"]
        missing_fields = [
            field
            for field in required_fields
            if field not in params or not str(params[field]).strip()
        ]

        if missing_fields:
            if current_user.is_authenticated:
                jsonResult = {
                    "UserType": current_user.UserType,
                    "Theme": current_user.Theme,
                    "Permission": statictext.UserTypes.get(current_user.UserType),
                    "Result": True,
                    "Code": 200,
                }

                return jsonResult

            error_code = 400

            jsonResult.update(
                {"Message": statictext.ResponseCode[error_code], "Code": error_code}
            )

            return jsonResult

        user_id = Util.app_decrypt(params["Auth"])
        object = cls.query.get(int(user_id))

        if object is None:
            error_code = 404

            jsonResult.update(
                {"Message": statictext.Messages["UserNotFound"], "Code": error_code}
            )

            return jsonResult

        if object.AccessToken == params["Token"]:
            jsonResult = {
                "UserType": object.UserType,
                "Theme": object.Theme,
                "Permission": statictext.UserTypes.get(object.UserType),
                "Result": True,
                "Code": 200,
            }

            if not current_user.is_authenticated:
                login_user(object, remember=True)

            return jsonResult
        else:
            error_code = 401

            jsonResult.update(
                {"Message": statictext.ResponseCode[error_code], "Code": error_code}
            )

        return jsonResult

    @classmethod
    def fix_sequence(cls):
        try:
            with db.engine.connect() as conn:
                conn.execute(text("""
                        SELECT setval(
                            pg_get_serial_sequence('tbl_user', 'UserID'),
                            (SELECT MAX("UserID") FROM "tbl_user")
                        )
                    """))
        except SQLAlchemyError as e:
            print(f"An error occurred while updating the sequence: {e}")

    @classmethod
    def load_user(cls, user_id):
        return cls.query.get(int(user_id))

    @classmethod
    def create_default_user(cls):
        user = cls.query.filter_by(UserName="admin").first()

        if not user:
            default_user = cls(
                UserID=1,
                UserName="admin",
                Password="qweqwe",
                UserType=1,
                Email="admin@example.com",
            )

            try:
                db.session.add(default_user)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
