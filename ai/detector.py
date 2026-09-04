"""YOLOv5 waterline detector (port of the legacy xserver_new.py `run()`).

The trained models find the water gauge / water boundary as a bounding box;
the bottom edge of that box (largest y of the box, `y2`) is the waterline row
that the calibration table converts into a level. With several boxes (multi
gauge stations) the box whose bottom edge is highest on the frame - smallest
y2 - is the one touching the water, as in the legacy TMB.01 rule.

IMPORTANT: importing this module puts `ai/yolov5` on sys.path, whose `models`
and `utils` packages would shadow the dashboard's own `models/` package. Only
import it from a dedicated interpreter (ai/detect.py), never from the web app.
"""

import functools
import os
import pathlib
import sys
import time

import numpy as np

AI_DIR = os.path.dirname(os.path.abspath(__file__))
YOLO_DIR = os.path.join(AI_DIR, "yolov5")
MODEL_DIR = os.path.join(AI_DIR, "trained_models")

DEFAULT_IMGSZ = 640
DEFAULT_CONF = 0.25
DEFAULT_IOU = 0.45
MAX_DET = 100

_models = {}  # (weights path, device) -> (model, stride, names)


def prepare_runtime():
    """Make the vendored YOLOv5 code importable and loadable.

    - `ai/yolov5` goes first on sys.path (its packages are `models`, `utils`).
    - torch >= 2.6 defaults `torch.load(weights_only=True)`, which rejects the
      YOLOv5 checkpoints (they pickle whole model classes); the vendored
      `attempt_load()` predates that change, so default it back to False here.
    - Checkpoints trained on Linux pickle `pathlib.PosixPath`, which cannot be
      instantiated on Windows; alias it like the legacy server did.
    """
    if YOLO_DIR not in sys.path:
        sys.path.insert(0, YOLO_DIR)
    os.environ.setdefault("YOLOv5_VERBOSE", "False")  # keep stdout for the JSON result

    import torch

    if not getattr(torch.load, "_ai_weights_only_patch", False):
        original = torch.load

        @functools.wraps(original)
        def load(*args, **kwargs):
            kwargs.setdefault("weights_only", False)
            return original(*args, **kwargs)

        load._ai_weights_only_patch = True
        torch.load = load

    if os.name == "nt":
        pathlib.PosixPath = pathlib.WindowsPath


def resolve_weights(weights):
    """Absolute path of a weights file: as given, or by name under trained_models/."""
    if not weights:
        return None
    path = str(weights)
    if not os.path.isabs(path) and not os.path.isfile(path):
        candidate = os.path.join(MODEL_DIR, path)
        if os.path.isfile(candidate):
            return candidate
    return os.path.abspath(path)


def _build(path, device):
    """DetectMultiBackend on `device` plus one warm-up forward, so a GPU whose
    architecture the installed torch build does not support ("no kernel image
    is available") fails here, not in the middle of a detection."""
    import torch
    from models.common import DetectMultiBackend
    from utils.torch_utils import select_device

    torch_device = select_device(device, newline=False)
    model = DetectMultiBackend(
        path, device=torch_device, dnn=False, data=None, fp16=False
    )
    with torch.no_grad():
        model(torch.zeros(1, 3, 64, 64, device=torch_device))
    return model, torch_device


def load_model(weights, device=""):
    """Load (and cache) a YOLOv5 checkpoint. Returns (model, stride, names, device).

    device: "" = AI_DEVICE from the environment, else auto (CUDA when usable,
    else CPU). When the CUDA build cannot run on the installed GPU (older card
    than the torch wheel supports, driver problems) the model is loaded again
    on the CPU, so a server never needs manual configuration for that."""
    prepare_runtime()

    path = resolve_weights(weights)
    if not path or not os.path.isfile(path):
        raise FileNotFoundError(f"weights not found: {weights}")

    device = str(device or os.getenv("AI_DEVICE") or "").strip().lower()
    key = (path, device)
    if key not in _models:
        try:
            model, torch_device = _build(path, device)
        except Exception as e:
            if device == "cpu":
                raise
            print(
                f"CUDA unusable ({type(e).__name__}: {str(e).splitlines()[0]}), falling back to CPU",
                file=sys.stderr,
            )
            model, torch_device = _build(path, "cpu")
        _models[key] = (model, int(model.stride), model.names, torch_device)
    return _models[key]


