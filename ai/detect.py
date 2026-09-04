"""Command-line entry point: one camera analysis job, JSON in / JSON out.

Stage 2 of the AI worker (services/ai_worker.py), the successor of the legacy
xserver_new.py `get_waterlevel_newdata()` + `detect_movement()`. Run with the
bundled interpreter from the project root, never inside the web process (see
ai/__init__.py):

    python313\\python.exe ai\\detect.py job.json
    type job.json | python313\\python.exe ai\\detect.py

Job (all keys optional except `weights` and one picture source):
    weights      : path or file name under ai/trained_models/
    imgsz        : inference size, 640 (default) or 1024
    device       : "" (auto: CUDA when available, else CPU), "cpu", "0"
    backend      : "torch" (default, AI_BACKEND) or "onnx" (OpenCV DNN on <model>.onnx, no torch)
    frames       : clip frames, oldest first (images_temp/1..N.jpg); frames[0] is analysed
    frame_times  : seconds of each frame from the clip start (raw.json)
    image_path   : single picture instead of `frames`
    stream_url / snapshot_url (+ username, password): live sources for ad-hoc runs
    crop         : [x1, y1, x2, y2] region given to the water-level model (frame pixels)
    level_from   : "frame" (default) or "crop" - which pixel row the calibration refers to
    sampling     : calibration rows [{"x": pixel_y, "y": level_m}, ...] (one table), or
    samplings    : {"<SamplingID>": rows, ...} - every table is evaluated, the level is the
                   minimum (legacy multi-gauge rule), all values are returned in `levels`
    velocity     : {"region": [x1, y1, x2, y2], "length": metres} - optical flow on `frames`
    conf, iou    : detection thresholds (0.25 / 0.45)
    gif_path     : write the annotated frames (green box, red waterline, level) as a GIF
    still_path   : write the annotated first frame (JPEG)
    label        : text drawn on the pictures (default "<level> m")

Result (stdout, last line): {"ok": true, "detected", "y", "y_crop", "bbox", "conf",
"detections", "level", "in_range", "levels", "velocity": {...} | null, "gif", "still",
"device", "elapsed_ms", ...} or {"ok": false, "error": "..."} with exit code 1.
Diagnostics go to stderr.
"""

import json
import os
import sys
import time

AI_DIR = os.path.dirname(os.path.abspath(__file__))
if AI_DIR not in sys.path:
    sys.path.insert(0, AI_DIR)

from calibration import pixel_to_level  # noqa: E402
from capture import fetch_snapshot, grab_frame, read_image  # noqa: E402


def _read_job(argv):
    if len(argv) > 1 and argv[1] != "-":
        with open(argv[1], encoding="utf-8") as fp:
            return json.load(fp)
    raw = sys.stdin.read()
    return json.loads(raw) if raw.strip() else {}


def _load_frames(job):
    """(frames, frame_times, source): BGR arrays oldest first."""
    paths = job.get("frames") or []
    if paths:
        frames = [read_image(p) for p in paths]
        frames = [f for f in frames if f is not None]
        if not frames:
            raise RuntimeError("none of the clip frames could be read")
        times = job.get("frame_times") or []
        if len(times) != len(frames):
            times = list(range(len(frames)))  # unknown spacing: 1 s per frame
        return frames, [float(t) for t in times], "frames"
    if job.get("image_path"):
        frame = read_image(job["image_path"])
        source = "file"
    elif job.get("snapshot_url"):
        frame = fetch_snapshot(
            job["snapshot_url"], job.get("username"), job.get("password")
        )
        source = "snapshot"
    elif job.get("stream_url"):
        frame = grab_frame(job["stream_url"])
        source = "stream"
    else:
        raise ValueError("frames, image_path, stream_url or snapshot_url is required")
    if frame is None:
        raise RuntimeError(f"could not read a frame from the {source}")
    return [frame], [0.0], source


def _levels(job, pixel):
    """{sampling id: level} for every calibration table in the job."""
    tables = dict(job.get("samplings") or {})
    if job.get("sampling"):
        tables.setdefault("default", job["sampling"])
    out = {}
    for name, rows in tables.items():
        level, in_range = pixel_to_level(rows, pixel)
        if level is not None:
            out[name] = {"level": round(level, 3), "in_range": in_range}
    return out


def run(job):
    started = time.perf_counter()
    if not job.get("weights"):
        raise ValueError("weights is required")

    frames, frame_times, source = _load_frames(job)

    import cv2
    import detector
    from animation import build_animation_from_arrays

    model_tuple = detector.load_model(job["weights"], job.get("device") or "", job.get("backend"))
    result = detector.detect_waterline(
        model_tuple,
        frames[0],
        imgsz=job.get("imgsz") or detector.DEFAULT_IMGSZ,
        crop=job.get("crop"),
        conf_thres=float(job.get("conf") or detector.DEFAULT_CONF),
        iou_thres=float(job.get("iou") or detector.DEFAULT_IOU),
    )

    out = {
        "ok": True,
        "source": source,
        "frame": [int(frames[0].shape[1]), int(frames[0].shape[0])],
        "frame_count": len(frames),
        "device": str(model_tuple[3]),
        "backend": model_tuple[4],
        "detected": result is not None,
        "level": None,
        "in_range": False,
        "levels": {},
        "sampling": None,
        "velocity": None,
        "gif": None,
        "still": None,
    }
    if result:
        out.update(result)
        pixel = result["y_crop"] if job.get("level_from") == "crop" else result["y"]
        levels = _levels(job, pixel)
        out["levels"] = levels
        if levels:
            # legacy multi-gauge rule: the lowest reading wins
            name = min(levels, key=lambda k: levels[k]["level"])
            out["sampling"] = name
            out["level"] = levels[name]["level"]
            out["in_range"] = levels[name]["in_range"]

    vel_cfg = job.get("velocity") or {}
    if vel_cfg.get("region") and len(frames) >= 2:
        import velocity

        out["velocity"] = velocity.analyse(
            frames, frame_times, vel_cfg.get("region"), vel_cfg.get("length")
        )

    label = job.get("label")
    if label is None and out["level"] is not None:
        label = f"{out['level']:.2f} m"
    if job.get("gif_path") or job.get("still_path"):
        annotated = [detector.annotate(frame, result, label) for frame in frames]
        if job.get("gif_path") and build_animation_from_arrays(
            annotated, job["gif_path"]
        ):
            out["gif"] = job["gif_path"]
        if job.get("still_path"):
            os.makedirs(
                os.path.dirname(os.path.abspath(job["still_path"])), exist_ok=True
            )
            tmp = os.path.splitext(job["still_path"])[0] + ".part.jpg"
            if cv2.imwrite(tmp, annotated[0]):
                os.replace(tmp, job["still_path"])
                out["still"] = job["still_path"]

    out["elapsed_ms"] = int((time.perf_counter() - started) * 1000)
    return out


def main(argv=None):
    argv = sys.argv if argv is None else argv
    try:
        job = _read_job(argv)
        result = run(job)
    except Exception as e:  # any failure becomes a JSON error for the caller
        print(
            json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"}), flush=True
        )
        return 1
    print(json.dumps(result), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
