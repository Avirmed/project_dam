from flask import render_template, redirect, url_for
from flask_login import login_required, current_user

from util import statictext
from models import Settings

import time


def register_blueprints(app):
    from routes import (
        main_bp,
        ckfinder_bp,
        dashboard_bp,
        user_bp,
        project_bp,
        riverbasin_bp,
        station_bp,
        sensor_bp,
        camera_bp,
        sampling_bp,
        area_bp,
        team_bp,
        filetransfer_bp,
        http_bp,
        csvlogger_bp,
        httplog_bp,
        stationdata_bp,
        inbound_bp,
        eventlog_bp,
    )

    @app.route("/", defaults={"module": "main", "cid": None})
    @app.route("/<string:module>", defaults={"cid": None})
    @app.route("/<string:module>/<int:cid>")
    def index(module: str = "main", cid: int | None = None):
        if not current_user.is_authenticated and module != "main":
            return redirect(url_for("index"))

        return render_template(
            "modules/index.html",
            Module=module,
            contentid=cid,
            current_path="/" if module == "main" else f"/{module}",
            User=current_user,
            StaticText=statictext,
            Settings=Settings.load_settings(),
            time=int(time.time()),
        )

    @app.route("/logout")
    @login_required
    def logout():
        current_user.logout()
        return redirect("dashboard")

    app.register_blueprint(main_bp, url_prefix="/main")
    app.register_blueprint(ckfinder_bp, url_prefix="/ck")
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")

    api_list = [
        (user_bp, "/users"),
        (project_bp, "/projects"),
        (riverbasin_bp, "/riverbasins"),
        (station_bp, "/stations"),
        (sensor_bp, "/sensors"),
        (camera_bp, "/cameras"),
        (sampling_bp, "/samplings"),
        (area_bp, "/areas"),
        (team_bp, "/teams"),
        (filetransfer_bp, "/filetransfer"),
        (http_bp, "/http"),
        (csvlogger_bp, "/csvlogger"),
        (httplog_bp, "/httplog"),
        (stationdata_bp, "/stationdata"),
        # Device-facing REST API server: POST /api/inbound/<DeviceID> (no login;
        # gated by each station's own API settings).
        (inbound_bp, "/inbound"),
        (eventlog_bp, "/eventlog"),
    ]

    for bp, prefix in api_list:
        app.register_blueprint(bp, url_prefix=f"/api{prefix}")
