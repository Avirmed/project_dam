"""YOLOv5 inference through OpenCV's DNN module (ONNX models, no torch).

Fallback backend for servers where the installed torch build cannot run
(GPU too old, CPU without the needed instruction set - the process dies with
an access violation). Needs only opencv-python + numpy, which every install
has, and the <model>.onnx exported next to the .pt by ai/export_onnx.py.

Same contract as the torch path in ai/detector.py: `load(path)` -> handle,
`detect(handle, region_bgr, size, conf, iou)` -> numpy array of
[x1, y1, x2, y2, conf, cls] rows in region pixels (empty when nothing found).
"""

import os

import cv2
import numpy as np

_nets = {}  # onnx path -> cv2.dnn.Net


def onnx_path(weights_path):
    """<name>.onnx next to a .pt (or the path itself when already .onnx)."""
    root, ext = os.path.splitext(str(weights_path))
    return weights_path if ext.lower() == ".onnx" else root + ".onnx"


def load(weights_path):
    """cv2.dnn network for the ONNX twin of `weights_path` (cached)."""
    path = onnx_path(weights_path)
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"ONNX model not found: {path} (export it with ai/export_onnx.py on a PC where torch works)"
        )
    if path not in _nets:
        net = cv2.dnn.readNetFromONNX(path)
        net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        _nets[path] = net
    return _nets[path]


def letterbox(image, size):
    """Square letterbox like the YOLOv5 loader (auto=False): returns the padded
    picture plus the scale and the (left, top) padding used to map boxes back."""
    height, width = image.shape[:2]
    ratio = min(size / height, size / width)
    new_w, new_h = int(round(width * ratio)), int(round(height * ratio))
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    canvas = np.full((size, size, 3), 114, dtype=np.uint8)
    left = (size - new_w) // 2
    top = (size - new_h) // 2
    canvas[top : top + new_h, left : left + new_w] = resized
    return canvas, ratio, left, top


def detect(net, region_bgr, size, conf_thres, iou_thres, max_det=100):
    """Run the network on one BGR picture; boxes in picture pixels."""
    canvas, ratio, left, top = letterbox(region_bgr, int(size))
    blob = cv2.dnn.blobFromImage(canvas, 1 / 255.0, (int(size), int(size)), swapRB=True, crop=False)
    net.setInput(blob)
    out = net.forward()
    rows = out.reshape(-1, out.shape[-1])  # (N, 5 + classes): cx, cy, w, h, obj, cls...
    if rows.shape[1] < 6:
        return np.zeros((0, 6), dtype=np.float32)

    obj = rows[:, 4]
    cls_scores = rows[:, 5:]
    cls = cls_scores.argmax(axis=1)
    conf = obj * cls_scores[np.arange(len(rows)), cls]
    keep = conf >= conf_thres
    if not keep.any():
        return np.zeros((0, 6), dtype=np.float32)
    rows, conf, cls = rows[keep], conf[keep], cls[keep]

    cx, cy, w, h = rows[:, 0], rows[:, 1], rows[:, 2], rows[:, 3]
    x1 = (cx - w / 2 - left) / ratio
    y1 = (cy - h / 2 - top) / ratio
    x2 = (cx + w / 2 - left) / ratio
    y2 = (cy + h / 2 - top) / ratio
    height, width = region_bgr.shape[:2]
    x1, x2 = np.clip(x1, 0, width - 1), np.clip(x2, 0, width - 1)
    y1, y2 = np.clip(y1, 0, height - 1), np.clip(y2, 0, height - 1)

    boxes_xywh = [[float(a), float(b), float(c - a), float(d - b)] for a, b, c, d in zip(x1, y1, x2, y2)]
    picked = cv2.dnn.NMSBoxes(boxes_xywh, conf.astype(float).tolist(), float(conf_thres), float(iou_thres))
    picked = np.array(picked).reshape(-1)[:max_det]
    if not len(picked):
        return np.zeros((0, 6), dtype=np.float32)
    return np.stack(
        [
            np.round(x1[picked]),
            np.round(y1[picked]),
            np.round(x2[picked]),
            np.round(y2[picked]),
            conf[picked],
            cls[picked].astype(np.float32),
        ],
        axis=1,
    ).astype(np.float32)
