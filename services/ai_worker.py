"""AI worker (camera analysis, the successor of the legacy xserver_new.py loop).

Every AI_WORKER_INTERVAL_MINUTES (Settings, 0 = off; slots aligned to the
clock like the CSV logger) each enabled camera of type "Sensor" that has an
uploaded model (Camera.model_file()) is processed in a separate interpreter
(ai/*.py, see ai/README.md) so that OpenCV / torch never run inside the web
process. Per camera, in order:

  1. capture   - ai/grab.py records an AI_CLIP_SECONDS RTSP clip to
                 RTU Data/<SiteCode>/<CameraID>/raw_temp/raw.mp4 (+ raw.json with
                 fps / frame times) and extracts AI_FRAME_COUNT evenly spaced
                 frames to images_temp/1..N.jpg (the legacy getImage.py burst).
  2. detection - ai/detect.py: YOLO gauge box on frame 1 -> waterline row ->
                 every linked Sampling table (cubic spline) -> level (lowest
                 wins, legacy multi-gauge rule); optical flow over the frames
                 inside the Velocity sensor's region -> velocity, direction,
                 colour, rain; the annotated frames (green box, red waterline,
                 level) become the public image.gif + image.jpg.
  3. storage   - frame 1 is archived like a snapshot (images/<CameraID>_<ts>.jpg,
                 SNAPSHOT_KEEP_COUNT) and one StationData row is written:
                 DeviceID = CameraID, RecordTime = capture time, Raw = the whole
                 AI result, Data = the values mapped through the station's Water
                 configures rows (Point 1/2 -> WL/WL2 for the camera's Water
                 Level sensor; the Velocity row -> VELOCITY plus DIRECTION,
                 COLOR, RAIN_FLAG from the same flow analysis) and FLOW/AREA
                 from StationData.apply_flow; then the station's HTTP
                 services are queued exactly as for an inbound device payload.

Nothing is written when the model finds no gauge. One camera per tick (a run
costs ~10-20 s); the last outcome per camera is kept in STATUS.
"""

import json
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime

from database import db
from models import Camera, Sampling, Sensor, Settings, Station, StationData
from services import snapshot
from util import statictext, util as Util

logger = logging.getLogger("worker")

AI_DIR = os.path.join(statictext.APP_DIRECTORY, "ai")
GRAB_SCRIPT = os.path.join(AI_DIR, "grab.py")
DETECT_SCRIPT = os.path.join(AI_DIR, "detect.py")
CLIP_NAME = "raw.mp4"
SUBPROCESS_TIMEOUT = (
    180  # seconds; a stuck RTSP open / model load must not block the worker
)
STREAM_TIMEOUT = 15  # seconds the capture waits for frames

_slots = {}  # camera ID -> last interval slot processed (success or failure)
STATUS = {}  # camera ID -> {"at", "ok", "message"}
# Detection backend handed to ai/detect.py: None = AI_BACKEND / torch. When the
# torch backend dies with a native crash (the interpreter exits with one of the
# Windows codes below instead of raising - unsupported CPU / GPU), the worker
# switches to "onnx" (OpenCV DNN, ai/backend_dnn.py) for the rest of its life.
_backend = {"name": None}
NATIVE_CRASH_CODES = {
    "3221225477",
    "3221225501",
    "3221226505",
    "-1073741819",
    "-1073741795",
    "-1073740791",
}


def python_exe():
    """Interpreter for the ai/ scripts: AI_PYTHON from .env, else the running one."""
    return os.getenv("AI_PYTHON") or sys.executable


def _setting(name, default):
    return Util.safe_int(Settings.load_settings().get(name), default)


def interval_minutes():
    return _setting("AI_WORKER_INTERVAL_MINUTES", statictext.AI_WORKER_INTERVAL_MINUTES)


def clip_seconds():
    return _setting("AI_CLIP_SECONDS", statictext.AI_CLIP_SECONDS)


def frame_count():
    return _setting("AI_FRAME_COUNT", statictext.AI_FRAME_COUNT)


def is_eligible(camera):
    """Sensor camera with an uploaded, existing model file."""
    if str(camera.configs().get("CameraType") or "") != "Sensor":
        return False
    path = camera.model_file()
    return bool(path and os.path.isfile(path))


