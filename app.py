import os
import sys

from dotenv import load_dotenv

load_dotenv()

APP_DEBUG = os.getenv("APP_DEBUG", "False").lower() in ("true", "1", "t", "yes")
APP_PORT = int(os.getenv("APP_PORT", 88))

if not APP_DEBUG:
    from gevent import monkey

    monkey.patch_all()

from gevent.pywsgi import WSGIServer
from werkzeug.middleware.proxy_fix import ProxyFix
from flask import Flask
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager

sys.path.append(os.path.dirname(__file__))

from database import db
from fixtures.loader import load_fixtures, register_cli
from urls import register_blueprints
from util import statictext
from util.handlers import register_handlers
from extensions import (
    init_login_manager,
    CustomJSONProvider,
    setup_logging,
    print_startup_banner,
)
import logging

os.environ["APP_KEY"] = statictext.APP_KEY
os.environ["APP_IV"] = statictext.APP_IV


setup_logging(APP_DEBUG)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(__name__)

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    app.config.from_object("config.Config")
    app.url_map.strict_slashes = False
    app.secret_key = os.getenv("APP_SECRET_KEY")

    app.json_provider_class = CustomJSONProvider
    app.json = app.json_provider_class(app)

    JWTManager(app)
    db.init_app(app)
    Migrate(app, db)
    init_login_manager(app)

    register_handlers(app)
    register_blueprints(app)
    register_cli(app)

    os.makedirs(statictext.APP_TMP_PATH, exist_ok=True)

    return app


app = create_app()


def run_startup_checks(app: Flask) -> None:
    with app.app_context():
        try:
            db.engine.connect()
        except Exception:
            logger.error("Database connection failed.")
            print("Action: Start PostgreSQL server and check your settings.")
            sys.exit(1)

        load_fixtures()


if __name__ == "__main__":
    if not APP_DEBUG or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        print_startup_banner(statictext.APP_NAME, APP_PORT, APP_DEBUG)
        run_startup_checks(app)

    if APP_DEBUG:
        app.run(host="0.0.0.0", port=APP_PORT, debug=True, use_reloader=True)
    else:
        http_server = WSGIServer(
            ("0.0.0.0", APP_PORT),
            app,
            log=None,
            error_log=logger,
        )
        try:
            http_server.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped by user.")
