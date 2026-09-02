import json

from flask import Blueprint, request, jsonify, abort
from flask_login import login_required

from models import StationData

from util import statictext

stationdata_bp = Blueprint("stationdata_bp", __name__)


@stationdata_bp.route("/get/<int:id>")
@login_required
def get(id):
    object_data = StationData.getData(id)
    if object_data is None:
        error_code = 404
        abort(error_code, description=statictext.ResponseCode[error_code])

    return jsonify(object_data)


@stationdata_bp.route("/list", methods=["GET", "POST"])
@login_required
def list():
    """Read-only list of received payloads; filter by StationID / DeviceID."""
    get_data = request.args.to_dict()
    post_data = (
        request.get_json() if request.is_json else request.form.to_dict()
    ) or {}
    requestData = {**get_data, **post_data}

    if not requestData.get("filters"):
        requestData["filters"] = {}

    for key in ("StationID", "DeviceID"):
        if requestData.get(key):
            requestData["filters"][key] = requestData.get(key)

    jsonResult = StationData.list(requestData)

    # JSONB columns are shown as readable strings in the table.
    for row in jsonResult.get("data", []):
        for key in ("Data", "Raw"):
            if isinstance(row.get(key), (dict, list)):
                row[key] = json.dumps(row[key], ensure_ascii=False)

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
        {
            "title": statictext.StationDataField["ID"],
            "field": "ID",
            "visible": False,
        },
        {
            "title": statictext.StationDataField["StationID"],
            "field": "SiteName",
            "formatter": "textarea",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": False,
        },
        {
            "title": statictext.StationDataField["DeviceID"],
            "field": "DeviceID",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": True,
        },
        {
            "title": statictext.StationDataField["RecordTime"],
            "field": "RecordTime",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": True,
        },
        {
            "title": statictext.StationDataField["Data"],
            "field": "Data",
            "formatter": "textarea",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": False,
        },
    ]

    return jsonify(jsonResult)
