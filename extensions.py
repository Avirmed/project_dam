import os
import sys
from flask_login import LoginManager
from flask.json.provider import DefaultJSONProvider
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import timedelta
from models import User
from datetime import datetime, date


def setup_logging(debug: bool) -> None:
    os.makedirs("logs", exist_ok=True)

    handlers: list[logging.Handler] = []

    is_reloader_watcher = debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true"

    if not is_reloader_watcher:
        file_handler = TimedRotatingFileHandler(
            os.path.join("logs", "app.log"),
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8",
            delay=True,
        )
        file_handler.suffix = "%Y-%m-%d"
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        handlers.append(file_handler)

    if debug:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        handlers.append(console_handler)

    # Log level follows the run mode (no env needed): INFO while debugging,
    # WARNING in production.
    log_level = logging.INFO if debug else logging.WARNING

    logging.basicConfig(level=log_level, handlers=handlers, force=True)

    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.setLevel(log_level)
    # In debug, let request logs propagate to the console handler; production is
    # quiet (gevent handles access logging with log=None).
    werkzeug_logger.propagate = debug


def clear_console():
    try:
        if os.name == "nt":
            os.system("")  # Windows терминалын ANSI горимыг нээнэ
        print("\033[2J\033[H", end="")
    except Exception:
        os.system("cls" if os.name == "nt" else "clear")


def print_startup_banner(
    app_name: str, port: int, debug: bool, host: str = "0.0.0.0"
) -> None:
    py = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    rule = "=" * 60

    clear_console()

    print(
        "\n".join(
            [
                "",
                rule,
                f"   {app_name} - application server",
                "-" * 60,
                f"   Mode      {'DEBUG (auto-reload)' if debug else 'PRODUCTION'}",
                f"   Server    {'Flask / Werkzeug dev server' if debug else 'gevent WSGIServer'}",
                f"   URL       http://{host}:{port}   (local http://127.0.0.1:{port})",
                f"   Python    {py}",
                f"   PID       {os.getpid()}",
                rule,
                "",
            ]
        )
    )


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
