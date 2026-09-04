"""In-process background worker.

Started from app.py right after the startup checks: a single daemon thread
that wakes every TICK_SECONDS, and runs each registered job whose interval has
elapsed inside its own app context / DB session. Every job runs in try/except
so a failure can never affect the web server; the whole worker can be switched
off with the WORKER_ENABLED setting (dashboard -> Settings).

Per-job statistics (last run, duration, result, errors, next run) are kept in
STATS and exposed by status() for the dashboard overview.

Under the production gevent server threading is monkey-patched, so this thread
is a cooperative greenlet; blocking I/O (urllib, ftplib) yields to web requests.
"""

import logging
import threading
import time
from datetime import datetime, timedelta

from database import db

logger = logging.getLogger("worker")

TICK_SECONDS = 5
STARTED_AT = datetime.now()  # app process start (module imported by app.py)

# (name, callable, interval_seconds) - populated by register() below.
JOBS = []
# name -> {"last_mono", "last_run", "duration", "result", "error", "runs", "errors"}
STATS = {}
_state = {"last_tick": None, "enabled": None}

_thread = None
_stop = threading.Event()


def register(name, func, interval_seconds):
    JOBS.append((name, func, max(int(interval_seconds), 1)))
    STATS.setdefault(
        name,
        {
            "last_mono": None,
            "last_run": None,
            "duration": None,
            "result": None,
            "error": None,
            "runs": 0,
            "errors": 0,
        },
    )


def _worker_enabled():
    from models import Settings

    value = str(Settings.load_settings().get("WORKER_ENABLED", "1")).strip().lower()
    return value not in ("0", "false", "off", "no")


def _describe(result):
    """Short text of a job's return value for the status panel."""
    if result is None:
        return None
    if isinstance(result, dict):
        parts = [f"{k}: {v}" for k, v in result.items() if v]
        return ", ".join(parts) if parts else None
    if isinstance(result, (int, float)) and not result:
        return None  # "nothing to do" counts are not worth showing
    return str(result)[:200]


def _run_job(name, func):
    stats = STATS[name]
    started = time.perf_counter()
    stats["last_mono"] = time.monotonic()
    stats["last_run"] = datetime.now()
    stats["runs"] += 1
    try:
        stats["result"] = _describe(func())
        stats["error"] = None
    except Exception as e:
        db.session.rollback()
        stats["errors"] += 1
        stats["error"] = f"{type(e).__name__}: {e}"[:300]
        logger.exception("Worker job '%s' failed.", name)
    finally:
        stats["duration"] = round(time.perf_counter() - started, 3)


def _loop(app):
    logger.info("Worker started (%d job(s), tick %ss).", len(JOBS), TICK_SECONDS)

    while not _stop.is_set():
        now = time.monotonic()
        with app.app_context():
            try:
                _state["last_tick"] = datetime.now()
                _state["enabled"] = _worker_enabled()
                if _state["enabled"]:
                    for name, func, interval in JOBS:
                        last = STATS[name]["last_mono"]
                        if last is not None and now - last < interval:
                            continue
                        _run_job(name, func)
            except Exception:
                logger.exception("Worker tick failed.")
            finally:
                db.session.remove()

        _stop.wait(TICK_SECONDS)

    logger.info("Worker stopped.")


def status():
    """Worker + per-job state for the dashboard (services/sysinfo is separate)."""
    now_mono = time.monotonic()
    now = datetime.now()
    jobs = []
    for name, _func, interval in JOBS:
        s = STATS.get(name, {})
        last_mono = s.get("last_mono")
        next_in = None
        if last_mono is not None:
            next_in = max(0, int(round(last_mono + interval - now_mono)))
        elif is_alive():
            next_in = 0
        jobs.append(
            {
                "name": name,
                "interval": interval,
                "last_run": s.get("last_run"),
                "duration": s.get("duration"),
                "result": s.get("result"),
                "error": s.get("error"),
                "runs": s.get("runs", 0),
                "errors": s.get("errors", 0),
                "next_in": next_in,
                "next_run": (
                    (now + timedelta(seconds=next_in)) if next_in is not None else None
                ),
            }
        )
    return {
        "alive": is_alive(),
        "enabled": _state["enabled"],
        "started_at": STARTED_AT,
        "last_tick": _state["last_tick"],
        "tick_seconds": TICK_SECONDS,
        "jobs": jobs,
    }


def is_alive():
    return _thread is not None and _thread.is_alive()


def start_worker(app):
    """Start the worker thread once (safe to call again)."""
    global _thread

    if is_alive():
        return _thread

    # Import jobs here so models are fully loaded first.
    from services import (
        http_sender,
        csv_logger,
        event_watcher,
        image_uploader,
        snapshot,
        sysinfo,
        retention,
        simulator,
    )

    if not JOBS:
        register("http_sender", http_sender.send_pending, 5)
        register("csv_logger", csv_logger.run, 30)
        register("event_watcher", event_watcher.run, 15)
        register("image_uploader", image_uploader.run, 30)
        register("snapshot", snapshot.run, 30)  # per-camera due-ness inside
        register("sysinfo", sysinfo.sample, 10)  # CPU sample + cached folder sizes
        register("retention", retention.run, 3600)
        # demo payloads (SIMULATOR_ENABLED); 15 s so a new 15-min slot is written
        # almost at once - otherwise stations look "No connection" for up to a
        # minute after every slot boundary (DATA_TIMEOUT_MINUTES = 15)
        register("simulator", simulator.run, 15)

    _stop.clear()
    _thread = threading.Thread(
        target=_loop, args=(app,), name="dam-worker", daemon=True
    )
    _thread.start()
    return _thread


def stop_worker():
    _stop.set()
