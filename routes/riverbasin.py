import os
import shutil

from flask import Blueprint, request, jsonify, abort
from flask_login import current_user, login_required

from models import (
    RiverBasin,
    Station,
    Team,
)

from util import statictext, util

from util.auth import require_types, MANAGERS

riverbasin_bp = Blueprint("riverbasin_bp", __name__)


@riverbasin_bp.route("/get/<int:id>")
@login_required
def get(id):
    if not str(id).isdigit():
        error_code = 400
        abort(error_code, description=statictext.ResponseCode[error_code])

    object_data = RiverBasin.getData(id)
    if object_data is None:
        error_code = 404
        abort(error_code, description=statictext.ResponseCode[error_code])

    return jsonify(object_data)


@riverbasin_bp.route("/detail", methods=["POST"])
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

    object_data = RiverBasin.getData(objID, True)

    if object_data is None:
        error_code = 404
        jsonResult.update(
            {"Message": f"{statictext.ResponseCode[error_code]}", "Code": error_code}
        )
        return jsonify(jsonResult), jsonResult["Code"]

    jsonResult = {"Result": True, "Code": 200, "Data": object_data}

    return jsonify(jsonResult), jsonResult["Code"]


@riverbasin_bp.route("/list", methods=["GET", "POST"])
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

    # Staff / Guest only see basins of their teams' stations (fail-closed).
    scope = Team.scope_station_ids()
    if scope is not None:
        stations = Station.query.filter(Station.StationID.in_(scope)).all()
        requestData["filters"]["RiverBasinID"] = sorted(
            {s.RiverBasinID for s in stations if s.RiverBasinID}
        ) or [-1]

    jsonResult = RiverBasin.list(requestData)

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
            "title": statictext.RiverBasinField["RiverBasinID"],
            "field": "RiverBasinID",
            "visible": False,
        },
        {
            "title": statictext.RiverBasinField["ImageSource"],
            "field": "Image",
            "width": 70,
            "headerHozAlign": "center",
            "hozAlign": "center",
            "vertAlign": "middle",
            "headerSort": False,
        },
        {
            "title": statictext.RiverBasinField["WatershedName"],
            "field": "WatershedName",
            "formatter": "textarea",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": True,
        },
        {
            "title": statictext.RiverBasinField["SortOrder"],
            "field": "SortOrder",
            "width": 100,
            "headerHozAlign": "center",
            "hozAlign": "center",
            "vertAlign": "middle",
            "headerSort": True,
        },
        {
            "title": statictext.RiverBasinField["Status"],
            "field": "Status",
            "width": 100,
            "headerHozAlign": "center",
            "hozAlign": "center",
            "vertAlign": "middle",
            "formatter": "tickCross",
            "headerSort": False,
        },
        {
            "title": statictext.RiverBasinField["Remark"],
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
                "title": statictext.RiverBasinField["RiverBasinID"],
                "field": "RiverBasinID",
                "visible": False,
            },
            {
                "title": statictext.RiverBasinField["ImageSource"],
                "field": "Image",
                "width": 70,
                "headerHozAlign": "center",
                "hozAlign": "center",
                "vertAlign": "middle",
                "headerSort": False,
            },
            {
                "title": statictext.RiverBasinField["WatershedName"],
                "field": "WatershedName",
                "formatter": "textarea",
                "headerHozAlign": "center",
                "vertAlign": "middle",
                "headerSort": True,
            },
        ]

    return jsonify(jsonResult)


@riverbasin_bp.route("/save", methods=["POST"])
@require_types(*MANAGERS)
def save():
    get_data = request.args.to_dict()
    post_data = (
        request.get_json() if request.is_json else request.form.to_dict()
    ) or {}
    requestData = {**get_data, **post_data}

    jsonResult = RiverBasin.save(requestData)

    return jsonify(jsonResult), jsonResult["Code"]


@riverbasin_bp.route("/delete", methods=["POST"])
@require_types(*MANAGERS)
def delete():
    get_data = request.args.to_dict()
    post_data = (
        request.get_json() if request.is_json else request.form.to_dict()
    ) or {}
    requestData = {**get_data, **post_data}

    jsonResult = RiverBasin.delete(requestData)

    return jsonify(jsonResult), jsonResult["Code"]


@riverbasin_bp.route("/fileupload", methods=["POST"])
@require_types(*MANAGERS)
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
        object = RiverBasin.query.get(contentid)
        if not object:
            try:
                os.remove(final_file_path)
            except Exception:
                pass
            error_code = 404
            abort(error_code, description=statictext.ResponseCode[error_code])

        dest_path = os.path.join(RiverBasin.drfFilePath, filename)
        shutil.move(final_file_path, dest_path)
        object.updateImage(filename)
        return jsonify(object.serialize())

    return filename, 200


@riverbasin_bp.route("/imgrotate", methods=["POST"])
@require_types(*MANAGERS)
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

    object_id = requestData.get("RiverBasinID")
    direction = requestData.get("direction", None)

    if not object_id:
        error_code = 400
        jsonResult.update(
            {"Message": f"{statictext.ResponseCode[error_code]}", "Code": error_code}
        )
        return jsonify(jsonResult), jsonResult["Code"]

    try:
        object = RiverBasin.query.get(object_id)

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
