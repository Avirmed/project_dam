import json

from flask import Blueprint, request, jsonify, abort
from flask_login import login_required

from models import (
    HttpLog,
)

from util import statictext

from models import Team

httplog_bp = Blueprint("httplog_bp", __name__)


def _request_data():
    get_data = request.args.to_dict()
    post_data = (
        request.get_json() if request.is_json else request.form.to_dict()
    ) or {}
    requestData = {**get_data, **post_data}

    if not requestData.get("filters"):
        requestData["filters"] = {}

    if requestData.get("status"):
        requestData["filters"]["Status"] = requestData.get("status")

    # Staff / Guest only see logs of their teams' stations (fail-closed).
    Team.apply_station_scope(requestData)

    return requestData


@httplog_bp.route("/get/<int:id>")
@login_required
def get(id):
    object_data = HttpLog.getData(id)
    if object_data is None or not Team.can_access_station(object_data.get("StationID")):
        error_code = 404
        abort(error_code, description=statictext.ResponseCode[error_code])

    return jsonify(object_data)


@httplog_bp.route("/counters", methods=["GET", "POST"])
@login_required
def counters():
    """Queue / Sent / Failed totals for the current filters (status ignored)."""
    return jsonify(HttpLog.counters(_request_data()))


@httplog_bp.route("/list", methods=["GET", "POST"])
@login_required
def list():
    requestData = _request_data()

    jsonResult = HttpLog.list(requestData)

    # Presentation-only fields for the grid: status badge, detail button and a
    # readable payload string (a dict would show as "[object Object]").
    for row in jsonResult.get("data", []):
        status = statictext.HttpLogStatuses.get(row.get("Status"), {})
        row["StatusBadge"] = (
            f'<span class="{status.get("class", "")}">{status.get("text", "")}</span>'
        )
        detail_title = statictext.HttpLogField["Detail"]
        row["control"] = (
            f'<span class="viewBtn text-primary" role="button" title="{detail_title}">{statictext.Icon["Info"]}</span>'
        )
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
            "title": statictext.HttpLogField["SiteName"],
            "field": "SiteName",
            "formatter": "textarea",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": False,
        },
        {
            "title": statictext.HttpLogField["DeviceID"],
            "field": "DeviceID",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": True,
        },
        {
            "title": statictext.HttpLogField["Method"],
            "field": "Method",
            "width": 80,
            "headerHozAlign": "center",
            "hozAlign": "center",
            "vertAlign": "middle",
            "headerSort": False,
        },
        {
            "title": statictext.HttpLogField["URL"],
            "field": "URL",
            "width": "30%",
            "formatter": "textarea",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": False,
        },
        {
            "title": statictext.HttpLogField["ResponseCode"],
            "field": "ResponseCode",
            "width": 90,
            "headerHozAlign": "center",
            "hozAlign": "center",
            "vertAlign": "middle",
            "headerSort": True,
        },
        {
            "title": statictext.HttpLogField["Attempts"],
            "field": "Attempts",
            "width": 80,
            "headerHozAlign": "center",
            "hozAlign": "center",
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
            "title": statictext.HttpLogField["SentDate"],
            "field": "SentDate",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": True,
        },
        {
            "title": statictext.HttpLogField["Status"],
            "field": "StatusBadge",
            "width": 120,
            "headerHozAlign": "center",
            "hozAlign": "center",
            "vertAlign": "middle",
            "formatter": "html",
            "headerSort": False,
        },
        {
            "title": "",
            "field": "control",
            "width": 50,
            "hozAlign": "center",
            "vertAlign": "middle",
            "formatter": "html",
            "headerSort": False,
            "resizable": False,
            "download": False,
        },
    ]

    return jsonify(jsonResult)
