"""Step-by-step check of the AI runtime on this machine (run on a new server):

    python313\\python.exe ai\\doctor.py [weights]

Each step prints before it runs, so when the interpreter dies with a native
crash (Windows exit code 3221225477 = 0xC0000005 access violation - usually a
CPU without AVX2 or an oneDNN kernel the CPU cannot execute) the last line
shows where. Try again with AI_NO_MKLDNN=1 (and AI_DEVICE=cpu) in .env when
step 5 or 6 crashes.
"""

import os
import platform
import sys
import time

AI_DIR = os.path.dirname(os.path.abspath(__file__))
if AI_DIR not in sys.path:
    sys.path.insert(0, AI_DIR)


def step(n, text):
    print(f"[{n}] {text}", flush=True)


def main():
    weights = sys.argv[1] if len(sys.argv) > 1 else None
    step(
        1,
        f"python {platform.python_version()} on {platform.platform()} ({platform.machine()}, {os.cpu_count()} cpus)",
    )
    step(
        2,
        f"env AI_DEVICE={os.getenv('AI_DEVICE', '')!r} AI_NO_MKLDNN={os.getenv('AI_NO_MKLDNN', '')!r}",
    )

    import numpy
    import cv2

    step(3, f"numpy {numpy.__version__}, opencv {cv2.__version__} imported")

    import torch

    cap = getattr(torch.backends.cpu, "get_cpu_capability", lambda: "?")()
    step(
        4,
        f"torch {torch.__version__} imported: cpu capability={cap}, "
        f"cuda available={torch.cuda.is_available()}, mkldnn={torch.backends.mkldnn.is_available()}",
    )
    if torch.cuda.is_available():
        try:
            print(
                f"    gpu: {torch.cuda.get_device_name(0)}, capability {torch.cuda.get_device_capability(0)}",
                flush=True,
            )
        except Exception as e:
            print(f"    gpu query failed: {e}", flush=True)

    import detector

    detector.prepare_runtime()
    step(5, f"cpu conv2d test (mkldnn enabled={torch.backends.mkldnn.enabled}) ...")
    with torch.no_grad():
        y = torch.nn.Conv2d(3, 8, 3)(torch.zeros(1, 3, 64, 64))
    print(f"    ok, output {tuple(y.shape)}", flush=True)

    if torch.cuda.is_available():
        step(6, "cuda conv2d test ...")
        try:
            with torch.no_grad():
                y = torch.nn.Conv2d(3, 8, 3).cuda()(
                    torch.zeros(1, 3, 64, 64, device="cuda")
                )
            print(f"    ok, output {tuple(y.shape)}", flush=True)
        except Exception as e:
            print(
                f"    cuda unusable: {type(e).__name__}: {str(e).splitlines()[0]} (the detector falls back to the CPU)",
                flush=True,
            )

    if not weights:
        names = (
            sorted(n for n in os.listdir(detector.MODEL_DIR) if n.endswith(".pt"))
            if os.path.isdir(detector.MODEL_DIR)
            else []
        )
        weights = names[0] if names else None
    if not weights:
        step(
            7,
            "no model file under ai/trained_models - upload one on the camera form, done",
        )
        return 0
    step(
        7,
        f"loading model {weights} on device {os.getenv('AI_DEVICE', '') or 'auto'} ...",
    )
    t = time.perf_counter()
    model = detector.load_model(weights)
    print(f"    ok on {model[3]} in {time.perf_counter() - t:.1f}s", flush=True)
    step(8, "detection on a blank frame ...")
    t = time.perf_counter()
    result = detector.detect_waterline(
        model, numpy.zeros((1080, 1920, 3), dtype=numpy.uint8)
    )
    print(
        f"    ok ({'no box' if result is None else 'box found'}) in {time.perf_counter() - t:.1f}s - the AI runtime works on this machine",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
