from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request
from flask_login import current_user
from sqlalchemy import func

from database import db
from models import Settings
from util import statictext
from util.auth import require_types, ADMINS, ADMIN, SUPERVISOR, STAFF, GUEST

main_bp = Blueprint("main_bp", __name__)


@main_bp.route("/init", methods=["GET", "POST"])
def init():
    excluded_keys = {
        "os",
        "util",
        "APP_STATIC_PATH",
        "APP_DIRECTORY",
        "APP_TMP_PATH",
        "APP_DATA_PATH",
        "APP_CERT_PATH",
        "UPLOAD_CK_FOLDER_FILE",
        "UPLOAD_CK_FOLDER_IMAGE",
    }

    static_vars = {
        key: value
        for key, value in vars(statictext).items()
        if not key.startswith("__") and key not in excluded_keys
    }

    static_vars["APP_SETTINGS"] = Settings.load_settings()
    static_vars["APP_SETTINGS"]["APP_THEME"] = request.cookies.get(
        "data-theme", "light"
    )

    return jsonify(static_vars)


@main_bp.route("/summary", methods=["GET"])
@require_types(ADMIN, SUPERVISOR, STAFF, GUEST)
def summary():
    """Everything the dashboard overview shows, in one call. Station-related
    numbers follow the user's station scope (Team); worker and system panels
    are Administrator-only."""
    from models import Station, StationData, HttpLog, EventLog, Team
    from services import scheduler, sysinfo

    now = datetime.now()
    scope = Team.scope_station_ids()
    scoped = {"filters": {"StationID": scope}} if scope is not None else {}

    # Stations: live status per station (same rule as the map)
    live = Station.live_status({"filters": {}})
    counts = {key: 0 for key in statictext.WaterLevelTypes}
    attention = []
    for row in live["data"]:
        level = row.get("WaterLevelType", 3)
        counts[level] = counts.get(level, 0) + 1
        if level >= 1:
            data = row.get("WaterLevelData") or {}
            values = data.get("Values") or {}
            attention.append(
                {
                    "StationID": row["StationID"],
                    "SiteCode": row.get("SiteCode"),
                    "SiteName": row.get("SiteName"),
                    "WaterLevelType": level,
                    "RecordTime": data.get("RecordTime"),
                    "WaterLevel": values.get(statictext.StationDataKeys["WaterLevel"]),
                }
            )
    attention.sort(key=lambda r: (-r["WaterLevelType"], str(r["SiteCode"])))

    # Inbound payloads: today, newest, and the last 24 hours per hour
    hour = now.replace(minute=0, second=0, microsecond=0)
    since = hour - timedelta(hours=23)
    query = db.session.query(
        func.date_trunc("hour", StationData.RecordTime).label("h"),
        func.count(StationData.ID),
    ).filter(StationData.RecordTime >= since)
    if scope is not None:
        query = query.filter(StationData.StationID.in_(scope))
    per_hour = {h: n for h, n in query.group_by("h").all()}
    series = [
        {
            "t": (since + timedelta(hours=i)),
            "n": per_hour.get(since + timedelta(hours=i), 0),
        }
        for i in range(24)
    ]
    base = StationData.query
    if scope is not None:
        base = base.filter(StationData.StationID.in_(scope))
    today = base.filter(
        StationData.RecordTime >= now.replace(hour=0, minute=0, second=0, microsecond=0)
    ).count()
    last = base.with_entities(func.max(StationData.RecordTime)).scalar()

    result = {
        "generated_at": now,
        "timeout_minutes": Settings.load_settings().get(
            "DATA_TIMEOUT_MINUTES", statictext.DATA_TIMEOUT_MINUTES
        ),
        "stations": {
            "total": len(live["data"]),
            "counts": counts,
            "attention": attention[:50],
        },
        "payloads": {"today": today, "last": last, "series": series},
        "http": HttpLog.counters(dict(scoped)),
        "events": EventLog.counters(dict(scoped)),
        "worker": None,
        "system": None,
    }
    if current_user.UserType in ADMINS:
        result["worker"] = scheduler.status()
        result["system"] = sysinfo.snapshot(scheduler.STARTED_AT)
    return jsonify(result)


@main_bp.route("/cleartmp", methods=["GET", "POST"])
@require_types(*ADMINS)
def clear_tmp():
    """Manual trigger of the tmp/ upload cleanup (the worker's retention job
    runs the same rule daily)."""
    from services.retention import purge_tmp_uploads

    response_code = 200
    return (
        jsonify(
            {
                "message": statictext.ResponseCode[response_code],
                "status": response_code,
                "deleted_files": purge_tmp_uploads(),
            }
        ),
        response_code,
    )
