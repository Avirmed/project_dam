import os
import hashlib
import shutil

from flask import Blueprint, request, jsonify, abort
from flask_login import current_user, login_required

from models import (
    Project,
    Station,
    Team,
)

from util import statictext

project_bp = Blueprint("project_bp", __name__)


@project_bp.route("/get/<int:id>")
@login_required
def get(id):
    if not str(id).isdigit():
        error_code = 400
        abort(error_code, description=statictext.ResponseCode[error_code])

    object_data = Project.getData(id)
    if object_data is None:
        error_code = 404
        abort(error_code, description=statictext.ResponseCode[error_code])

    return jsonify(object_data)


@project_bp.route("/detail", methods=["POST"])
@login_required
def getByPost():
    get_data = request.args.to_dict()
    post_data = (
        request.get_json() if request.is_json else request.form.to_dict()
    ) or {}
    requestData = {**get_data, **post_data}

    jsonResult = {
        "Result": False,
        "Title": statictext.Messages["Title"],
        "Message": statictext.Messages["InvalidAccess"],
        "Code": 400,
    }

    objID = requestData.get("cid")

    if not objID:
        error_code = 404
        jsonResult.update(
            {"Message": f"{statictext.ResponseCode[error_code]}", "Code": error_code}
        )
        return jsonify(jsonResult), jsonResult["Code"]

    object_data = Project.getData(objID, True)

    if object_data is None:
        error_code = 404
        jsonResult.update(
            {"Message": f"{statictext.ResponseCode[error_code]}", "Code": error_code}
        )
        return jsonify(jsonResult), jsonResult["Code"]

    jsonResult = {"Result": True, "Code": 200, "Data": object_data}

    return jsonify(jsonResult), jsonResult["Code"]


@project_bp.route("/list", methods=["GET", "POST"])
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

    if current_user.is_authenticated and current_user.UserType in [3, 4]:
        teamsData = Team.get_user_teams(current_user.UserID)

        StationIDs = []
        for data in teamsData:
            for id in data["RiverBasins"]:
                StationIDs.append(id)

        stations = Station.query.filter(Station.StationID.in_(StationIDs)).all()
        ProjectIDs = []
        for station in stations:
            if station.ProjectID not in ProjectIDs:
                ProjectIDs.append(station.ProjectID)

        if len(ProjectIDs) > 0:
            requestData["filters"]["ProjectID"] = ProjectIDs

    jsonResult = Project.list(requestData)

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
        {
            "title": statictext.ProjectField["ProjectID"],
            "field": "ProjectID",
            "visible": False,
        },
        {
            "title": statictext.ProjectField["ImageSource"],
            "field": "Image",
            "width": 70,
            "headerHozAlign": "center",
            "hozAlign": "center",
            "vertAlign": "middle",
            "headerSort": False,
        },
        {
            "title": statictext.ProjectField["ProjectName"],
            "field": "ProjectName",
            "formatter": "textarea",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": True,
        },
        {
            "title": statictext.ProjectField["CustomerName"],
            "field": "CustomerName",
            "formatter": "textarea",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": True,
        },
        {
            "title": statictext.ProjectField["SortOrder"],
            "field": "SortOrder",
            "width": 100,
            "headerHozAlign": "center",
            "hozAlign": "center",
            "vertAlign": "middle",
            "headerSort": True,
        },
        {
            "title": statictext.ProjectField["Status"],
            "field": "Status",
            "width": 100,
            "headerHozAlign": "center",
            "hozAlign": "center",
            "vertAlign": "middle",
            "formatter": "tickCross",
            "headerSort": False,
        },
        {
            "title": statictext.ProjectField["Remark"],
            "field": "Remark",
            "width": 200,
            "formatter": "textarea",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": False,
        },
    ]

    if requestData.get("viewType") == "simple":
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
            {
                "title": statictext.ProjectField["ProjectID"],
                "field": "ProjectID",
                "visible": False,
            },
            {
                "title": statictext.ProjectField["ImageSource"],
                "field": "Image",
                "width": 70,
                "headerHozAlign": "center",
                "hozAlign": "center",
                "vertAlign": "middle",
                "headerSort": False,
            },
            {
                "title": statictext.ProjectField["ProjectName"],
                "field": "ProjectName",
                "formatter": "textarea",
                "headerHozAlign": "center",
                "vertAlign": "middle",
                "headerSort": True,
            },
        ]

    return jsonify(jsonResult)


@project_bp.route("/save", methods=["POST"])
@login_required
def save():
    get_data = request.args.to_dict()
    post_data = (
        request.get_json() if request.is_json else request.form.to_dict()
    ) or {}
    requestData = {**get_data, **post_data}

    jsonResult = Project.save(requestData)

    return jsonify(jsonResult), jsonResult["Code"]


@project_bp.route("/delete", methods=["POST"])
@login_required
def delete():
    get_data = request.args.to_dict()
    post_data = (
        request.get_json() if request.is_json else request.form.to_dict()
    ) or {}
    requestData = {**get_data, **post_data}

    jsonResult = Project.delete(requestData)

    return jsonify(jsonResult), jsonResult["Code"]


@project_bp.route("/fileupload", methods=["POST"])
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

    file_ext = os.path.splitext(file_real_name)[1].lstrip(".")
    hash_str = hashlib.md5((file_real_name + upload_time).encode()).hexdigest()
    filename = f"{upload_time}_{hash_str}.{file_ext}"

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
        object = Project.query.get(contentid)
        if not object:
            try:
                os.remove(final_file_path)
            except Exception:
                pass
            error_code = 404
            abort(error_code, description=statictext.ResponseCode[error_code])

        dest_path = os.path.join(Project.drfFilePath, filename)
        shutil.move(final_file_path, dest_path)
        object.updateImage(filename)
        return jsonify(object.serialize())

    return filename, 200


@project_bp.route("/imgrotate", methods=["POST"])
def imgrotate():
    if not current_user.is_authenticated:
        error_code = 401
        abort(error_code, description=statictext.ResponseCode[error_code])

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

    object_id = requestData.get("ProjectID")
    direction = requestData.get("direction", None)

    if not object_id:
        error_code = 400
        jsonResult.update(
            {"Message": f"{statictext.ResponseCode[error_code]}", "Code": error_code}
        )
        return jsonify(jsonResult), jsonResult["Code"]

    try:
        object = Project.query.get(object_id)

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
