import time

from flask import Blueprint, render_template, request, redirect, jsonify
from flask_login import login_required, current_user

from models import Settings
from util import statictext

from util.auth import require_types, ADMINS

dashboard_bp = Blueprint("dashboard_bp", __name__)


@dashboard_bp.route("/login")
def login():
    if current_user.is_authenticated:
        return redirect("/dashboard")

    return render_template(
        "dashboard/login.html",
        StaticText=statictext,
        Settings=Settings.load_settings(),
        time=int(time.time()),
    )


@dashboard_bp.route("/", defaults={"module": "main", "cid": None})
@dashboard_bp.route("/<string:module>", defaults={"cid": None})
@dashboard_bp.route("/<string:module>/<int:cid>")
@login_required
def dashboard(module="main", cid=None):
    return render_template(
        "dashboard/index.html",
        Module=module,
        contentid=cid,
        current_path="/dashboard" if module == "main" else f"/dashboard/{module}",
        User=current_user,
        StaticText=statictext,
        Settings=Settings.load_settings(),
        time=int(time.time()),
    )


@dashboard_bp.route("/settings/save", methods=["POST"])
@require_types(*ADMINS)
def save():
    get_data = request.args.to_dict()
    post_data = (
        request.get_json() if request.is_json else request.form.to_dict()
    ) or {}
    requestData = {**get_data, **post_data}

    jsonResult = Settings.save(requestData)

    return jsonify(jsonResult), jsonResult["Code"]
