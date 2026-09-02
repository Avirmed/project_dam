from flask import Blueprint, jsonify, request

from models import Settings
from util import statictext
from util.auth import require_types, ADMINS

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
