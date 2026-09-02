"""In-process background worker.

Started from app.py right after the startup checks: a single daemon thread
that wakes every TICK_SECONDS, and runs each registered job whose interval has
elapsed inside its own app context / DB session. Every job runs in try/except
so a failure can never affect the web server; the whole worker can be switched
off with the WORKER_ENABLED setting (dashboard -> Settings).

Under the production gevent server threading is monkey-patched, so this thread
is a cooperative greenlet; blocking I/O (urllib, ftplib) yields to web requests.
"""

import logging
import threading
import time

from database import db

logger = logging.getLogger("worker")

TICK_SECONDS = 5

# (name, callable, interval_seconds) - populated by register() below.
JOBS = []

_thread = None
_stop = threading.Event()


def register(name, func, interval_seconds):
    JOBS.append((name, func, max(int(interval_seconds), 1)))


def _worker_enabled():
    from models import Settings

    value = str(Settings.load_settings().get("WORKER_ENABLED", "1")).strip().lower()
    return value not in ("0", "false", "off", "no")


def _loop(app):
    last_run = {}
    logger.info("Worker started (%d job(s), tick %ss).", len(JOBS), TICK_SECONDS)

    while not _stop.is_set():
        now = time.monotonic()
        with app.app_context():
            try:
                if _worker_enabled():
                    for name, func, interval in JOBS:
                        if now - last_run.get(name, 0) < interval:
                            continue
                        last_run[name] = now
                        try:
                            func()
                        except Exception:
                            db.session.rollback()
                            logger.exception("Worker job '%s' failed.", name)
            except Exception:
                logger.exception("Worker tick failed.")
            finally:
                db.session.remove()

        _stop.wait(TICK_SECONDS)

    logger.info("Worker stopped.")


def start_worker(app):
    """Start the worker thread once (safe to call again)."""
    global _thread

    if _thread is not None and _thread.is_alive():
        return _thread

    # Import jobs here so models are fully loaded first.
    from services import http_sender, csv_logger, event_watcher, image_uploader, retention

    if not JOBS:
        register("http_sender", http_sender.send_pending, 5)
        register("csv_logger", csv_logger.run, 30)
        register("event_watcher", event_watcher.run, 15)
        register("image_uploader", image_uploader.run, 30)
        register("retention", retention.run, 3600)

    _stop.clear()
    _thread = threading.Thread(
        target=_loop, args=(app,), name="dam-worker", daemon=True
    )
    _thread.start()
    return _thread


def stop_worker():
    _stop.set()