def run_script(script, job):
    """Run one ai/ script with a JSON job; returns the parsed result dict
    (last stdout line) or {"ok": False, "error": ...}."""
    try:
        proc = subprocess.run(
            [python_exe(), script, "-"],
            input=json.dumps(job),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=statictext.APP_DIRECTORY,
            timeout=SUBPROCESS_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"timeout after {SUBPROCESS_TIMEOUT}s"}
    except OSError as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    lines = [line for line in (proc.stdout or "").splitlines() if line.strip()]
    if lines:
        try:
            return json.loads(lines[-1])
        except ValueError:
            pass
    tail = (proc.stderr or "").strip().splitlines()[-3:]
    return {
        "ok": False,
        "error": f"exit {proc.returncode}: {' | '.join(tail) or 'no output'}",
    }


# ----------------------------------------------------------------- configuration
def _configs(row, block):
    """Meta[block]["configs"] of a model row when the block is switched on."""
    data = (row.Meta or {}).get(block) if row is not None else None
    if not isinstance(data, dict) or not data.get("status"):
        return None
    cfg = data.get("configs")
    return cfg if isinstance(cfg, dict) else {}


def _points(rows):
    """First row of a SensorPointsTable -> [x1, y1, x2, y2] or None."""
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        values = [Util.safe_float(row.get(k)) for k in ("p1x", "p1y", "p2x", "p2y")]
        if None not in values:
            return values
    return None


def _sensor(code):
    """Sensor by SensorID code or numeric ID (same lookup as Station.flow_sensor)."""
    code = str(code or "").strip()
    if not code:
        return None
    sensor = Sensor.query.filter(Sensor.SensorID == code).first()
    if sensor is None and code.isdigit():
        sensor = db.session.get(Sensor, int(code))
    return sensor


def _water_rows(station):
    """Checked rows of the station's Water configures: {row key: sensor code}."""
    cfg = _configs(station, "WaterConfigures") or {}
    rows = {}
    for key, entry in cfg.items():
        if (
            isinstance(entry, dict)
            and entry.get("checked")
            and str(entry.get("text") or "").strip()
        ):
            rows[key] = str(entry["text"]).strip()
    return rows


def _level_sensor(sensor, camera):
    """Water Level tab of `sensor` when one of its rows names this camera:
    (samplings {SamplingID: rows}, crop, level_from) or None."""
    cfg = _configs(sensor, "WaterLevels")
    if cfg is None:
        return None
    ids = []
    for row in cfg.get("WaterLevel") or []:
        if not isinstance(row, dict):
            continue
        cam = str(row.get("CameraID") or "").strip()
        if cam and cam not in (camera.CameraID, str(camera.ID)):
            continue
        sid = str(row.get("SamplingID") or "").strip()
        if sid:
            ids.append(sid)
    if not ids:
        return None
    samplings = {}
    for sid in ids:
        sampling = Sampling.query.filter(Sampling.SamplingID == sid).first()
        if sampling is None and sid.isdigit():
            sampling = db.session.get(Sampling, int(sid))
        rows = (
            (_configs(sampling, "SamplingConfigures") or {}).get("CameraConfigures")
            if sampling
            else None
        )
        if rows:
            samplings[sampling.SamplingID] = rows
    if not samplings:
        return None
    return samplings, _points(cfg.get("Points")), str(cfg.get("LevelFrom") or "frame")


