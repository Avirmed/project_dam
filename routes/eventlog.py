from flask import Blueprint, request, jsonify, abort
from flask_login import login_required, current_user

from models import (
    EventLog,
)

from util import statictext

from models import Team
from util.auth import require_types, EDITORS

eventlog_bp = Blueprint("eventlog_bp", __name__)


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

    # Staff / Guest only see events of their teams' stations (fail-closed).
    Team.apply_station_scope(requestData)

    return requestData


@eventlog_bp.route("/get/<int:id>")
@login_required
def get(id):
    object_data = EventLog.getData(id)
    if object_data is None or not Team.can_access_station(object_data.get("StationID")):
        error_code = 404
        abort(error_code, description=statictext.ResponseCode[error_code])

    return jsonify(object_data)


@eventlog_bp.route("/counters", methods=["GET", "POST"])
@login_required
def counters():
    return jsonify(EventLog.counters(_request_data()))


@eventlog_bp.route("/action", methods=["POST"])
@require_types(*EDITORS)
def action():
    """Approve (Status 1) / reject (Status 2) one event (own stations only)."""
    requestData = _request_data()
    event = EventLog.getData(requestData.get("ID"))
    if event is None or not Team.can_access_station(event.get("StationID")):
        abort(404, description=statictext.ResponseCode[404])

    jsonResult = EventLog.set_status(requestData, current_user.UserID)
    return jsonify(jsonResult), jsonResult["Code"]


@eventlog_bp.route("/list", methods=["GET", "POST"])
@login_required
def list():
    jsonResult = EventLog.list(_request_data())

    approve = statictext.EventLogStatuses[EventLog.STATUS_APPROVE]
    reject = statictext.EventLogStatuses[EventLog.STATUS_REJECT]

    for row in jsonResult.get("data", []):
        status = statictext.EventLogStatuses.get(row.get("Status"), {})
        row["StatusBadge"] = (
            f'<span class="{status.get("class", "")}">{status.get("text", "")}</span>'
        )
        row["control"] = (
            f'<span class="actionBtn text-success d-block" role="button" data-status="{EventLog.STATUS_APPROVE}">'
            f'{statictext.Icon["CheckFill"]} {approve["text"]}</span>'
            f'<span class="actionBtn text-danger d-block" role="button" data-status="{EventLog.STATUS_REJECT}">'
            f'{statictext.Icon["UncheckFill"]} {reject["text"]}</span>'
        )

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
        {"title": statictext.EventLogField["ID"], "field": "ID", "visible": False},
        {
            "title": statictext.EventLogField["StationID"],
            "field": "SiteCode",
            "headerHozAlign": "center",
            "hozAlign": "center",
            "vertAlign": "middle",
            "headerSort": False,
        },
        {
            "title": statictext.EventLogField["Image"],
            "field": "Image",
            "width": 140,
            "headerHozAlign": "center",
            "hozAlign": "center",
            "vertAlign": "middle",
            "headerSort": False,
        },
        {
            "title": statictext.EventLogField["WatershedName"],
            "field": "WatershedName",
            "formatter": "textarea",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": False,
        },
        {
            "title": statictext.EventLogField["EventTime"],
            "field": "EventTime",
            "headerHozAlign": "center",
            "hozAlign": "center",
            "vertAlign": "middle",
            "headerSort": True,
        },
        {
            "title": statictext.EventLogField["Event"],
            "field": "Event",
            "headerHozAlign": "center",
            "hozAlign": "center",
            "vertAlign": "middle",
            "headerSort": True,
        },
        {
            "title": statictext.EventLogField["Status"],
            "field": "StatusBadge",
            "width": 110,
            "headerHozAlign": "center",
            "hozAlign": "center",
            "vertAlign": "middle",
            "formatter": "html",
            "headerSort": False,
        },
        {
            "title": statictext.EventLogField["Action"],
            "field": "control",
            "width": 120,
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "formatter": "html",
            "headerSort": False,
            "resizable": False,
            "download": False,
        },
    ]

    return jsonify(jsonResult)
