# ai/ — camera water-level detection

Clean re-implementation of the core of the legacy `xserver_new.py` water-level
server (YOLOv5 gauge detection + pixel → level calibration, optical-flow
velocity). The legacy folder itself is gone; its models were imported into
`trained_models/` and its sampling tables into the Sampling records.

## Layout

| Path | Purpose |
|---|---|
| `grab.py` | CLI, stage 1 of the AI worker: records an RTSP clip (`raw_temp/raw.mp4` + `raw.json`), extracts N evenly spaced frames to `images_temp/1..N.jpg` and animates them into the public `image.gif`. |
| `detect.py` | CLI: one water-level detection job as JSON (file or stdin) → one JSON result on stdout (stage 2: level, velocity/direction/colour/rain, annotated gif). |
| `animation.py` | Pictures → animated GIF (Pillow), used by `grab.py`; importable from the web app as `ai.animation`. |
| `velocity.py` | Port of the legacy `detect_movement()`: Farneback optical flow inside the velocity region → m/s (scaled by the region length and real frame spacing), direction, dominant colour (OpenCV k-means), rain flag. |
| `doctor.py` | Step-by-step runtime check for a new server (imports, CPU capability, CPU/CUDA conv test, model load, blank detection); shows where a native crash happens. |
| `backend_dnn.py` | torch-free inference: OpenCV DNN on the `<model>.onnx` twin (letterbox, decode, NMS). Used when `AI_BACKEND=onnx` or after the torch backend crashed. |
| `export_onnx.py` | Exports the uploaded `.pt` models to `.onnx` (opset 12, static input); run automatically after a model upload, or by hand on a PC where torch works. |
| `detector.py` | Loads a YOLOv5 checkpoint (cached per process) and finds the waterline on a frame: the box touching the water (smallest `y2`), its bottom row is the waterline. |
| `calibration.py` | Sampling rows `{x: pixel row, y: level m}` → cubic spline → level, extrapolated at both ends like the legacy code. Pure numpy/scipy. |
| `capture.py` | Frame sources: image file, one RTSP frame (`grab_frame`), RTSP burst (`grab_burst`, for the future velocity job), ISAPI snapshot (`fetch_snapshot`, Basic then Digest auth). |
| `yolov5/` | Vendored YOLOv5 runtime (`models/`, `utils/`, AGPL-3.0 licence kept) copied unchanged from the legacy YOLOv5 code. |
| `trained_models/` | Uploaded weights, one per camera: `<CameraID>.pt` (camera form → `POST /api/cameras/modelupload`). Git-ignored. |
| `requirements.txt` | Extra packages installed into the bundled `python313` for this folder. |

## Why a separate process

`ai/yolov5` contains packages literally named `models` and `utils`; the pickled
YOLOv5 checkpoints reference `models.yolo.*` classes by that name, so the
folder must be first on `sys.path`. Inside the Flask process `models` is the
SQLAlchemy package, so the detector must never be imported there. The web app
(worker job, later) runs:

```
python313\python.exe ai\detect.py job.json
```

and parses the last stdout line (`services/ai_worker.py::run_script`, also used for `ai/grab.py` because OpenCV's blocking RTSP
calls would stall the gevent web server). torch, ultralytics and friends are therefore
loaded only in that short-lived interpreter. `detector.prepare_runtime()` also
restores `torch.load(weights_only=False)` (torch ≥ 2.6 rejects the old
checkpoints otherwise) and aliases `pathlib.PosixPath` on Windows. `detector.load_model()` warms the model up on the chosen device and falls back to the CPU when the CUDA build cannot run on the installed GPU ("no kernel image is available" on cards older than the torch wheel supports); `AI_DEVICE=cpu` in `.env` forces the CPU; `AI_NO_MKLDNN=1` disables the oneDNN CPU kernels and `AI_TORCH_THREADS=n` caps the CPU threads. When the torch build cannot run at all (the interpreter dies with exit 0xC0000005 on an old CPU / VM), `services/ai_worker.py` switches to the **onnx backend** (`ai/backend_dnn.py`, OpenCV DNN on the exported `.onnx`, ~0.3 s per frame on a CPU) and stays there; `AI_BACKEND=onnx` selects it from the start. The `.onnx` files are produced by `ai/export_onnx.py` (automatically after an upload where torch works; otherwise export on a PC and copy the file next to the `.pt`).

## Job / result

```json
{
  "weights": "CAM-TC04.pt",
  "imgsz": 640,
  "image_path": "some.jpg",          // or "frames": [...clip frames...], "stream_url", "snapshot_url"
  "crop": [x1, y1, x2, y2],           // optional region given to the model
  "sampling": [{"x": "1", "y": "2.18"}, ...],
  "level_from": "frame",             // or "crop" when the table was surveyed on the cropped picture
  "out_image": "static/data/cameras/CAM-TC04/detected.jpg"
}
```

Result: `{"ok": true, "y": 512, "y_crop": 512, "bbox": [...], "conf": 0.91,
"detections": 1, "level": 0.97, "in_range": true, "image": "...", "device":
"cuda:0", "elapsed_ms": 240}` — or `{"ok": false, "error": "..."}` with exit
code 1.

## Models per station (from the legacy server)

| Station | Weights | imgsz |
|---|---|---|
| TC.04 | `TC.04.pt` (legacy code named `TC.04v6.pt`, not available) | 640 |
| TC.12 | `TC_v1.pt` (generic fallback; `tc12_1.pt` not available) | 640 |
| TTC.01 | `TTC01_v1.pt` | 640 |
| TS.KB | `tskb_pillar_mids2.pt` | 1024 |
| TMB.01 | `tmb_mar_4.pt` (several gauges → smallest `y2` box) | 640 |
