import os
from flask_login import LoginManager
from flask.json.provider import DefaultJSONProvider
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import timedelta
from models import User
from datetime import datetime, date


def setup_logging(debug: bool) -> None:
    os.makedirs("logs", exist_ok=True)

    file_handler = TimedRotatingFileHandler(
        os.path.join("logs", "app.log"),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.suffix = "%Y-%m-%d"
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )

    handlers: list[logging.Handler] = [file_handler]

    if debug:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        handlers.append(console_handler)

    logging.basicConfig(level=logging.INFO, handlers=handlers, force=True)

    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.setLevel(logging.ERROR)
    werkzeug_logger.propagate = False


def init_login_manager(app):
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.session_protection = "basic"
    login_manager.remember_cookie_duration = timedelta(days=7)
    login_manager.login_view = "/dashboard/login"

    @login_manager.user_loader
    def user_loader(user_id):
        return User.load_user(user_id)


class CustomJSONProvider(DefaultJSONProvider):
    def __init__(self, app):
        super().__init__(app)

        self.ensure_ascii = False
        self.sort_keys = False

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(obj, date):
            return obj.strftime("%Y-%m-%d")
        return super().default(obj)
