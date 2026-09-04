"""Export uploaded YOLOv5 checkpoints to ONNX so the detector can run without
torch (OpenCV DNN backend, ai/backend_dnn.py) on servers whose CPU / GPU the
installed torch build cannot use.

    python313\\python.exe ai\\export_onnx.py                # every .pt under ai/trained_models
    python313\\python.exe ai\\export_onnx.py CAM-TC04.pt   # one model
    python313\\python.exe ai\\export_onnx.py CAM-TSKB.pt --imgsz 1024
    python313\\python.exe ai\\export_onnx.py --missing      # app_run.bat: only models without .onnx, sizes from the DB

Writes <name>.onnx next to the .pt (opset 12, static 1x3xSxS input "images",
output "output0" = 1 x N x (5 + classes), the classic YOLOv5 layout). Needs
torch + onnx, i.e. a PC where torch works; the dashboard runs it automatically
after a model upload (Camera.store_model) and ignores failures.
"""

import argparse
import os
import sys

AI_DIR = os.path.dirname(os.path.abspath(__file__))
if AI_DIR not in sys.path:
    sys.path.insert(0, AI_DIR)

import detector  # noqa: E402

DEFAULT_OPSET = 12


def export(weights, imgsz=None, opset=DEFAULT_OPSET):
    """Export one checkpoint; returns the .onnx path."""
    import torch

    path = detector.resolve_weights(weights)
    if not path or not os.path.isfile(path):
        raise FileNotFoundError(f"weights not found: {weights}")
    model, _stride, _names, _device, _backend = detector.load_model(
        path, "cpu", "torch"
    )  # export always needs the torch model
    net = model.model  # the fused PyTorch module inside DetectMultiBackend
    net.eval()
    for module in net.modules():  # export mode of the Detect head: plain tensor output
        if module.__class__.__name__ == "Detect":
            module.export = True
            module.inplace = False
    size = int(imgsz or detector.DEFAULT_IMGSZ)
    dummy = torch.zeros(1, 3, size, size)
    out_path = os.path.splitext(path)[0] + ".onnx"
    tmp = out_path + ".part"
    torch.onnx.export(
        net,
        dummy,
        tmp,
        opset_version=opset,
        input_names=["images"],
        output_names=["output0"],
        dynamo=False,
    )
    os.replace(tmp, out_path)
    return out_path


def sizes_from_db():
    """{weights file name: ModelImageSize} of every camera (Camera configures);
    {} when the database is not reachable. Imported lazily: the app must be
    loaded before detector.prepare_runtime() puts ai/yolov5 on sys.path."""
    try:
        sys.path.insert(0, os.path.dirname(AI_DIR))
        from app import app
        from models import Camera

        with app.app_context():
            sizes = {}
            for camera in Camera.query.all():
                cfg = camera.configs()
                name = str(cfg.get("TrainedModel") or "").strip()
                size = str(cfg.get("ModelImageSize") or "").strip()
                if name and size.isdigit():
                    sizes[name] = int(size)
            return sizes
    except Exception as e:
        print(
            f"sizes from the database unavailable ({type(e).__name__}), using {detector.DEFAULT_IMGSZ}",
            flush=True,
        )
        return {}


def export_missing():
    """app_run.bat / worker start-up: export every .pt that has no .onnx yet,
    each in its own interpreter (a torch crash must not take this one down),
    with the camera's ModelImageSize from the database. Always returns 0."""
    import subprocess

    names = (
        sorted(n for n in os.listdir(detector.MODEL_DIR) if n.lower().endswith(".pt"))
        if os.path.isdir(detector.MODEL_DIR)
        else []
    )
    missing = [
        n
        for n in names
        if not os.path.isfile(
            os.path.join(detector.MODEL_DIR, os.path.splitext(n)[0] + ".onnx")
        )
    ]
    if not missing:
        print(f"ONNX models up to date ({len(names)} model(s))", flush=True)
        return 0
    sizes = sizes_from_db()
    for name in missing:
        args = [
            sys.executable,
            os.path.abspath(__file__),
            name,
            "--imgsz",
            str(sizes.get(name, detector.DEFAULT_IMGSZ)),
        ]
        try:
            proc = subprocess.run(
                args,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=300,
            )
            tail = ((proc.stdout or "") + (proc.stderr or "")).strip().splitlines()
            print(tail[-1] if tail else f"{name}: exit {proc.returncode}", flush=True)
        except subprocess.TimeoutExpired:
            print(f"{name} FAILED: timeout", flush=True)
        if not os.path.isfile(
            os.path.join(detector.MODEL_DIR, os.path.splitext(name)[0] + ".onnx")
        ):
            print(
                f"{name}: no ONNX created - torch cannot run on this machine; export on a PC and copy the .onnx here",
                flush=True,
            )
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--missing",
        action="store_true",
        help="export only the models without .onnx, sizes from the database (used by app_run.bat)",
    )
    parser.add_argument(
        "weights",
        nargs="*",
        help="model file(s); default: every .pt in ai/trained_models",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=None,
        help="input size (default 640; 1024 for TS.KB-type models)",
    )
    args = parser.parse_args(argv)
    if args.missing:
        return export_missing()

    names = args.weights or sorted(
        n for n in os.listdir(detector.MODEL_DIR) if n.lower().endswith(".pt")
    )
    if not names:
        print("no model to export", flush=True)
        return 1
    failed = 0
    for name in names:
        try:
            out = export(name, args.imgsz)
            print(f"{name} -> {out} ({os.path.getsize(out) // 1024} KB)", flush=True)
        except Exception as e:
            failed += 1
            print(
                f"{name} FAILED: {type(e).__name__}: {e}", file=sys.stderr, flush=True
            )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
