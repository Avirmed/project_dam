import builtins
import json

from flask import Blueprint, request, jsonify, abort
from flask_login import login_required

from models import StationData, Team
from util import statictext

stationdata_bp = Blueprint("stationdata_bp", __name__)


def _request_data():
    """Merge args / JSON / form; lift the legacy top-level StationID / DeviceID
    into filters and apply the user's station scope (Staff / Guest)."""
    get_data = request.args.to_dict()
    post_data = (
        request.get_json() if request.is_json else request.form.to_dict()
    ) or {}
    requestData = {**get_data, **post_data}

    if not isinstance(requestData.get("filters"), dict):
        requestData["filters"] = {}

    for key in ("StationID", "DeviceID"):
        if requestData.get(key):
            requestData["filters"][key] = requestData.get(key)

    # Staff / Guest only see data of their teams' stations (fail-closed).
    Team.apply_station_scope(requestData)

    return requestData


def _value_columns():
    """One grid column per agreed Data column (statictext.StationDataKeys)."""
    columns = []
    for key in statictext.StationDataKeys.values():
        meta = statictext.StationDataParameters.get(key, {})
        title = meta.get("text", key)
        if meta.get("unit"):
            title = f"{title} ({meta['unit']})"
        columns.append(
            {
                "title": title,
                "field": f"V_{key}",
                "headerHozAlign": "center",
                "hozAlign": "right",
                "vertAlign": "middle",
                "headerSort": False,
                "width": 100,
            }
        )
    return columns


@stationdata_bp.route("/get/<int:id>")
@login_required
def get(id):
    object_data = StationData.getData(id)
    if object_data is None or not Team.can_access_station(object_data.get("StationID")):
        error_code = 404
        abort(error_code, description=statictext.ResponseCode[error_code])

    return jsonify(object_data)


@stationdata_bp.route("/summary", methods=["GET", "POST"])
@login_required
def summary():
    """Payloads / stations / first / last record for the current filters."""
    return jsonify(StationData.summary(_request_data()))


@stationdata_bp.route("/series", methods=["GET", "POST"])
@login_required
def series():
    """Chart data for one station: one Data column (filters.Parameter, see
    StationData.series) or several at once when "parameters" is a list."""
    requestData = _request_data()
    keys = requestData.get("parameters")
    # NB: `list` is shadowed by the list() view below - use builtins.list
    if isinstance(keys, builtins.list) and keys:
        allowed = set(statictext.StationDataKeys.values())
        return jsonify(
            StationData.series_multi(requestData, [k for k in keys if k in allowed])
        )
    return jsonify(StationData.series(requestData))


@stationdata_bp.route("/list", methods=["GET", "POST"])
@login_required
def list():
    """Read-only grid of received payloads with the agreed Data columns
    flattened into V_<key> fields; JSON columns are kept as readable strings."""
    requestData = _request_data()

    jsonResult = StationData.list(requestData)

    detail_title = statictext.StationDataField["Detail"]
    for row in jsonResult.get("data", []):
        data = row.get("Data") if isinstance(row.get("Data"), dict) else {}
        for key in statictext.StationDataKeys.values():
            row[f"V_{key}"] = data.get(key)
        for key in ("Data", "Raw"):
            if isinstance(row.get(key), (dict, list)):
                row[key] = json.dumps(row[key], ensure_ascii=False)
        row["control"] = (
            f'<span class="viewBtn text-primary" role="button" title="{detail_title}">{statictext.Icon["Info"]}</span>'
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
        {"title": statictext.StationDataField["ID"], "field": "ID", "visible": False},
        {
            "title": statictext.StationDataField["SiteCode"],
            "field": "SiteCode",
            "width": 90,
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": False,
        },
        {
            "title": statictext.StationDataField["SiteName"],
            "field": "SiteName",
            "formatter": "textarea",
            "minWidth": 220,
            "widthGrow": 3,
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": False,
        },
        {
            "title": statictext.StationDataField["DeviceID"],
            "field": "DeviceID",
            "width": 120,
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": True,
        },
        {
            "title": statictext.StationDataField["RecordTime"],
            "field": "RecordTime",
            "width": 160,
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": True,
        },
        *_value_columns(),
        {
            # full mapped payload: hidden in the grid, still exported
            "title": statictext.StationDataField["Data"],
            "field": "Data",
            "visible": False,
            "download": True,
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
