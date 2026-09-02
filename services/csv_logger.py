"""CSV logger job (design slide 2 / 20).

Every `LogInterval` minutes (aligned to the clock, e.g. :00 :15 :30 :45) each
enabled CSV Logger appends one row - built from its Parameter Mapping and the
station's newest StationData - to a daily CSV file named by `FilenameFormat`,
then uploads the file through the logger's File Transfer (FTP) connection.
The outcome is stored on the logger row (LastRun / LastResult).

Filename placeholders : @DEVICENAME (site code), @DATE (YYYY-MM-DD) and
                        strftime codes such as %d%m%Y.
Column placeholders   : %DEVICENAME%, %DATETIME%, %DATE%, %DATE_DMY%, %TIME%,
                        %<key>% = value from the station's mapped data (then the
                        raw payload); anything else is written literally.
"""

import csv
import logging
import os
import re
from datetime import datetime

from database import db
from models import CsvLogger, StationData
from services import file_transfer
from util import statictext, util as Util

logger = logging.getLogger("worker")

PLACEHOLDER = re.compile(r"^%([A-Za-z0-9_\-.]+)%$")
_slots = {}  # logger ID -> last interval slot that was written


def csv_root():
    return os.path.join(statictext.APP_TMP_PATH, "csv")


def device_name(station):
    return (station.SiteCode or station.DeviceID or "").strip()


def render_filename(fmt, station, moment):
    name = str(fmt or "@DEVICENAME_@DATE.csv")
    name = name.replace("@DEVICENAME", device_name(station)).replace(
        "@DATE", moment.strftime("%Y-%m-%d")
    )
    try:
        name = moment.strftime(name)
    except ValueError:
        pass
    # keep it a plain file name
    return re.sub(r"[\\/:*?\"<>|]", "_", name) or "log.csv"


def render_value(source, station, data, raw, moment):
    text = str(source or "").strip()
    match = PLACEHOLDER.match(text)
    if not match:
        return text
    key = match.group(1)
    specials = {
        "DEVICENAME": device_name(station),
        "DATETIME": moment.strftime("%Y-%m-%d %H:%M:%S"),
        "DATE": moment.strftime("%Y-%m-%d"),
        "DATE_DMY": moment.strftime("%d/%m/%y"),
        "TIME": moment.strftime("%H:%M:%S"),
    }
    if key in specials:
        return specials[key]
    value = Util.lookup_path(data or {}, key)
    if value is None:
        value = Util.lookup_path(raw or {}, key)
    return "" if value is None else value


def write_row(logger_row, station, latest, cfg, moment):
    """Append one row (header on a new file) and return the local file path."""
    mapping = [
        m
        for m in (cfg.get("Mapping") or [])
        if isinstance(m, dict) and str(m.get("header") or "").strip()
    ]
    headers = [str(m.get("header")).strip() for m in mapping]
    values = [
        render_value(m.get("source"), station, latest.Data, latest.Raw, moment)
        for m in mapping
    ]

    folder = os.path.join(csv_root(), str(logger_row.ID))
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(
        folder, render_filename(logger_row.FilenameFormat, station, moment)
    )
    is_new = not os.path.exists(path)

    with open(path, "a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if is_new:
            if (
                Util.safe_int(cfg.get("DeviceNameFirstLine"), 0)
                or cfg.get("DeviceNameFirstLine") is True
            ):
                writer.writerow([device_name(station)])
            writer.writerow(headers)
        writer.writerow(values)

    return path


def run_logger(logger_row, moment):
    transfer = logger_row.filetransfer
    station = transfer.station if transfer else None
    if station is None:
        return False, "No station on the File Transfer"

    block = (logger_row.Meta or {}).get("Logger") or {}
    if not isinstance(block, dict) or not block.get("status"):
        return False, "Logger switched off"
    cfg = block.get("configs") or {}

    latest = StationData.latest_by_station([station.StationID]).get(station.StationID)
    if latest is None:
        return False, "No station data yet"

    path = write_row(logger_row, station, latest, cfg, moment)
    ok, message = file_transfer.upload(transfer, path, os.path.basename(path))
    return ok, (
        f"{os.path.basename(path)} -> {message}"
        if ok
        else f"{os.path.basename(path)} written; {message}"
    )


def run():
    """Worker job: run every logger whose interval slot has not been written."""
    now = datetime.now()
    for logger_row in CsvLogger.query.filter(CsvLogger.Status == 1).all():
        block = (logger_row.Meta or {}).get("Logger") or {}
        cfg = block.get("configs") if isinstance(block, dict) else {}
        interval = Util.safe_int((cfg or {}).get("LogInterval"), 15) or 15
        slot = int(now.timestamp() // (interval * 60))

        if _slots.get(logger_row.ID) == slot:
            continue
        if (
            logger_row.LastRun
            and int(logger_row.LastRun.timestamp() // (interval * 60)) == slot
        ):
            _slots[logger_row.ID] = slot
            continue
        _slots[logger_row.ID] = slot

        try:
            ok, message = run_logger(logger_row, now)
        except Exception as e:
            ok, message = False, f"{type(e).__name__}: {e}"
            logger.exception("CSV logger %s failed.", logger_row.ID)

        logger_row.LastRun = now
        logger_row.LastResult = (("OK: " if ok else "ERROR: ") + str(message))[:500]
        db.session.commit()
        (logger.info if ok else logger.warning)(
            "CSV logger %s: %s", logger_row.ID, logger_row.LastResult
        )
