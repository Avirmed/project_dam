from flask import Blueprint, request, jsonify, abort
from flask_login import login_required

from models import (
    FileTransfer,
)

from util import statictext

from models import Team
from util.auth import require_types, EDITORS

filetransfer_bp = Blueprint("filetransfer_bp", __name__)


@filetransfer_bp.route("/get/<int:id>")
@login_required
def get(id):
    if not str(id).isdigit():
        error_code = 400
        abort(error_code, description=statictext.ResponseCode[error_code])

    object_data = FileTransfer.getData(id)
    if object_data is None or not Team.can_access_station(object_data.get("StationID")):
        error_code = 404
        abort(error_code, description=statictext.ResponseCode[error_code])

    return jsonify(object_data)


@filetransfer_bp.route("/list", methods=["GET", "POST"])
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

    Team.apply_station_scope(requestData)

    jsonResult = FileTransfer.list(requestData)

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
        {"title": statictext.FileTransferField["ID"], "field": "ID", "visible": False},
        {
            "title": statictext.FileTransferField["StationID"],
            "field": "SiteName",
            "formatter": "textarea",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": False,
        },
        {
            "title": statictext.FileTransferField["Hostname"],
            "field": "Hostname",
            "formatter": "textarea",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": True,
        },
        {
            "title": statictext.FileTransferField["Status"],
            "field": "Status",
            "width": 100,
            "headerHozAlign": "center",
            "hozAlign": "center",
            "vertAlign": "middle",
            "formatter": "tickCross",
            "headerSort": False,
        },
        {
            "title": statictext.FileTransferField["Remark"],
            "field": "Remark",
            "width": "20%",
            "formatter": "textarea",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": False,
        },
    ]

    return jsonify(jsonResult)


@filetransfer_bp.route("/save", methods=["POST"])
@require_types(*EDITORS)
def save():
    get_data = request.args.to_dict()
    post_data = (
        request.get_json() if request.is_json else request.form.to_dict()
    ) or {}
    requestData = {**get_data, **post_data}

    jsonResult = FileTransfer.save(requestData)

    return jsonify(jsonResult), jsonResult["Code"]


@filetransfer_bp.route("/delete", methods=["POST"])
@require_types(*EDITORS)
def delete():
    get_data = request.args.to_dict()
    post_data = (
        request.get_json() if request.is_json else request.form.to_dict()
    ) or {}
    requestData = {**get_data, **post_data}

    jsonResult = FileTransfer.delete(requestData)

    return jsonify(jsonResult), jsonResult["Code"]
