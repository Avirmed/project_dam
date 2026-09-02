import json

from flask import Blueprint, request, jsonify, abort
from flask_login import login_required

from models import (
    HttpLog,
)

from util import statictext

httplog_bp = Blueprint("httplog_bp", __name__)


@httplog_bp.route("/get/<int:id>")
@login_required
def get(id):
    if not str(id).isdigit():
        error_code = 400
        abort(error_code, description=statictext.ResponseCode[error_code])

    object_data = HttpLog.getData(id)
    if object_data is None:
        error_code = 404
        abort(error_code, description=statictext.ResponseCode[error_code])

    return jsonify(object_data)


@httplog_bp.route("/list", methods=["GET", "POST"])
@login_required
def list():
    get_data = request.args.to_dict()
    post_data = (
        request.get_json() if request.is_json else request.form.to_dict()
    ) or {}
    requestData = {**get_data, **post_data}

    if not requestData.get("filters"):
        requestData["filters"] = {}

    if requestData.get("status"):
        requestData["filters"]["Status"] = requestData.get("status")

    jsonResult = HttpLog.list(requestData)

    # Render the JSONB payload as a readable string in the list grid
    # (a dict would show up as "[object Object]"); the /get detail keeps the object.
    for row in jsonResult.get("data", []):
        if isinstance(row.get("Content"), (dict, list)):
            row["Content"] = json.dumps(row["Content"], ensure_ascii=False)

    jsonResult["column"] = [
        {
            "title": statictext.Numbering,
            "field": "rownum",
            "formatter": "rownum",
            "width": 50,
            "headerHozAlign": "center",
            "hozAlign": "center",
            "vertAlign": "middle",
            "headerSort": False,
            "resizable": False,
        },
        {"title": statictext.HttpLogField["ID"], "field": "ID", "visible": False},
        {
            "title": statictext.HttpLogField["DeviceID"],
            "field": "DeviceID",
            "formatter": "textarea",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": True,
        },
        {
            "title": statictext.HttpLogField["Content"],
            "field": "Content",
            "width": "45%",
            "formatter": "textarea",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": False,
        },
        {
            "title": statictext.HttpLogField["CreateDate"],
            "field": "CreateDate",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": True,
        },
        {
            "title": statictext.HttpLogField["Status"],
            "field": "Status",
            "width": 100,
            "headerHozAlign": "center",
            "hozAlign": "center",
            "vertAlign": "middle",
            "formatter": "tickCross",
            "headerSort": False,
        },
    ]

    return jsonify(jsonResult)
