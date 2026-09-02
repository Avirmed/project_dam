"""Camera image uploader (design slide 6).

Images that another process saves under Camera.imageOutPath/<CameraID>/
are sent to the customer's server through the camera's "Upload JPG" (FTP)
settings; delivered files move to a `sent` sub-folder, failures stay for the
next run. The outcome is stored on the camera (LastUploadRun / LastUploadResult).
"""

import logging
import os
import re
import shutil
import time
from datetime import datetime

from database import db
from models import Camera
from services import file_transfer

logger = logging.getLogger("worker")

MIN_AGE_SECONDS = 2
IMAGE_EXT = (".jpg", ".jpeg", ".png")


def out_root():
    path = Camera.imageOutPath
    os.makedirs(path, exist_ok=True)
    return path


def camera_folder(camera):
    safe_id = re.sub(r"[\\/:*?\"<>|]", "_", str(camera.CameraID or camera.ID))
    path = os.path.join(out_root(), safe_id)
    os.makedirs(path, exist_ok=True)
    return path


def pending_files(folder):
    now = time.time()
    files = []
    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        if (
            os.path.isfile(path)
            and name.lower().endswith(IMAGE_EXT)
            and now - os.path.getmtime(path) >= MIN_AGE_SECONDS
        ):
            files.append(path)
    return files


def upload_camera_images(camera):
    """Upload every pending image of one camera. Returns (sent, failed, last_message)."""
    block = (camera.Meta or {}).get("UploadConfigures") or {}
    if not isinstance(block, dict) or not block.get("status"):
        return 0, 0, None
    cfg = block.get("configs") if isinstance(block.get("configs"), dict) else {}

    folder = camera_folder(camera)
    files = pending_files(folder)
    if not files:
        return 0, 0, None

    sent_dir = os.path.join(folder, "sent")
    os.makedirs(sent_dir, exist_ok=True)

    sent = failed = 0
    message = None
    for path in files:
        name = os.path.basename(path)
        ok, message = file_transfer.upload_with_config(
            cfg.get("ServerIPAddress"), cfg, path, name
        )
        if ok:
            shutil.move(path, os.path.join(sent_dir, name))
            sent += 1
        else:
            failed += 1
            break  # same server: stop early, retry next run
    return sent, failed, message


def run():
    """Worker job: process pending images for every enabled camera."""
    for camera in Camera.query.filter(Camera.Status == 1).all():
        try:
            sent, failed, message = upload_camera_images(camera)
        except Exception as e:
            sent, failed, message = 0, 1, f"{type(e).__name__}: {e}"
            logger.exception("Image upload failed for camera %s", camera.ID)

        if sent == 0 and failed == 0:
            continue

        camera.LastUploadRun = datetime.now()
        camera.LastUploadResult = (
            f"OK: {sent} file(s) -> {message}"
            if failed == 0
            else f"ERROR: {failed} failed, {sent} sent; {message}"
        )[:500]
        db.session.commit()
        (logger.info if failed == 0 else logger.warning)(
            "Camera %s upload: %s", camera.CameraID, camera.LastUploadResult
        )
