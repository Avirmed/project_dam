from flask import Blueprint, request, jsonify, abort
from flask_login import login_required

from models import (
    CsvLogger,
)

from util import statictext

from models import Team, FileTransfer
from util.auth import require_types, EDITORS

csvlogger_bp = Blueprint("csvlogger_bp", __name__)


@csvlogger_bp.route("/get/<int:id>")
@login_required
def get(id):
    if not str(id).isdigit():
        error_code = 400
        abort(error_code, description=statictext.ResponseCode[error_code])

    object_data = CsvLogger.getData(id)
    transfer = (
        FileTransfer.query.get(object_data.get("FileTransferID"))
        if object_data and object_data.get("FileTransferID")
        else None
    )
    if object_data is None or not Team.can_access_station(
        transfer.StationID if transfer else None
    ):
        error_code = 404
        abort(error_code, description=statictext.ResponseCode[error_code])

    return jsonify(object_data)


@csvlogger_bp.route("/list", methods=["GET", "POST"])
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

    # Station scope reaches the logger through its File Transfer (fail-closed).
    scope = Team.scope_station_ids()
    if scope is not None:
        transfer_ids = [
            t.ID
            for t in FileTransfer.query.filter(FileTransfer.StationID.in_(scope)).all()
        ]
        requestData["filters"]["FileTransferID"] = transfer_ids or [-1]

    jsonResult = CsvLogger.list(requestData)

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
        {"title": statictext.CsvLoggerField["ID"], "field": "ID", "visible": False},
        {
            "title": statictext.CsvLoggerField["FileTransferID"],
            "field": "FileTransferHostname",
            "formatter": "textarea",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": False,
        },
        {
            "title": statictext.CsvLoggerField["FilenameFormat"],
            "field": "FilenameFormat",
            "formatter": "textarea",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": True,
        },
        {
            "title": statictext.CsvLoggerField["LastRun"],
            "field": "LastRun",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": True,
        },
        {
            "title": statictext.CsvLoggerField["LastResult"],
            "field": "LastResult",
            "width": "20%",
            "formatter": "textarea",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": False,
        },
        {
            "title": statictext.CsvLoggerField["Status"],
            "field": "Status",
            "width": 100,
            "headerHozAlign": "center",
            "hozAlign": "center",
            "vertAlign": "middle",
            "formatter": "tickCross",
            "headerSort": False,
        },
        {
            "title": statictext.CsvLoggerField["Remark"],
            "field": "Remark",
            "width": "20%",
            "formatter": "textarea",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": False,
        },
    ]

    return jsonify(jsonResult)


@csvlogger_bp.route("/save", methods=["POST"])
@require_types(*EDITORS)
def save():
    get_data = request.args.to_dict()
    post_data = (
        request.get_json() if request.is_json else request.form.to_dict()
    ) or {}
    requestData = {**get_data, **post_data}

    jsonResult = CsvLogger.save(requestData)

    return jsonify(jsonResult), jsonResult["Code"]


@csvlogger_bp.route("/delete", methods=["POST"])
@require_types(*EDITORS)
def delete():
    get_data = request.args.to_dict()
    post_data = (
        request.get_json() if request.is_json else request.form.to_dict()
    ) or {}
    requestData = {**get_data, **post_data}

    jsonResult = CsvLogger.delete(requestData)

    return jsonify(jsonResult), jsonResult["Code"]