def detect_waterline(
    model_tuple,
    image_bgr,
    imgsz=DEFAULT_IMGSZ,
    crop=None,
    conf_thres=DEFAULT_CONF,
    iou_thres=DEFAULT_IOU,
):
    """Find the waterline on one BGR frame.

    crop: optional (x1, y1, x2, y2) region (full-frame pixels) given to the
    model; boxes are reported in full-frame coordinates and, additionally,
    relative to the crop (`y_crop`) because some calibration tables were
    surveyed on the cropped picture.

    Returns None when nothing is detected, else a dict:
    {bbox, y, y_crop, conf, cls, detections, crop, elapsed_ms}.
    """
    import torch
    from utils.augmentations import letterbox
    from utils.general import non_max_suppression, scale_boxes

    model, stride, _names, device = model_tuple
    started = time.perf_counter()

    height, width = image_bgr.shape[:2]
    x1 = y1 = 0
    x2, y2 = width, height
    if crop:
        x1, y1, x2, y2 = [int(round(float(v))) for v in crop[:4]]
        x1, x2 = sorted((max(0, min(width, x1)), max(0, min(width, x2))))
        y1, y2 = sorted((max(0, min(height, y1)), max(0, min(height, y2))))
        if x2 - x1 < 2 or y2 - y1 < 2:  # degenerate crop: use the whole frame
            x1, y1, x2, y2 = 0, 0, width, height
    region = image_bgr[y1:y2, x1:x2]

    size = int(imgsz or DEFAULT_IMGSZ)
    # Same pre-processing as the legacy run(): square letterbox (auto=False),
    # HWC BGR -> CHW RGB, 0..1 float, batch of one.
    im = letterbox(region, (size, size), stride=stride, auto=False)[0]
    im = np.ascontiguousarray(im.transpose((2, 0, 1))[::-1])
    tensor = torch.from_numpy(im).to(device).float() / 255.0
    tensor = tensor[None]

    with torch.no_grad():
        pred = model(tensor)
    det = non_max_suppression(pred, conf_thres, iou_thres, max_det=MAX_DET)[0]
    if det is None or not len(det):
        return None

    det[:, :4] = scale_boxes(tensor.shape[2:], det[:, :4], region.shape).round()
    boxes = det.cpu().numpy()
    pick = int(np.argmin(boxes[:, 3]))  # box touching the water: smallest y2
    bx1, by1, bx2, by2, conf, cls = boxes[pick][:6]

    return {
        "bbox": [int(bx1) + x1, int(by1) + y1, int(bx2) + x1, int(by2) + y1],
        "y": int(by2) + y1,
        "y_crop": int(by2),
        "conf": round(float(conf), 4),
        "cls": int(cls),
        "detections": int(len(boxes)),
        "crop": [x1, y1, x2, y2] if crop else None,
        "elapsed_ms": int((time.perf_counter() - started) * 1000),
    }


def annotate(image_bgr, result, label=None):
    """Copy of the frame with the waterline (red row), the box and a label."""
    import cv2

    out = image_bgr.copy()
    if not result:
        return out
    height, width = out.shape[:2]
    y = max(0, min(height - 1, int(result["y"])))
    cv2.line(out, (0, y), (width - 1, y), (0, 0, 255), 2)
    bx1, by1, bx2, by2 = result["bbox"]
    cv2.rectangle(
        out, (bx1, by1), (bx2, by2), (0, 255, 0), 2
    )  # green box, red waterline (legacy look)
    if result.get("crop"):
        cx1, cy1, cx2, cy2 = result["crop"]
        cv2.rectangle(out, (cx1, cy1), (cx2, cy2), (0, 255, 255), 1)
    if label:
        org = (min(bx2 + 8, width - 200), max(24, y - 8))
        cv2.putText(
            out, label, org, cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 4, cv2.LINE_AA
        )
        cv2.putText(
            out, label, org, cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA
        )
    return out
