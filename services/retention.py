"""Data retention job - keeps the fact tables from growing without bound.

Runs once per day (first worker tick of the day). Limits come from Settings
(0 = keep forever):
  DATA_RETENTION_DAYS     - delete tbl_station_data rows older than N days
  RAW_RETENTION_DAYS      - drop the raw device payload (StationData.Raw) of rows
                            older than N days while keeping the mapped Data
  HTTPLOG_RETENTION_DAYS  - delete delivered / failed HttpLog rows older than N days
  EVENTLOG_RETENTION_DAYS - delete EventLog rows (and their image files) older than N days
Deletes run in batches so the tables are never locked for long.
"""

import logging
import os
from datetime import date, datetime, timedelta

from database import db
from models import EventLog, HttpLog, Settings, StationData
from util import statictext, util as Util

logger = logging.getLogger("worker")

BATCH = 5000
_last_run_day = None


def _days(settings, name, default):
    return Util.safe_int(settings.get(name), default)


def _cutoff(days):
    return datetime.now() - timedelta(days=days)


def _delete_batches(model, condition):
    """DELETE ... WHERE condition, BATCH rows at a time; returns rows removed."""
    removed = 0
    last_ids = None
    while True:
        ids = [row[0] for row in db.session.query(model.ID).filter(condition).limit(BATCH).all()]
        if not ids or ids == last_ids:  # nothing left, or no progress -> stop
            return removed
        last_ids = ids
        db.session.query(model).filter(model.ID.in_(ids)).delete(synchronize_session=False)
        db.session.commit()
        removed += len(ids)


def purge_station_data(days):
    if days <= 0:
        return 0
    return _delete_batches(StationData, StationData.RecordTime < _cutoff(days))


def purge_raw_payloads(days):
    if days <= 0:
        return 0
    cleared = 0
    cutoff = _cutoff(days)
    last_ids = None
    while True:
        ids = [
            row[0]
            for row in db.session.query(StationData.ID)
            .filter(StationData.RecordTime < cutoff, StationData.Raw.isnot(None))
            .limit(BATCH)
            .all()
        ]
        if not ids or ids == last_ids:  # nothing left, or no progress -> stop
            return cleared
        last_ids = ids
        # db.null() writes SQL NULL; a Python None would be stored as JSON 'null'
        # on a JSONB column and still match IS NOT NULL.
        db.session.query(StationData).filter(StationData.ID.in_(ids)).update({StationData.Raw: db.null()}, synchronize_session=False)
        db.session.commit()
        cleared += len(ids)


def purge_http_logs(days):
    if days <= 0:
        return 0
    return _delete_batches(HttpLog, (HttpLog.Status != HttpLog.STATUS_QUEUE) & (HttpLog.CreateDate < _cutoff(days)))


def purge_event_logs(days):
    if days <= 0:
        return 0
    removed = 0
    cutoff = _cutoff(days)
    while True:
        rows = EventLog.query.filter(EventLog.EventTime < cutoff).limit(BATCH).all()
        if not rows:
            return removed
        for row in rows:
            if row.ImageSource:
                path = os.path.join(EventLog.drfFilePath, *row.ImageSource.split("/"))
                try:
                    os.remove(path)
                except OSError:
                    pass
            db.session.delete(row)
        db.session.commit()
        removed += len(rows)


def run_now():
    """Apply every retention rule once; returns {rule: rows affected}."""
    settings = Settings.load_settings()
    result = {
        "station_data": purge_station_data(_days(settings, "DATA_RETENTION_DAYS", statictext.DATA_RETENTION_DAYS)),
        "raw_payloads": purge_raw_payloads(_days(settings, "RAW_RETENTION_DAYS", statictext.RAW_RETENTION_DAYS)),
        "http_logs": purge_http_logs(_days(settings, "HTTPLOG_RETENTION_DAYS", statictext.HTTPLOG_RETENTION_DAYS)),
        "event_logs": purge_event_logs(_days(settings, "EVENTLOG_RETENTION_DAYS", statictext.EVENTLOG_RETENTION_DAYS)),
    }
    if any(result.values()):
        logger.info("Retention: %s", result)
    return result


def run():
    """Worker job: once per calendar day."""
    global _last_run_day
    today = date.today()
    if _last_run_day == today:
        return None
    _last_run_day = today
    return run_now()
