"""Camera snapshot job (front design rev.18 slides 4-7, CCTV "Snap").

Every SNAPSHOT_INTERVAL_MINUTES (Settings, 0 = off) the worker downloads one
picture from each enabled camera's ISAPI snapshot link (Camera.build_links)
and stores it as Camera.snapshotPath/<CameraID>/latest.jpg, served publicly
from Camera.snapshotUrl for the front CCTV page. The file's mtime is the
"taken at" time, so no database column is needed; a camera is due when its
latest.jpg is older than the interval. Failures are logged and the previous
picture is kept.
"""

import logging
import os
import re
import time
import urllib.request
from urllib.parse import urlsplit, urlunsplit

from models import Camera, Settings
from util import statictext, util as Util

logger = logging.getLogger("worker")

TIMEOUT_SECONDS = 5
FILE_NAME = "latest.jpg"
# Cameras fetched per worker tick: an unreachable camera costs TIMEOUT_SECONDS,
# and jobs run one after another in the worker thread, so keep a tick short.
MAX_PER_TICK = 2
# camera ID -> monotonic time of the last attempt (success or failure), so an
# unreachable camera is retried once per interval instead of on every tick.
_last_attempt = {}


def camera_folder(camera):
    safe_id = re.sub(r"[\\/:*?\"<>|]", "_", str(camera.CameraID or camera.ID))
    return os.path.join(Camera.snapshotPath, safe_id)


def snapshot_file(camera):
    return os.path.join(camera_folder(camera), FILE_NAME)


def interval_minutes():
    return Util.safe_int(
        Settings.load_settings().get("SNAPSHOT_INTERVAL_MINUTES"),
        statictext.SNAPSHOT_INTERVAL_MINUTES,
    )


def is_due(camera, minutes):
    """Due when the last attempt (this process) and the stored picture are both
    older than the interval."""
    last = _last_attempt.get(camera.ID)
    if last is not None and time.monotonic() - last < minutes * 60:
        return False
    try:
        age = time.time() - os.path.getmtime(snapshot_file(camera))
    except OSError:
        return True  # never taken
    return age >= minutes * 60


def _opener(url):
    """URL without credentials + opener handling Basic and Digest auth
    (Hikvision ISAPI answers with Digest by default)."""
    parts = urlsplit(url)
    host = parts.hostname or ""
    netloc = f"{host}:{parts.port}" if parts.port else host
    clean = urlunsplit((parts.scheme, netloc, parts.path, parts.query, ""))
    handlers = []
    if parts.username:
        manager = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        manager.add_password(None, clean, parts.username, parts.password or "")
        handlers += [
            urllib.request.HTTPBasicAuthHandler(manager),
            urllib.request.HTTPDigestAuthHandler(manager),
        ]
    return clean, urllib.request.build_opener(*handlers)


def fetch(url):
    """Download one picture; returns the image bytes or raises."""
    clean, opener = _opener(url)
    with opener.open(clean, timeout=TIMEOUT_SECONDS) as response:
        content_type = response.headers.get("Content-Type", "")
        data = response.read()
    if not data or not content_type.lower().startswith("image/"):
        raise ValueError(
            f"not an image ({content_type or 'no content type'}, {len(data)} bytes)"
        )
    return data


def take_snapshot(camera):
    """Fetch and store the camera's picture; returns the file path."""
    url = camera.build_links().get("SnapshotURL")
    if not url:
        return None
    data = fetch(url)
    folder = camera_folder(camera)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, FILE_NAME)
    tmp = path + ".part"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)  # atomic: readers never see a half-written file
    return path


def run():
    """Worker job: refresh every due camera picture."""
    minutes = interval_minutes()
    if minutes <= 0:
        return None
    done = 0
    for camera in Camera.query.filter(Camera.Status == 1).order_by(Camera.ID).all():
        if done >= MAX_PER_TICK:
            break
        if not is_due(camera, minutes):
            continue
        _last_attempt[camera.ID] = time.monotonic()
        done += 1
        try:
            path = take_snapshot(camera)
            if path:
                logger.info("Snapshot %s -> %s", camera.CameraID, path)
        except Exception as e:
            logger.warning("Snapshot failed for camera %s: %s", camera.CameraID, e)
