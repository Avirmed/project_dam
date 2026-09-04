from flask import Blueprint, request, jsonify, abort
from flask_login import login_required

from models import (
    Camera,
)

from util import statictext

from util.auth import require_types, EDITORS

camera_bp = Blueprint("camera_bp", __name__)


@camera_bp.route("/get/<int:id>")
@login_required
def get(id):
    if not str(id).isdigit():
        error_code = 400
        abort(error_code, description=statictext.ResponseCode[error_code])

    object_data = Camera.getData(id)
    if object_data is None:
        error_code = 404
        abort(error_code, description=statictext.ResponseCode[error_code])

    return jsonify(object_data)


@camera_bp.route("/detail", methods=["POST"])
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

    object_data = Camera.getData(objID, True)

    if object_data is None:
        error_code = 404
        jsonResult.update(
            {"Message": f"{statictext.ResponseCode[error_code]}", "Code": error_code}
        )
        return jsonify(jsonResult), jsonResult["Code"]

    jsonResult = {"Result": True, "Code": 200, "Data": object_data}

    return jsonify(jsonResult), jsonResult["Code"]


@camera_bp.route("/list", methods=["GET", "POST"])
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

    jsonResult = Camera.list(requestData)

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
        {"title": statictext.CameraField["ID"], "field": "ID", "visible": False},
        {
            "title": statictext.CameraField["CameraID"],
            "field": "CameraID",
            "formatter": "textarea",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": True,
        },
        {
            "title": statictext.CameraField["CameraName"],
            "field": "CameraName",
            "formatter": "textarea",
            "headerHozAlign": "center",
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
            "title": statictext.CameraField["LastUploadResult"],
            "field": "LastUploadResult",
            "width": "18%",
            "formatter": "textarea",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": False,
        },
        {
            "title": statictext.CameraField["Remark"],
            "field": "Remark",
            "width": "20%",
            "formatter": "textarea",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": False,
        },
    ]

    return jsonify(jsonResult)


@camera_bp.route("/save", methods=["POST"])
@require_types(*EDITORS)
def save():
    get_data = request.args.to_dict()
    post_data = (
        request.get_json() if request.is_json else request.form.to_dict()
    ) or {}
    requestData = {**get_data, **post_data}

    jsonResult = Camera.save(requestData)

    return jsonify(jsonResult), jsonResult["Code"]


def _camera_from_request():
    """(camera, error json) for the model upload / delete endpoints."""
    camera_id = request.form.get("id", "")
    kind = request.form.get("kind", "TrainedModel")
    if not str(camera_id).isdigit() or kind != "TrainedModel":
        return None, {"Message": statictext.ResponseCode[400], "Code": 400}
    camera = Camera.query.get(int(camera_id))
    if not camera:
        return None, {"Message": statictext.ResponseCode[404], "Code": 404}
    return camera, None


@camera_bp.route("/modelupload", methods=["POST"])
@require_types(*EDITORS)
def model_upload():
    """Store the camera's YOLO weights (.pt) as ai/trained_models/<CameraID>.pt
    (Camera.store_model). Only the file name goes back to the form / Meta."""
    jsonResult = {
        "Result": False,
        "Title": statictext.Messages["Title"],
        "Message": statictext.Messages["InvalidAccess"],
        "Code": 400,
    }

    file = request.files.get("file")
    camera, error = _camera_from_request()
    if error or not file:
        jsonResult.update(
            error or {"Message": statictext.ResponseCode[400], "Code": 400}
        )
        return jsonify(jsonResult), jsonResult["Code"]

    try:
        filename = camera.store_model(file)
    except ValueError as e:
        jsonResult.update({"Message": str(e), "Code": 422})
        return jsonify(jsonResult), jsonResult["Code"]
    except Exception as e:
        jsonResult.update(
            {"Message": f"{statictext.ResponseCode[500]}: {str(e)}", "Code": 500}
        )
        return jsonify(jsonResult), jsonResult["Code"]

    jsonResult.update(
        {
            "Result": True,
            "Message": statictext.Messages["ModelUploaded"],
            "Code": 200,
            "Filename": filename,
        }
    )
    return jsonify(jsonResult), jsonResult["Code"]


@camera_bp.route("/modeldelete", methods=["POST"])
@require_types(*EDITORS)
def model_delete():
    """Remove the camera's uploaded weights file and clear Meta.TrainedModel."""
    jsonResult = {
        "Result": False,
        "Title": statictext.Messages["Title"],
        "Message": statictext.Messages["InvalidAccess"],
        "Code": 400,
    }

    camera, error = _camera_from_request()
    if error:
        jsonResult.update(error)
        return jsonify(jsonResult), jsonResult["Code"]

    try:
        camera.remove_model()
    except Exception as e:
        jsonResult.update(
            {"Message": f"{statictext.ResponseCode[500]}: {str(e)}", "Code": 500}
        )
        return jsonify(jsonResult), jsonResult["Code"]

    jsonResult.update(
        {"Result": True, "Message": statictext.Messages["ModelDeleted"], "Code": 200}
    )
    return jsonify(jsonResult), jsonResult["Code"]


@camera_bp.route("/delete", methods=["POST"])
@require_types(*EDITORS)
def delete():
    get_data = request.args.to_dict()
    post_data = (
        request.get_json() if request.is_json else request.form.to_dict()
    ) or {}
    requestData = {**get_data, **post_data}

    jsonResult = Camera.delete(requestData)

    return jsonify(jsonResult), jsonResult["Code"]
