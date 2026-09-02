import json

from flask import Blueprint, request, jsonify, abort
from flask_login import login_required

from models import (
    Sensor,
)

from util import statictext, hydro

from util.auth import require_types, EDITORS

sensor_bp = Blueprint("sensor_bp", __name__)


@sensor_bp.route("/profile", methods=["POST"])
@require_types(*EDITORS)
def profile():
    """Flow tab "Calculate": Profile rows (water level -> wetted area) from the
    Custom Profile polygon sent by the form; nothing is stored until Save."""
    data = request.get_json(silent=True) or request.form.to_dict()
    rows = data.get("CustomProfile")
    if isinstance(rows, str):
        try:
            rows = json.loads(rows)
        except ValueError:
            rows = []

    jsonResult = {
        "Result": False,
        "Title": statictext.Messages["Title"],
        "Message": statictext.Messages["ProfileNeedsPoints"],
        "Code": 422,
    }

    profile = hydro.build_profile(rows, data.get("AreaRef") or "Level")
    if profile:
        jsonResult.update(
            {
                "Result": True,
                "Data": profile,
                "Message": statictext.Messages["ProfileCalculated"],
                "Code": 200,
            }
        )

    return jsonify(jsonResult), jsonResult["Code"]


@sensor_bp.route("/get/<int:id>")
@login_required
def get(id):
    if not str(id).isdigit():
        error_code = 400
        abort(error_code, description=statictext.ResponseCode[error_code])

    object_data = Sensor.getData(id)
    if object_data is None:
        error_code = 404
        abort(error_code, description=statictext.ResponseCode[error_code])

    return jsonify(object_data)


@sensor_bp.route("/detail", methods=["POST"])
@login_required
def getByPost():
    get_data = request.args.to_dict()
    post_data = (
        request.get_json() if request.is_json else request.form.to_dict()
    ) or {}
    requestData = {**get_data, **post_data}

    jsonResult = {
        "Result": False,
        "Title": statictext.Messages["Title"],
        "Message": statictext.Messages["InvalidAccess"],
        "Code": 400,
    }

    objID = requestData.get("cid")

    if not objID:
        error_code = 404
        jsonResult.update(
            {"Message": f"{statictext.ResponseCode[error_code]}", "Code": error_code}
        )
        return jsonify(jsonResult), jsonResult["Code"]

    object_data = Sensor.getData(objID, True)

    if object_data is None:
        error_code = 404
        jsonResult.update(
            {"Message": f"{statictext.ResponseCode[error_code]}", "Code": error_code}
        )
        return jsonify(jsonResult), jsonResult["Code"]

    jsonResult = {"Result": True, "Code": 200, "Data": object_data}

    return jsonify(jsonResult), jsonResult["Code"]


@sensor_bp.route("/list", methods=["GET", "POST"])
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

    jsonResult = Sensor.list(requestData)

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
        {"title": statictext.SensorField["ID"], "field": "ID", "visible": False},
        {
            "title": statictext.SensorField["SensorID"],
            "field": "SensorID",
            "width": 200,
            "formatter": "textarea",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": True,
        },
        {
            "title": statictext.SensorField["SensorName"],
            "field": "SensorName",
            "formatter": "textarea",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": True,
        },
        {
            "title": statictext.SensorField["SensorType"],
            "field": "SensorType",
            "width": 200,
            "formatter": "textarea",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": True,
        },
        {
            "title": statictext.RiverBasinField["Status"],
            "field": "Status",
            "width": 100,
            "headerHozAlign": "center",
            "hozAlign": "center",
            "vertAlign": "middle",
            "formatter": "tickCross",
            "headerSort": False,
        },
        {
            "title": statictext.SensorField["Remark"],
            "field": "Remark",
            "width": "20%",
            "formatter": "textarea",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": False,
        },
    ]

    return jsonify(jsonResult)


@sensor_bp.route("/save", methods=["POST"])
@require_types(*EDITORS)
def save():
    get_data = request.args.to_dict()
    post_data = (
        request.get_json() if request.is_json else request.form.to_dict()
    ) or {}
    requestData = {**get_data, **post_data}

    jsonResult = Sensor.save(requestData)

    return jsonify(jsonResult), jsonResult["Code"]


@sensor_bp.route("/delete", methods=["POST"])
@require_types(*EDITORS)
def delete():
    get_data = request.args.to_dict()
    post_data = (
        request.get_json() if request.is_json else request.form.to_dict()
    ) or {}
    requestData = {**get_data, **post_data}

    jsonResult = Sensor.delete(requestData)

    return jsonify(jsonResult), jsonResult["Code"]
