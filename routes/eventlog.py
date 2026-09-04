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


@eventlog_bp.route("/latest", methods=["GET", "POST"])
@login_required
def latest():
    """Newest pending events for the header notification dropdown."""
    return jsonify(EventLog.latest(_request_data()))


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

    actions = statictext.EventLogActions
    for row in jsonResult.get("data", []):
        current = row.get("Status")
        status = statictext.EventLogStatuses.get(current, {})
        # soft pill with a coloured dot (classes in custom.css)
        row["StatusBadge"] = (
            f'<span class="{status.get("pill", "")}"><i class="status-pill-dot"></i>{status.get("text", "")}</span>'
        )
        # one row menu like the dashboard grids (.tmp-control): Approve / Reject,
        # the current status disabled
        items = ""
        for code, label, icon in (
            (EventLog.STATUS_APPROVE, approve["text"], statictext.Icon["Check"]),
            (EventLog.STATUS_REJECT, reject["text"], statictext.Icon["Uncheck"]),
        ):
            disabled = " disabled" if current == code else ""
            items += (
                f'<li><a class="dropdown-item actionBtn{disabled}" href="javascript:;" '
                f'data-status="{code}">{icon} {label}</a></li>'
            )
        popper = "'" + '{"strategy":"fixed"}' + "'"  # menu escapes the cell's overflow clipping
        row["control"] = (
            f'<div class="dropdown position-static app-row-menu">'
            f'<button class="btn btn-sm" type="button" data-bs-toggle="dropdown" '
            f'data-bs-popper-config={popper} title="{actions["Menu"]}">'
            f'{statictext.Icon["VerticalDots"]}</button>'
            f'<ul class="dropdown-menu dropdown-menu-end">{items}</ul></div>'
        )

    # No. | Image | Station | River | Date Time | Event | Status | Action
    # fixed widths for the narrow columns; River and Event share the rest
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
            "title": statictext.EventLogField["Image"],
            "field": "Image",
            "width": 70,
            "headerHozAlign": "center",
            "hozAlign": "center",
            "vertAlign": "middle",
            "headerSort": False,
            "resizable": False,
        },
        {
            "title": statictext.EventLogField["StationID"],
            "field": "SiteCode",
            "width": 160,
            "headerHozAlign": "center",
            "hozAlign": "center",
            "vertAlign": "middle",
            "headerSort": False,
        },
        {
            "title": statictext.EventLogField["WatershedName"],
            "field": "WatershedName",
            "formatter": "textarea",
            "minWidth": 160,
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": False,
        },
        {
            "title": statictext.EventLogField["EventTime"],
            "field": "EventTime",
            "width": 150,
            "headerHozAlign": "center",
            "hozAlign": "center",
            "vertAlign": "middle",
            "headerSort": True,
        },
        {
            "title": statictext.EventLogField["Event"],
            "field": "Event",
            "minWidth": 140,
            "headerHozAlign": "center",
            "hozAlign": "center",
            "vertAlign": "middle",
            "headerSort": True,
        },
        {
            "title": statictext.EventLogField["Status"],
            "field": "StatusBadge",
            "width": 100,
            "headerHozAlign": "center",
            "hozAlign": "center",
            "vertAlign": "middle",
            "formatter": "html",
            "headerSort": False,
            "resizable": False,
        },
        {
            "title": statictext.EventLogField["Action"],
            "field": "control",
            "width": 60,
            "headerHozAlign": "right",
            "hozAlign": "right",
            "vertAlign": "middle",
            "formatter": "html",
            "headerSort": False,
            "resizable": False,
            "download": False,
        },
    ]

    return jsonify(jsonResult)
