import math

from database import db
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import contains_eager
from sqlalchemy.dialects.postgresql import JSONB

from util import statictext, util as Util


class HttpLog(db.Model):
    """Read-only log of outbound HTTP deliveries (populated by the runtime
    sender, which is not built yet). The dashboard only lists these rows."""

    __tablename__ = "tbl_httplog"

    sort = [
        {"column": "ID", "field": "ID", "dir": "desc"},
    ]

    searchFields = ["DeviceID"]

    ID = db.Column(db.Integer, primary_key=True)

    DeviceID = db.Column(db.String(100), index=True)
    Content = db.Column(JSONB, nullable=True, default=dict)
    Status = db.Column(db.SmallInteger, default=1, nullable=False)

    CreateDate = db.Column(db.DateTime)

    def __repr__(self):
        return f"<HttpLog {self.ID}:{self.DeviceID}>"

    def serialize(self):
        data = {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }

        return data

    ################################ Class methods ################################

    @classmethod
    def getData(cls, id):
        object = cls.query.filter(cls.ID == id).first()

        if object is None:
            return None

        return object.serialize()

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
                            pg_get_serial_sequence('tbl_httplog', 'ID'),
                            (SELECT MAX("ID") FROM "tbl_httplog")
                        )
                    """))
        except SQLAlchemyError as e:
            print(f"An error occurred while updating the sequence: {e}")
