"""Camera snapshot job (front design rev.18 slides 4-7, CCTV "Snap").

Every SNAPSHOT_INTERVAL_MINUTES (Settings, 0 = off) the worker downloads one
picture from each enabled camera's ISAPI snapshot link (Camera.build_links)
and files it under the station's private RTU Data folder, the way the legacy
server did:

    RTU Data/<SiteCode>/<CameraID>/images/   <CameraID>_<yyyymmddHHMMSSffffff>.jpg,
                                             newest SNAPSHOT_KEEP_COUNT kept

RTU Data is never web-served; the newest picture is also copied to the public
Camera.snapshotPath/<CameraID>/image.jpg (static/data/cameras/) for the front
CCTV page and the camera form. The animation image.gif next to it is produced
by the AI worker from its RTSP clip (images_temp/1..N.jpg, ai/animation.py),
not by this job; the page
shows the gif when present, else image.jpg, else the blank picture. A camera
is due when its newest picture is older than the interval. Failures are logged
and the previous pictures are kept.
"""

import logging
import os
import time
import urllib.request
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit

from models import Camera, Settings
from util import statictext, util as Util

logger = logging.getLogger("worker")

TIMEOUT_SECONDS = 5
FILE_EXT = ".jpg"
TIME_FORMAT = "%Y%m%d%H%M%S%f"  # 20260905002148123456
GIF_NAME = "image.gif"
STILL_NAME = "image.jpg"
# Cameras fetched per worker tick: an unreachable camera costs TIMEOUT_SECONDS,
# and jobs run one after another in the worker thread, so keep a tick short.
MAX_PER_TICK = 2
# camera ID -> monotonic time of the last attempt (success or failure), so an
# unreachable camera is retried once per interval instead of on every tick.
_last_attempt = {}


def _is_snapshot(name):
    return name.lower().endswith(FILE_EXT) and not name.endswith(".part")


def _list_pictures(folder):
    """Pictures in a folder, oldest first (the names sort by time)."""
    try:
        names = [n for n in os.listdir(folder) if _is_snapshot(n)]
    except OSError:
        return []
    return [os.path.join(folder, n) for n in sorted(names)]


def snapshot_files(camera):
    """All archived pictures of a camera (images/), oldest first."""
    return _list_pictures(camera.images_folder())


def snapshot_file(camera):
    """Path of the newest archived picture, or None when none exists."""
    files = snapshot_files(camera)
    return files[-1] if files else None


def snapshot_time(path):
    """Taken-at time parsed from the file name; falls back to the mtime."""
    stem = os.path.splitext(os.path.basename(path))[0]
    stamp = stem.rsplit("_", 1)[-1]
    try:
        return datetime.strptime(stamp, TIME_FORMAT)
    except ValueError:
        return datetime.fromtimestamp(os.path.getmtime(path))


def _setting(name, default):
    return Util.safe_int(Settings.load_settings().get(name), default)


def interval_minutes():
    return _setting("SNAPSHOT_INTERVAL_MINUTES", statictext.SNAPSHOT_INTERVAL_MINUTES)


def keep_count():
    return _setting("SNAPSHOT_KEEP_COUNT", statictext.SNAPSHOT_KEEP_COUNT)


def is_due(camera, minutes):
    """Due when the last attempt (this process) and the newest archived
    picture are both older than the interval."""
    last = _last_attempt.get(camera.ID)
    if last is not None and time.monotonic() - last < minutes * 60:
        return False
    newest = snapshot_file(camera)
    if newest is None:
        return True  # never taken
    try:
        age = time.time() - os.path.getmtime(newest)
    except OSError:
        return True
    return age >= minutes * 60


def _prune(folder, keep):
    """Delete the oldest pictures of a folder so at most `keep` remain
    (0 = unlimited). Returns the number of files removed."""
    if keep <= 0:
        return 0
    files = _list_pictures(folder)
    removed = 0
    for path in files[: max(0, len(files) - keep)]:
        try:
            os.remove(path)
            removed += 1
        except OSError as e:
            logger.warning("Snapshot prune failed for %s: %s", path, e)
    return removed


def prune(camera, keep=None):
    """Trim the camera's archive (images/) to SNAPSHOT_KEEP_COUNT files."""
    return _prune(camera.images_folder(), keep_count() if keep is None else keep)


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


def _atomic_write(path, data):
    tmp = path + ".part"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)  # readers never see a half-written file


def rebuild_public(camera):
    """Copy the newest archived picture to the public image.jpg. Safe to call
    at any time; returns the public path or None when the archive is empty."""
    archive = snapshot_files(camera)
    if not archive:
        return None
    public = camera.public_folder()
    os.makedirs(public, exist_ok=True)
    path = os.path.join(public, STILL_NAME)
    with open(archive[-1], "rb") as f:
        _atomic_write(path, f.read())
    return path


def take_snapshot(camera, keep=None):
    """Fetch the camera's picture into images/ as a new timestamped file, trim
    the archive and refresh the public image.jpg. Returns the archived path."""
    url = camera.build_links().get("SnapshotURL")
    if not url:
        return None
    data = fetch(url)
    folder = camera.images_folder()
    os.makedirs(folder, exist_ok=True)
    stamp = datetime.now().strftime(TIME_FORMAT)
    path = os.path.join(folder, f"{camera.safe_id()}_{stamp}{FILE_EXT}")
    _atomic_write(path, data)
    prune(camera, keep)
    rebuild_public(camera)
    return path


def run():
    """Worker job: refresh every due camera picture."""
    minutes = interval_minutes()
    if minutes <= 0:
        return None
    keep = keep_count()
    done = 0
    for camera in Camera.query.filter(Camera.Status == 1).order_by(Camera.ID).all():
        if done >= MAX_PER_TICK:
            break
        if not is_due(camera, minutes):
            continue
        _last_attempt[camera.ID] = time.monotonic()
        done += 1
        try:
            path = take_snapshot(camera, keep)
            if path:
                logger.info("Snapshot %s -> %s", camera.CameraID, path)
        except Exception as e:
            logger.warning("Snapshot failed for camera %s: %s", camera.CameraID, e)
