"""Capture stage of the AI worker: record a short RTSP clip and extract frames.

Run by services/ai_worker.py as a separate interpreter (OpenCV's blocking RTSP
calls must not stall the gevent web server), one JSON job in, one JSON line out:

    python313\\python.exe ai\\grab.py job.json
    type job.json | python313\\python.exe ai\\grab.py

Job:
    stream_url  : RTSP URL (credentials embedded, Camera.build_links()["StreamURL"])
    clip_path   : where to write the recording (mp4), e.g. RTU Data/<SiteCode>/<CameraID>/raw_temp/raw.mp4
    seconds     : clip length in seconds (AI_CLIP_SECONDS, default 2)
    frames      : number of pictures to extract, evenly spread over the clip (SNAPSHOT_TEMP_COUNT, default 10)
    frames_dir  : folder of the extracted pictures (images_temp/), written as 1.jpg .. <frames>.jpg
    gif_path    : optional - animate the extracted pictures into this GIF (public image.gif)
    timeout     : seconds to wait for the stream (default 15)

Result (stdout, last line):
    {"ok": true, "clip": path, "fps": 25.0, "frame_count": 50, "width": 1920, "height": 1080,
     "captured_at": "2026-09-05T03:20:00", "elapsed_ms": 4800, "frames": [paths...],
     "frame_indices": [0, 5, ...], "frame_times": [0.0, 0.2, ...], "gif": path | null}
    or {"ok": false, "error": "..."} with exit code 1.

A sidecar <clip>.json with the same result is written next to the clip so a
later stage (optical flow, detection) knows the real frame spacing.
"""

import json
import os
import re
import sys
import time
from datetime import datetime

AI_DIR = os.path.dirname(os.path.abspath(__file__))
if AI_DIR not in sys.path:
    sys.path.insert(0, AI_DIR)

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from animation import build_animation  # noqa: E402
from capture import DEFAULT_TIMEOUT, set_ffmpeg_options  # noqa: E402

DEFAULT_SECONDS = 2
DEFAULT_FRAMES = 10
FALLBACK_FPS = 25.0  # when the stream does not report a frame rate
CLIP_EXT = ".mp4"
FRAME_EXT = ".jpg"


def _read_job(argv):
    if len(argv) > 1 and argv[1] != "-":
        with open(argv[1], encoding="utf-8") as fp:
            return json.load(fp)
    raw = sys.stdin.read()
    return json.loads(raw) if raw.strip() else {}


def pick_indices(total, count):
    """`count` frame indices spread evenly over `total` frames (first and last included)."""
    if total <= 0 or count <= 0:
        return []
    if count >= total:
        return list(range(total))
    return sorted({int(round(v)) for v in np.linspace(0, total - 1, count)})


def record_clip(url, clip_path, seconds, timeout):
    """Read the stream for `seconds` and write it to `clip_path` (mp4).

    Returns (frames, fps, size): the frames read (BGR arrays, in order), the
    frame rate reported by the stream (or FALLBACK_FPS) and (width, height).
    Raises RuntimeError when the stream cannot be opened or yields nothing.
    """
    set_ffmpeg_options()
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        raise RuntimeError("could not open the RTSP stream")
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        if not (1.0 <= fps <= 120.0):
            fps = FALLBACK_FPS
        wanted = max(1, int(round(fps * seconds)))
        frames = []
        deadline = time.monotonic() + timeout
        while len(frames) < wanted and time.monotonic() < deadline:
            ok, frame = cap.read()
            if ok and frame is not None:
                frames.append(frame)
            elif frames:
                break
    finally:
        cap.release()
    if not frames:
        raise RuntimeError("the RTSP stream delivered no frame")

    height, width = frames[0].shape[:2]
    os.makedirs(os.path.dirname(os.path.abspath(clip_path)), exist_ok=True)
    tmp = os.path.splitext(clip_path)[0] + ".part" + CLIP_EXT
    writer = cv2.VideoWriter(tmp, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError("could not create the clip file")
    try:
        for frame in frames:
            writer.write(frame)
    finally:
        writer.release()
    os.replace(tmp, clip_path)  # readers never see a half-written clip
    return frames, fps, (width, height)


def extract_frames(frames, indices, folder):
    """Write the selected frames as 1.jpg .. <n>.jpg (oldest first) and drop
    stale numbered pictures left by an earlier run with a higher count."""
    os.makedirs(folder, exist_ok=True)
    paths = []
    for slot, index in enumerate(indices, start=1):
        path = os.path.join(folder, f"{slot}{FRAME_EXT}")
        tmp = os.path.join(
            folder, f"{slot}.part{FRAME_EXT}"
        )  # imwrite picks the codec by extension
        if not cv2.imwrite(tmp, frames[index]):
            raise RuntimeError(f"could not write {path}")
        os.replace(tmp, path)
        paths.append(path)
    keep = {os.path.basename(p) for p in paths}
    for name in os.listdir(folder):
        if re.fullmatch(r"\d+" + re.escape(FRAME_EXT), name) and name not in keep:
            try:
                os.remove(os.path.join(folder, name))
            except OSError:
                pass
    return paths


def run(job):
    started = time.perf_counter()
    url = job.get("stream_url")
    clip_path = job.get("clip_path")
    frames_dir = job.get("frames_dir")
    if not (url and clip_path and frames_dir):
        raise ValueError("stream_url, clip_path and frames_dir are required")
    seconds = float(job.get("seconds") or DEFAULT_SECONDS)
    count = int(job.get("frames") or DEFAULT_FRAMES)
    timeout = float(job.get("timeout") or DEFAULT_TIMEOUT)

    captured_at = datetime.now()
    frames, fps, (width, height) = record_clip(url, clip_path, seconds, timeout)
    indices = pick_indices(len(frames), count)
    paths = extract_frames(frames, indices, frames_dir)
    gif = job.get("gif_path")
    if gif and not build_animation(paths, gif):
        gif = None

    result = {
        "ok": True,
        "clip": clip_path,
        "fps": round(float(fps), 3),
        "frame_count": len(frames),
        "width": width,
        "height": height,
        "captured_at": captured_at.strftime("%Y-%m-%dT%H:%M:%S"),
        "frames": paths,
        "frame_indices": indices,
        "frame_times": [
            round(i / fps, 3) for i in indices
        ],  # seconds from the clip start
        "gif": gif,
        "elapsed_ms": int((time.perf_counter() - started) * 1000),
    }
    with open(os.path.splitext(clip_path)[0] + ".json", "w", encoding="utf-8") as fp:
        json.dump(result, fp, ensure_ascii=False, indent=2)
    return result


def main(argv=None):
    argv = sys.argv if argv is None else argv
    try:
        result = run(_read_job(argv))
    except Exception as e:  # any failure becomes a JSON error for the caller
        print(
            json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"}), flush=True
        )
        return 1
    print(json.dumps(result), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
