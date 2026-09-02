from flask import Blueprint, request, jsonify, abort
from flask_login import login_required

from models import (
    Sampling,
)

from util import statictext

from util.auth import require_types, EDITORS

sampling_bp = Blueprint("sampling_bp", __name__)


@sampling_bp.route("/get/<int:id>")
@login_required
def get(id):
    if not str(id).isdigit():
        error_code = 400
        abort(error_code, description=statictext.ResponseCode[error_code])

    sampling_data = Sampling.getData(id)
    if sampling_data is None:
        error_code = 404
        abort(error_code, description=statictext.ResponseCode[error_code])

    return jsonify(sampling_data)


@sampling_bp.route("/detail", methods=["POST"])
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

    sampling_data = Sampling.getData(objID, True)

    if sampling_data is None:
        error_code = 404
        jsonResult.update(
            {"Message": f"{statictext.ResponseCode[error_code]}", "Code": error_code}
        )
        return jsonify(jsonResult), jsonResult["Code"]

    jsonResult = {"Result": True, "Code": 200, "Data": sampling_data}

    return jsonify(jsonResult), jsonResult["Code"]


@sampling_bp.route("/list", methods=["GET", "POST"])
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

    jsonResult = Sampling.list(requestData)

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
        {"title": statictext.SamplingField["ID"], "field": "ID", "visible": False},
        {
            "title": statictext.SamplingField["SamplingID"],
            "field": "SamplingID",
            "formatter": "textarea",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": True,
        },
        {
            "title": statictext.SamplingField["SamplingName"],
            "field": "SamplingName",
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
            "title": statictext.SamplingField["Remark"],
            "field": "Remark",
            "width": "20%",
            "formatter": "textarea",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": False,
        },
    ]

    return jsonify(jsonResult)


@sampling_bp.route("/save", methods=["POST"])
@require_types(*EDITORS)
def save():
    get_data = request.args.to_dict()
    post_data = (
        request.get_json() if request.is_json else request.form.to_dict()
    ) or {}
    requestData = {**get_data, **post_data}

    jsonResult = Sampling.save(requestData)

    return jsonify(jsonResult), jsonResult["Code"]


@sampling_bp.route("/delete", methods=["POST"])
@require_types(*EDITORS)
def delete():
    get_data = request.args.to_dict()
    post_data = (
        request.get_json() if request.is_json else request.form.to_dict()
    ) or {}
    requestData = {**get_data, **post_data}

    jsonResult = Sampling.delete(requestData)

    return jsonify(jsonResult), jsonResult["Code"]
