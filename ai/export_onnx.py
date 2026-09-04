"""Export uploaded YOLOv5 checkpoints to ONNX so the detector can run without
torch (OpenCV DNN backend, ai/backend_dnn.py) on servers whose CPU / GPU the
installed torch build cannot use.

    python313\\python.exe ai\\export_onnx.py                # every .pt under ai/trained_models
    python313\\python.exe ai\\export_onnx.py CAM-TC04.pt   # one model
    python313\\python.exe ai\\export_onnx.py CAM-TSKB.pt --imgsz 1024

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
    model, _stride, _names, _device = detector.load_model(path, "cpu")
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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("weights", nargs="*", help="model file(s); default: every .pt in ai/trained_models")
    parser.add_argument("--imgsz", type=int, default=None, help="input size (default 640; 1024 for TS.KB-type models)")
    args = parser.parse_args(argv)

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
            print(f"{name} FAILED: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
