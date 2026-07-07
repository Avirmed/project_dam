from flask import Blueprint, request, jsonify, abort
from flask_login import login_required

from models import (
    Area,
)

from util import statictext

area_bp = Blueprint("area_bp", __name__)


@area_bp.route("/get/<int:id>")
@login_required
def get(id):
    if not str(id).isdigit():
        error_code = 400
        abort(error_code, description=statictext.ResponseCode[error_code])

    area_data = Area.getData(id)
    if area_data is None:
        error_code = 404
        abort(error_code, description=statictext.ResponseCode[error_code])

    return jsonify(area_data)


@area_bp.route("/detail", methods=["POST"])
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

    area_data = Area.getData(objID, True)

    if area_data is None:
        error_code = 404
        jsonResult.update(
            {"Message": f"{statictext.ResponseCode[error_code]}", "Code": error_code}
        )
        return jsonify(jsonResult), jsonResult["Code"]

    jsonResult = {"Result": True, "Code": 200, "Data": area_data}

    return jsonify(jsonResult), jsonResult["Code"]


@area_bp.route("/list", methods=["GET", "POST"])
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

    jsonResult = Area.list(requestData)

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
        {"title": statictext.AreaField["ID"], "field": "ID", "visible": False},
        {
            "title": statictext.AreaField["AreaID"],
            "field": "AreaID",
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
            "title": statictext.AreaField["Remark"],
            "field": "Remark",
            "width": "20%",
            "formatter": "textarea",
            "headerHozAlign": "center",
            "vertAlign": "middle",
            "headerSort": False,
        },
    ]

    return jsonify(jsonResult)


@area_bp.route("/save", methods=["POST"])
@login_required
def save():
    get_data = request.args.to_dict()
    post_data = (
        request.get_json() if request.is_json else request.form.to_dict()
    ) or {}
    requestData = {**get_data, **post_data}

    jsonResult = Area.save(requestData)

    return jsonify(jsonResult), jsonResult["Code"]


@area_bp.route("/delete", methods=["POST"])
@login_required
def delete():
    get_data = request.args.to_dict()
    post_data = (
        request.get_json() if request.is_json else request.form.to_dict()
    ) or {}
    requestData = {**get_data, **post_data}

    jsonResult = Area.delete(requestData)

    return jsonify(jsonResult), jsonResult["Code"]
