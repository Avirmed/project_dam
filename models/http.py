import math
import json

from flask_login import current_user

from database import db
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import contains_eager
from sqlalchemy.dialects.postgresql import JSONB

from util import statictext, util as Util


class Http(db.Model):
    __tablename__ = "tbl_http"

    sort = [
        {"column": "URL", "field": "URL", "dir": "asc"},
    ]

    searchFields = ["URL"]

    required_fields = ["StationID", "URL"]

    ID = db.Column(db.Integer, primary_key=True)

    StationID = db.Column(
        db.Integer,
        db.ForeignKey("tbl_station.StationID", onupdate="CASCADE", ondelete="RESTRICT"),
        index=True,
        nullable=True,
    )
    URL = db.Column(db.String(500), nullable=False)

    Meta = db.Column(JSONB, nullable=True, default=dict)

    Status = db.Column(db.SmallInteger, default=1, nullable=False)
    Remark = db.Column(db.Text)

    CreateUserID = db.Column(db.Integer)
    CreateDate = db.Column(db.DateTime)
    UpdateUserID = db.Column(db.Integer)
    UpdateDate = db.Column(db.DateTime)

    station = db.relationship("Station")

    def __repr__(self):
        return f"<Http {self.ID}:{self.URL}>"

    def serialize(self):
        data = {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }

        data["SiteName"] = self.station.SiteName if self.station else None
        data["DeviceID"] = self.station.DeviceID if self.station else None

        return data

    def remove(self, commit=True):
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
        object = cls.query.filter(cls.ID == id).first()

        if object is None:
            return None

        return object.serialize()

    @classmethod
    def _parse_json_fields(cls, params):
        jsonb_fields = {
            col.name
            for col in cls.__table__.columns
            if isinstance(col.type, (db.JSON, JSONB))
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
                            pg_get_serial_sequence('tbl_http', 'ID'),
                            (SELECT MAX("ID") FROM "tbl_http")
                        )
                    """))
        except SQLAlchemyError as e:
            print(f"An error occurred while updating the sequence: {e}")
