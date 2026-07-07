import logging
import re
from flask import request, jsonify
from flask_login import current_user
from models import User
from datetime import datetime


def register_handlers(app):
    @app.before_request
    def log_request_info():
        path = request.path
        skip_paths = ["/static", "/favicon.ico", "/.well-known"]
        if not any(path.startswith(p) for p in skip_paths):
            logging.info(
                f"Request: {request.method} {path} | User: {current_user.get_id()}"
            )

    @app.errorhandler(404)
    def page_not_found(e):
        return jsonify(error="Not found"), 404

    @app.template_filter("strftime")
    def strftime_filter(timestamp, format="%Y-%m-%d %H:%M:%S"):
        if timestamp is None:
            return ""
        date = datetime.fromtimestamp(float(timestamp))
        return date.strftime(format)