def build_context(camera):
    """Everything the detection needs for one camera, from the DB:
    {station, keys: {Data key: source}, samplings, crop, level_from, velocity}.
    `keys` tells which StationData keys the station wants from this camera."""
    station_id = Util.safe_int(camera.configs().get("StationID"), None)
    station = db.session.get(Station, station_id) if station_id is not None else None
    if station is None:
        return None
    keys_map = statictext.StationDataKeys
    ctx = {
        "station": station,
        "keys": {},
        "samplings": {},
        "crop": None,
        "level_from": "frame",
        "velocity": None,
    }
    rows = _water_rows(station)

    for row_key, data_key in (
        ("WaterLevelPoint1_UP", "WaterLevel"),
        ("WaterLevelPoint2_DOWN", "WaterLevel2"),
    ):
        code = rows.get(row_key)
        found = _level_sensor(_sensor(code), camera) if code else None
        if found:
            samplings, crop, level_from = found
            if not ctx[
                "samplings"
            ]:  # the first level sensor defines the detection set-up
                ctx["samplings"], ctx["crop"], ctx["level_from"] = (
                    samplings,
                    crop,
                    level_from,
                )
            ctx["keys"][keys_map[data_key]] = "level"

    code = rows.get("Velocity")
    vel_cfg = _configs(_sensor(code), "Velocities") if code else None
    if vel_cfg is not None:
        region = _points(vel_cfg.get("Points"))
        length = Util.safe_float(vel_cfg.get("Length"))
        if region and length:
            # the flow analysis yields all four at once (legacy CSV columns 17-21)
            ctx["velocity"] = {"region": region, "length": length}
            ctx["keys"][keys_map["Velocity"]] = "velocity"
            ctx["keys"][keys_map["Direction"]] = "direction"
            ctx["keys"][keys_map["WaterColor"]] = "color"
            ctx["keys"][keys_map["RainFlag"]] = "rain"
    return ctx


# ----------------------------------------------------------------------- stages
def capture(camera):
    """Stage 1: RTSP clip to raw_temp/ + frames to images_temp/."""
    url = camera.build_links().get("StreamURL")
    if not url:
        return {"ok": False, "error": "no RTSP address"}
    job = {
        "stream_url": url,
        "clip_path": os.path.join(camera.raw_temp_folder(), CLIP_NAME),
        "seconds": clip_seconds(),
        "frames": frame_count(),
        "frames_dir": camera.images_temp_folder(),
        "timeout": STREAM_TIMEOUT,
    }
    return run_script(GRAB_SCRIPT, job)


def _native_crash(result):
    """True when a script died with an access violation-type exit code."""
    error = str(result.get("error") or "")
    return (
        error.startswith("exit ") and error.split()[1].rstrip(":") in NATIVE_CRASH_CODES
    )


def detect(camera, ctx, grab):
    """Stage 2: water level (+ velocity) on the clip frames, annotated pictures.
    Falls back to the onnx backend (and keeps it) when torch crashes natively."""
    result = _detect(camera, ctx, grab, _backend["name"])
    if _backend["name"] != "onnx" and _native_crash(result):
        logger.warning(
            "AI worker: torch backend crashed (%s) - switching to the ONNX backend (OpenCV DNN)",
            result.get("error"),
        )
        _backend["name"] = "onnx"
        result = _detect(camera, ctx, grab, "onnx")
    return result


def _detect(camera, ctx, grab, backend):
    public = camera.public_folder()
    job = {
        "backend": backend,
        "weights": camera.model_file(),
        "imgsz": Util.safe_int(camera.configs().get("ModelImageSize"), 0) or None,
        "frames": grab.get("frames") or [],
        "frame_times": grab.get("frame_times") or [],
        "crop": ctx["crop"],
        "level_from": ctx["level_from"],
        "samplings": ctx["samplings"],
        "velocity": ctx["velocity"],
        "gif_path": os.path.join(public, Camera.snapshotGif),
        "still_path": os.path.join(public, Camera.snapshotStill),
    }
    return run_script(DETECT_SCRIPT, job)


