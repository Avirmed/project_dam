"""Animated GIF from pictures (Pillow only, no torch / OpenCV).

Shared by ai/grab.py (raw clip frames -> public image.gif) and ai/detect.py
(annotated frames -> the same file); importable from the web process as
`ai.animation` when a rebuild is needed.
"""

import logging
import os

from PIL import Image

logger = logging.getLogger("worker")

GIF_WIDTH = 640  # frames are downscaled to this width
GIF_FRAME_MS = 1000  # time each frame is shown


def _fit(im, width):
    if im.width > width:
        im = im.resize((width, max(1, round(im.height * width / im.width))))
    return im


def save_animation(images, out_path, frame_ms=GIF_FRAME_MS):
    """Write PIL RGB images as a looping GIF, atomically. False when empty."""
    if not images:
        return False
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    tmp = os.path.splitext(out_path)[0] + ".part.gif"
    images[0].save(
        tmp,
        format="GIF",
        save_all=True,
        append_images=images[1:],
        duration=frame_ms,
        loop=0,
    )
    os.replace(tmp, out_path)
    return True


def build_animation(paths, out_path, width=GIF_WIDTH, frame_ms=GIF_FRAME_MS):
    """GIF from picture files (frames in the given order, looping)."""
    frames = []
    for path in paths:
        try:
            with Image.open(path) as im:
                frames.append(_fit(im.convert("RGB"), width))
        except OSError as e:
            logger.warning("Animation frame skipped %s: %s", path, e)
    return save_animation(frames, out_path, frame_ms)


def build_animation_from_arrays(
    frames_bgr, out_path, width=GIF_WIDTH, frame_ms=GIF_FRAME_MS
):
    """GIF from OpenCV (BGR numpy) frames already in memory."""
    images = [_fit(Image.fromarray(frame[:, :, ::-1]), width) for frame in frames_bgr]
    return save_animation(images, out_path, frame_ms)
