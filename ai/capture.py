"""Frame acquisition for the detector: RTSP stream, ISAPI snapshot or a file.

OpenCV only (plus requests for ISAPI), so this module can be used from either
process. The legacy getImage.py read 10 consecutive RTSP frames per station;
`grab_burst()` keeps that behaviour for the future velocity job.
"""

import ctypes
import os
import time

import cv2
import numpy as np
import requests
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

# TCP transport: with the default UDP the cameras behind NAT never deliver RTP
# packets (only the SDP arrives, OpenCV then times out after 30 s). Socket
# timeouts are in microseconds (FFmpeg options).
RTSP_OPTIONS = "rtsp_transport;tcp|stimeout;5000000|max_delay;500000"
DEFAULT_TIMEOUT = 10  # seconds


def set_ffmpeg_options(options=RTSP_OPTIONS):
    """Hand the capture options to OpenCV's FFmpeg plugin.

    The plugin DLL shipped with opencv-python on Windows is a MinGW build that
    reads its environment through msvcrt.dll, whose table is separate from the
    UCRT one that os.environ / SetEnvironmentVariableW update - so the value has
    to be written with msvcrt's own _putenv as well, before the plugin loads
    (first VideoCapture). Verified: without this every RTSP open times out.
    """
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = options
    if os.name == "nt":
        try:
            ctypes.cdll.msvcrt._putenv(
                f"OPENCV_FFMPEG_CAPTURE_OPTIONS={options}".encode()
            )
        except (OSError, AttributeError):
            pass


set_ffmpeg_options()


def read_image(path):
    """Load an image file as a BGR array (None when unreadable)."""
    return cv2.imread(str(path)) if path and os.path.isfile(path) else None


def _open_stream(url):
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    return cap if cap.isOpened() else None


def grab_burst(url, count=1, timeout=DEFAULT_TIMEOUT):
    """Read up to `count` consecutive frames from an RTSP/HTTP stream.

    Returns a list of BGR arrays (possibly shorter than `count`, empty when the
    stream could not be opened or produced no frame before `timeout`).
    """
    cap = _open_stream(url)
    if cap is None:
        return []
    frames = []
    deadline = time.monotonic() + timeout
    try:
        while len(frames) < count and time.monotonic() < deadline:
            ok, frame = cap.read()
            if ok and frame is not None:
                frames.append(frame)
            elif frames:  # stream ended after some frames
                break
    finally:
        cap.release()
    return frames


def grab_frame(url, timeout=DEFAULT_TIMEOUT):
    """One frame from an RTSP/HTTP stream, or None."""
    frames = grab_burst(url, count=1, timeout=timeout)
    return frames[0] if frames else None


def fetch_snapshot(url, username=None, password=None, timeout=DEFAULT_TIMEOUT):
    """Download one JPEG from an ISAPI picture URL (Basic, then Digest auth).

    Returns a BGR array or None. Credentials may also be embedded in the URL,
    in which case requests handles them as Basic auth.
    """
    auths = [None]
    if username:
        auths = [
            HTTPBasicAuth(username, password or ""),
            HTTPDigestAuth(username, password or ""),
        ]
    for auth in auths:
        try:
            response = requests.get(url, auth=auth, timeout=timeout)
        except requests.RequestException:
            return None
        if response.status_code == 401:
            continue
        if not response.ok or not response.content:
            return None
        data = np.frombuffer(response.content, np.uint8)
        return cv2.imdecode(data, cv2.IMREAD_COLOR)
    return None