def _slot_time(moment, minutes):
    """Legacy CSV rule: the clip time rounded up to the next interval slot."""
    seconds = max(1, minutes) * 60
    stamp = int(moment.timestamp())
    rounded = -(-stamp // seconds) * seconds
    return datetime.fromtimestamp(rounded)


def archive_frame(camera, grab):
    """Keep frame 1 in the snapshot archive (images/<CameraID>_<ts>.jpg) and
    return its path relative to RTU Data (for Raw.image)."""
    frames = grab.get("frames") or []
    if not frames or not os.path.isfile(frames[0]):
        return None
    taken = datetime.strptime(grab["captured_at"], "%Y-%m-%dT%H:%M:%S")
    folder = camera.images_folder()
    os.makedirs(folder, exist_ok=True)
    name = (
        f"{camera.safe_id()}_{taken.strftime(snapshot.TIME_FORMAT)}{snapshot.FILE_EXT}"
    )
    shutil.copyfile(frames[0], os.path.join(folder, name))
    snapshot.prune(camera)
    return os.path.relpath(
        os.path.join(folder, name), statictext.APP_DATA_PATH
    ).replace("\\", "/")


def store(camera, ctx, grab, result, image):
    """Stage 3: one StationData row from the AI result; returns the row."""
    station = ctx["station"]
    taken = datetime.strptime(grab["captured_at"], "%Y-%m-%dT%H:%M:%S")
    velocity = result.get("velocity") or {}
    values = {
        "level": result.get("level"),
        "velocity": velocity.get("velocity"),
        "direction": velocity.get("direction"),
        "color": velocity.get("color"),
        "rain": (1 if velocity.get("rain") else 0) if velocity else None,
    }
    formats = {"level": "{:.3f}", "velocity": "{:.3f}"}
    mapped = {
        "DateTime": _slot_time(taken, interval_minutes()).strftime("%Y-%m-%dT%H:%M:%S")
    }
    for key, source in ctx["keys"].items():
        value = values.get(source)
        if value is None:
            continue
        mapped[key] = formats[source].format(value) if source in formats else str(value)
    StationData.apply_flow(station, mapped)

    raw = dict(result)
    raw.update(
        {
            "source": "ai",
            "camera": camera.CameraID,
            "model": os.path.basename(camera.model_file() or ""),
            "image": image,
            "clip": {
                k: grab.get(k)
                for k in (
                    "fps",
                    "frame_count",
                    "frame_indices",
                    "frame_times",
                    "captured_at",
                )
            },
        }
    )
    row = StationData(
        StationID=station.StationID,
        DeviceID=camera.CameraID,
        RecordTime=taken,
        Data=mapped,
        Raw=raw,
        CreateDate=datetime.now(),
    )
    db.session.add(row)
    db.session.commit()
    try:
        from models.httplog import HttpLog

        HttpLog.enqueue_for_station(station, row)
    except Exception as e:
        db.session.rollback()
        logger.warning("HttpLog enqueue failed for %s: %s", camera.CameraID, e)
    return row


def process(camera):
    """All stages for one camera; returns (ok, message)."""
    ctx = build_context(camera)
    if ctx is None:
        return False, "no station on the camera"
    if not ctx["samplings"]:
        return False, "no Water Level sensor / Sampling table linked to this camera"

    grab = capture(camera)
    if not grab.get("ok"):
        return False, f"capture failed: {grab.get('error')}"
    image = archive_frame(camera, grab)

    result = detect(camera, ctx, grab)
    if not result.get("ok"):
        return False, f"detection failed: {result.get('error')}"
    if not result.get("detected") or result.get("level") is None:
        snapshot.rebuild_public(camera)  # keep the CCTV page picture fresh anyway
        return False, "no gauge detected on the picture (nothing stored)"

    row = store(camera, ctx, grab, result, image)
    velocity = result.get("velocity") or {}
    parts = [
        f"WL {result['level']:.3f} m (conf {result.get('conf')}, {result.get('sampling')})"
    ]
    if velocity:
        parts.append(
            f"v {velocity.get('velocity')} m/s {velocity.get('direction')}, {velocity.get('color_name')}"
        )
    parts.append(
        f"row {row.ID}, {result.get('backend')} {result.get('device')}, {grab.get('elapsed_ms', 0) + result.get('elapsed_ms', 0)} ms"
    )
    return True, "; ".join(parts)


def run():
    """Worker job: process one due camera (Sensor + model) per tick."""
    minutes = interval_minutes()
    if minutes <= 0:
        return None
    now = datetime.now()
    slot = int(now.timestamp() // (minutes * 60))
    for camera in Camera.query.filter(Camera.Status == 1).order_by(Camera.ID).all():
        if not is_eligible(camera) or _slots.get(camera.ID) == slot:
            continue
        _slots[camera.ID] = slot
        try:
            ok, message = process(camera)
        except Exception as e:  # never let one camera kill the job
            db.session.rollback()
            ok, message = False, f"{type(e).__name__}: {e}"
        STATUS[camera.ID] = {"at": now, "ok": ok, "message": message}
        (logger.info if ok else logger.warning)(
            "AI worker %s: %s", camera.CameraID, message
        )
        return f"{camera.CameraID}: {message}"  # one camera per tick
    return None
