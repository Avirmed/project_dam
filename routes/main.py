import os
import time

from flask import request
from flask import Blueprint, jsonify, request

from models import Settings
from util import statictext

main_bp = Blueprint("main_bp", __name__)


@main_bp.route("/init", methods=["GET", "POST"])
def init():
    excluded_keys = {
        "os",
        "util",
        "APP_STATIC_PATH",
        "APP_DIRECTORY",
        "APP_TMP_PATH",
        "APP_CERT_PATH",
        "EVENT_IMAGE_PATH",
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
def clear_tmp():
    expire_time = time.time() - 24 * 60 * 60
    deleted_files = []

    for file in os.listdir(statictext.APP_TMP_PATH):
        file_path = os.path.join(statictext.APP_TMP_PATH, file)
        if os.path.isfile(file_path) and os.path.getmtime(file_path) < expire_time:
            try:
                os.remove(file_path)
                deleted_files.append(file)
            except Exception as e:
                print(f"Файл устгах үед алдаа гарлаа: {file_path} -> {e}")

    response_code = 200
    return (
        jsonify(
            {
                "message": statictext.ResponseCode[response_code],
                "status": response_code,
                "deleted_files": deleted_files,
            }
        ),
        response_code,
    )
