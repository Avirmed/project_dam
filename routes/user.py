import os
import shutil

from flask import Blueprint, request, jsonify, abort
from flask_login import login_user, current_user, login_required
from sqlalchemy import func

from models import (
    User,
    Team,
)

from util import util, statictext

user_bp = Blueprint("user_bp", __name__)


@user_bp.route("/<id>", methods=["GET"])
def get(id):
    if not current_user.is_authenticated:
        error_code = 404
        abort(error_code, description=statictext.ResponseCode[error_code])

    if not str(id).isdigit():
        error_code = 400
        abort(error_code, description=statictext.ResponseCode[error_code])

    object_data = User.getData(id)
    if object_data is None:
        error_code = 404
        abort(error_code, description=statictext.ResponseCode[error_code])

    return jsonify(object_data)


@user_bp.route("/save", methods=["POST"])
@login_required
def save():
    get_data = request.args.to_dict()
    post_data = (
        request.get_json() if request.is_json else request.form.to_dict()
    ) or {}
    requestData = {**get_data, **post_data}

    jsonResult = User.save(requestData)

    return jsonify(jsonResult), jsonResult["Code"]


@user_bp.route("/delete", methods=["POST"])
@login_required
def delete():
    get_data = request.args.to_dict()
    post_data = (
        request.get_json() if request.is_json else request.form.to_dict()
    ) or {}
    requestData = {**get_data, **post_data}

    jsonResult = User.delete(requestData)

    return jsonify(jsonResult), jsonResult["Code"]


@user_bp.route("/list", methods=["GET", "POST"])
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

    jsonResult = User.list(requestData)

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
        {"title": statictext.UserField["UserID"], "field": "UserID", "visible": False},
        {
            "title": statictext.UserField["Image"],
            "field": "Image",
            "width": 70,
            "headerHozAlign": "center",
            "hozAlign": "center",
            "headerSort": False,
        },
        {
            "title": statictext.UserField["FirstName"],
            "field": "FirstName",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "sorter": "string",
        },
        {
            "title": statictext.UserField["LastName"],
            "field": "LastName",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "sorter": "string",
        },
        {
            "title": statictext.UserField["UserName"],
            "field": "UserName",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "sorter": "string",
        },
        {
            "title": statictext.UserField["Email"],
            "field": "Email",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "sorter": "string",
        },
        {
            "title": statictext.UserField["UserType"],
            "field": "UserType",
            "width": 200,
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "sorter": "string",
        },
        {
            "title": statictext.Status,
            "field": "Status",
            "width": 80,
            "headerHozAlign": "center",
            "hozAlign": "center",
            "vertAlign": "middle",
            "formatter": "tickCross",
            "headerSort": False,
        },
    ]

    if requestData.get("viewType") == "checkbox":
        jsonResult["column"] = [
            {
                "title": "",
                "field": "checkbox",
                "formatter": "checkbox",
                "width": 50,
                "headerHozAlign": "center",
                "hozAlign": "center",
                "vertAlign": "middle",
                "headerSort": False,
                "resizable": False,
            },
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
                "title": statictext.UserField["UserID"],
                "field": "UserID",
                "visible": False,
            },
            {
                "title": statictext.UserField["Image"],
                "field": "Image",
                "width": 40,
                "headerHozAlign": "center",
                "hozAlign": "center",
                "headerSort": False,
            },
            {
                "title": statictext.UserField["FirstName"],
                "field": "FirstName",
                "headerHozAlign": "center",
                "vertAlign": "middle",
                "sorter": "string",
            },
            {
                "title": statictext.UserField["LastName"],
                "field": "LastName",
                "headerHozAlign": "center",
                "vertAlign": "middle",
                "sorter": "string",
            },
            {
                "title": statictext.UserField["UserName"],
                "field": "UserName",
                "headerHozAlign": "center",
                "vertAlign": "middle",
                "sorter": "string",
            },
            {
                "title": statictext.UserField["Email"],
                "field": "Email",
                "headerHozAlign": "center",
                "vertAlign": "middle",
                "sorter": "string",
            },
        ]

        if requestData.get("TeamID"):
            team_data = Team.getData(requestData.get("TeamID"))

            if team_data and "Users" in team_data and len(team_data["Users"]) > 0:
                for data in jsonResult["data"]:
                    data["checkbox"] = data["UserID"] in team_data["Users"]

    return jsonify(jsonResult)


