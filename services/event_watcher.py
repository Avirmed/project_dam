"""Security camera folder watcher (design slide 10).

CCTVs of Camera Type "Security" drop event snapshots into the watch folder
(tmp/<EVENT_WATCH_FOLDER>, configurable in Settings). Each file is named
<IP>_<channel>_<yyyymmddHHMMSS[mmm]>_<EVENT>.jpg, e.g.
192.168.1.65_01_20250905115636245_MOTION_DETECTION.jpg.

Every run: parse new files, match the camera by IP (RSTP_IP / Onvif_IP in the
camera's settings), move the image under static/data/events/<yyyymm>/ and
create an EventLog row for the operator to approve / reject. Files that do not
match the pattern go to <watch>/_unmatched so they never block the folder.
"""

import logging
import os
import re
import shutil
import time
import uuid
from datetime import datetime

from database import db
from models import Camera, EventLog, Settings
from util import statictext

logger = logging.getLogger("worker")

FILENAME = re.compile(
    r"^(?P<ip>\d{1,3}(?:\.\d{1,3}){3})_(?P<channel>\d+)_(?P<ts>\d{14})(?P<ms>\d*)_(?P<event>[A-Za-z0-9_\-]+)\.(?P<ext>jpe?g|png)$",
    re.IGNORECASE,
)
MIN_AGE_SECONDS = 2  # skip files that are still being written


def watch_folder():
    name = str(
        Settings.load_settings().get("EVENT_WATCH_FOLDER")
        or statictext.EVENT_WATCH_FOLDER
    ).strip()
    name = re.sub(r"[\\/:*?\"<>|.]", "_", name) or statictext.EVENT_WATCH_FOLDER
    path = os.path.join(statictext.APP_TMP_PATH, name)
    os.makedirs(path, exist_ok=True)
    return path


def event_title(raw):
    return " ".join(
        part.capitalize() for part in str(raw).replace("-", "_").split("_") if part
    )


def _camera_ip_index():
    """{ip: (camera, station_id)} for enabled cameras, Security type first."""
    index = {}
    cameras = Camera.query.filter(Camera.Status == 1).all()
    cameras.sort(
        key=lambda c: (
            0
            if ((c.Meta or {}).get("CameraConfigures") or {})
            .get("configs", {})
            .get("CameraType")
            == "Security"
            else 1
        )
    )
    for camera in cameras:
        block = (camera.Meta or {}).get("CameraConfigures") or {}
        cfg = block.get("configs") if isinstance(block, dict) else {}
        if not isinstance(cfg, dict):
            continue
        station_id = cfg.get("StationID") or None
        for key in ("RSTP_IP", "Onvif_IP"):
            ip = str(cfg.get(key) or "").strip()
            ip = (
                re.sub(r"^[a-z]+://", "", ip).split("/")[0].split("@")[-1].split(":")[0]
            )
            if ip and ip not in index:
                index[ip] = (camera, station_id)
    return index


def parse_filename(filename):
    match = FILENAME.match(filename)
    if not match:
        return None
    try:
        moment = datetime.strptime(match.group("ts"), "%Y%m%d%H%M%S")
    except ValueError:
        return None
    return {
        "ip": match.group("ip"),
        "channel": match.group("channel"),
        "time": moment,
        "event": event_title(match.group("event")),
        "ext": match.group("ext").lower(),
    }


def process_file(path, ip_index):
    filename = os.path.basename(path)
    info = parse_filename(filename)
    folder = os.path.dirname(path)

    if info is None:
        unmatched = os.path.join(folder, "_unmatched")
        os.makedirs(unmatched, exist_ok=True)
        shutil.move(path, os.path.join(unmatched, filename))
        logger.warning("Event watcher: unrecognised file moved aside: %s", filename)
        return None

    if EventLog.query.filter(EventLog.Filename == filename).first():
        os.remove(path)
        return None

    camera, station_id = ip_index.get(info["ip"], (None, None))

    subdir = info["time"].strftime("%Y%m")
    dest_dir = os.path.join(statictext.EVENT_IMAGE_PATH, subdir)
    os.makedirs(dest_dir, exist_ok=True)
    dest_name = filename
    if os.path.exists(os.path.join(dest_dir, dest_name)):
        dest_name = f"{uuid.uuid4().hex[:8]}_{filename}"
    shutil.move(path, os.path.join(dest_dir, dest_name))

    now = datetime.now()
    row = EventLog(
        CameraID=camera.ID if camera else None,
        StationID=int(station_id) if str(station_id or "").isdigit() else None,
        IP=info["ip"],
        Channel=info["channel"],
        EventTime=info["time"],
        Event=info["event"],
        Filename=filename,
        ImageSource=f"{subdir}/{dest_name}",
        Status=EventLog.STATUS_PENDING,
        CreateDate=now,
    )
    db.session.add(row)
    db.session.commit()
    logger.info(
        "Event watcher: %s -> event #%s (%s)",
        filename,
        row.ID,
        "camera matched" if camera else "no camera match",
    )
    return row


def run():
    """Worker job: ingest every settled image file in the watch folder."""
    folder = watch_folder()
    ip_index = None
    created = 0
    now = time.time()

    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        if not os.path.isfile(path) or not name.lower().endswith(
            (".jpg", ".jpeg", ".png")
        ):
            continue
        if now - os.path.getmtime(path) < MIN_AGE_SECONDS:
            continue
        if ip_index is None:
            ip_index = _camera_ip_index()
        try:
            if process_file(path, ip_index) is not None:
                created += 1
        except Exception:
            db.session.rollback()
            logger.exception("Event watcher failed on %s", name)

    return created
