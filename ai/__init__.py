"""AI water-level detection package (see ai/README.md).

Nothing here imports torch or the vendored YOLOv5 runtime at module level:
`ai/yolov5/` ships packages literally named `models` and `utils`, which would
shadow the dashboard's own `models/` package inside the web process. All
inference therefore runs in a separate interpreter through `ai/detect.py`
(`python313\\python.exe ai\\detect.py`), and the web app only exchanges JSON
with that process.
"""