@user_bp.route("/login", methods=["POST"])
def login():
    jsonResult = {
        "Result": False,
        "Title": statictext.Messages["Title"],
        "Message": statictext.Messages["InvalidAccess"],
        "Code": 400,
    }

    if request.method == "POST":
        username = request.form.get("UserName", None)
        password = request.form.get("Password", None)
        rememberme = "RememberMe" in request.form

        if username is not None and password is not None:
            username = username.strip()
            password = password.strip()

            object = User.query.filter(
                func.lower(User.UserName) == func.lower(username)
            ).first()

            if object and not object.Status:
                jsonResult.update(
                    {"Message": statictext.Messages["LoginFailed"], "Code": 403}
                )
                return jsonify(jsonResult), jsonResult["Code"]

            if object and object.check_password(password):
                login_user(object, remember=rememberme)
                object.update_token()

                jsonResult["Data"] = {
                    "UserType": object.UserType,
                    "Permission": statictext.UserTypes.get(object.UserType),
                    "Theme": object.Theme,
                }

                if rememberme:
                    jsonResult["Data"].update(
                        {
                            "Auth": util.app_encrypt(object.UserID),
                            "Token": object.AccessToken,
                        }
                    )

                jsonResult.update(
                    {
                        "Result": True,
                        "Message": statictext.Messages["LoginSuccess"],
                        "Code": 200,
                    }
                )

            else:
                jsonResult.update(
                    {"Message": statictext.Messages["LoginFailed"], "Code": 401}
                )

    return jsonify(jsonResult), jsonResult["Code"]


@user_bp.route("/logout", methods=["GET", "POST"])
def logout():
    jsonResult = {
        "Result": False,
        "Title": statictext.Messages["Title"],
        "Message": statictext.Messages["InvalidAccess"],
        "Code": 400,
    }

    if current_user.is_authenticated:
        current_user.logout()

        jsonResult.update(
            {
                "Result": True,
                "Message": statictext.Messages["LogoutSuccess"],
                "Code": 200,
            }
        )

    return jsonify(jsonResult), jsonResult["Code"]


@user_bp.route("/check", methods=["POST"])
def check():
    requestData = (
        request.get_json() if request.is_json else request.form.to_dict()
    ) or {}

    jsonResult = User.check(requestData)

    return jsonify(jsonResult), jsonResult["Code"]


@user_bp.route("/fileupload", methods=["POST"])
@login_required
def file_upload():
    file = request.files.get("file")
    file_real_name = request.form.get("filename")
    upload_time = request.form.get("time")

    if not file or not file_real_name or not upload_time:
        error_code = 404
        abort(error_code, description=statictext.ResponseCode[error_code])

    part = int(request.form.get("part", 0))
    lastPart = request.form.get("lastPart", "").lower() in ("1", "true", "yes")
    contentid = request.form.get("contentid", None)

    file_ext = util.get_safe_extension(file_real_name)
    if not file_ext:
        error_code = 400
        abort(error_code, description=statictext.ResponseCode[error_code])

    filename = util.build_upload_filename(upload_time, file_real_name, file_ext)

    part_file = os.path.join(statictext.APP_TMP_PATH, f"{filename}.part{part}")
    final_file_path = os.path.join(statictext.APP_TMP_PATH, filename)

    file.save(part_file)

    success = False
    for _ in range(10):
        try:
            with open(final_file_path, "ab") as f_out:
                with open(part_file, "rb") as f_in:
                    f_out.write(f_in.read())
            success = True
            break
        except Exception as e:
            continue

    try:
        os.remove(part_file)
    except Exception as e:
        print(f"{statictext.Messages['FileDeleteError']}: {part_file} -> {e}")

    if not success:
        error_code = 500
        abort(error_code, description=statictext.ResponseCode[error_code])

    if lastPart:
        object = User.query.get(contentid)
        if not object:
            try:
                os.remove(final_file_path)
            except Exception:
                pass
            error_code = 404
            abort(error_code, description=statictext.ResponseCode[error_code])

        dest_path = os.path.join(User.drfFilePath, filename)
        shutil.move(final_file_path, dest_path)
        object.updateImage(filename)
        return jsonify(object.serialize())

    return filename, 200


@user_bp.route("/imgrotate", methods=["POST"])
@login_required
def imgrotate():
    jsonResult = {
        "Result": False,
        "Title": statictext.Messages["Title"],
        "Message": statictext.Messages["InvalidAccess"],
        "Code": 400,
    }

    get_data = request.args.to_dict()
    post_data = (
        request.get_json() if request.is_json else request.form.to_dict()
    ) or {}
    requestData = {**get_data, **post_data}

    object_id = requestData.get("UserID")
    direction = requestData.get("direction", None)

    if not object_id:
        error_code = 400
        jsonResult.update(
            {
                "Message": f"{statictext.ResponseCode[error_code]}",
                "Code": error_code,
            }
        )
        return jsonify(jsonResult), jsonResult["Code"]

    try:
        object = User.query.get(object_id)

        jsonResult.update(
            {
                "Result": True,
                "Data": object.rotateImage(direction),
                "Message": statictext.Messages["SuccessSaved"],
                "Code": 200,
            }
        )

    except Exception as e:
        error_code = 500
        jsonResult.update(
            {
                "Message": f"{statictext.ResponseCode[error_code]}: {str(e)}",
                "Code": error_code,
            }
        )

    return jsonify(jsonResult), jsonResult["Code"]
