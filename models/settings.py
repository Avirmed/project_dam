from database import db
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.postgresql import JSONB
import json

from util import statictext, util as Util


class Settings(db.Model):
    __tablename__ = "tbl_settings"

    ID = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(200), unique=True, nullable=False)
    Value = db.Column(db.String(500), nullable=False)

    def __repr__(self):
        return f"<Settings {self.Name}:{self.Value}>"

    def serialize(self):
        data = {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }

        return data

    ################################ Class methods ################################

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
            "Code": 200,
        }

        required_fields = ["Name", "Value"]
        missing_fields = [
            field
            for field in required_fields
            if field not in params or not str(params[field]).strip()
        ]

        if missing_fields:
            error_code = 422

            jsonResult.update(
                {"Message": statictext.ResponseCode[error_code], "Code": error_code}
            )

            return jsonResult

        try:
            object = cls.query.filter_by(Name=params["Name"]).first()
            object.Value = (
                params["Value"].strip()
                if isinstance(params["Value"], str)
                else params["Value"]
            )

            db.session.commit()
            resultMsg = statictext.Messages["SuccessUpdated"]

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
    def load_settings(cls):
        settings = cls.query.all()
        return {setting.Name: setting.Value for setting in settings}

    @classmethod
    def fix_sequence(cls):
        try:
            # begin() commits on exit; connect() would roll the setval back, leaving the sequence unchanged.
            with db.engine.begin() as conn:
                conn.execute(text("""
                        SELECT setval(
                            pg_get_serial_sequence('tbl_settings', 'ID'),
                            (SELECT MAX("ID") FROM "tbl_settings")
                        )
                    """))
        except SQLAlchemyError as e:
            print(f"An error occurred while updating the sequence: {e}")
