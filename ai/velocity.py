"""Surface velocity, flow direction, water colour and rain flag from a clip.

Port of the legacy xserver_new.py `detect_movement()` / `detect_color()`:
dense optical flow (Farneback) between consecutive frames inside the
detection region, the mean horizontal displacement of the "consistent" flow
vectors scaled by the region's real-world width gives m/s; the dominant flow
sign gives the direction, many vertically moving points mean rain, and the
region's dominant colour (k-means, one cluster) is the water colour.

Differences to the legacy code (deliberate): the frame spacing comes from the
clip (`frame_times`, real fps) instead of the processing time between two
`imread` calls, the region is given in full-frame pixels (the legacy resized
every frame to 1080x640 first), and k-means runs with OpenCV instead of
scikit-learn.
"""

import cv2
import numpy as np

STEP = 15  # grid spacing of the sampled flow vectors (px)
VERTICAL_LIMIT = 0.5  # |other component| allowed for a "horizontal" / "vertical" vector
RAIN_POINTS = 100  # vertically moving grid points over the clip that mean "rain"
BLUR = 3

# Legacy `css3_colors` table: the dominant colour is reported as the nearest name.
COLOR_NAMES = {
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "cyan": (0, 255, 255),
    "magenta": (255, 0, 255),
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "gray": (169, 169, 169),
    "lightgray": (211, 211, 211),
    "brown": (139, 69, 19),
    "orange": (255, 165, 0),
    "pink": (255, 192, 203),
    "purple": (128, 0, 128),
    "lightblue": (173, 216, 230),
    "darkblue": (0, 0, 139),
}


def clamp_region(region, width, height):
    """(x1, y1, x2, y2) clipped to the frame; None when degenerate."""
    if not region:
        return None
    try:
        x1, y1, x2, y2 = [int(round(float(v))) for v in region[:4]]
    except (TypeError, ValueError):
        return None
    x1, x2 = sorted((max(0, min(width, x1)), max(0, min(width, x2))))
    y1, y2 = sorted((max(0, min(height, y1)), max(0, min(height, y2))))
    if x2 - x1 < STEP * 2 or y2 - y1 < STEP * 2:
        return None
    return x1, y1, x2, y2


def dominant_color(bgr_region):
    """Dominant colour of a region: (hex "#rrggbb", (r, g, b), nearest name)."""
    pixels = bgr_region.reshape(-1, 3).astype(np.float32)
    if len(pixels) > 20000:  # subsample: k-means on every pixel of 1080p is slow
        pixels = pixels[
            np.random.default_rng(0).choice(len(pixels), 20000, replace=False)
        ]
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
    _, _, centers = cv2.kmeans(pixels, 1, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
    b, g, r = [int(round(v)) for v in centers[0]]
    rgb = (r, g, b)
    name = min(
        COLOR_NAMES,
        key=lambda n: sum((a - c) ** 2 for a, c in zip(rgb, COLOR_NAMES[n])),
    )
    return f"#{r:02x}{g:02x}{b:02x}", rgb, name


def _prepare(frame, region):
    x1, y1, x2, y2 = region
    gray = cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY)
    return cv2.GaussianBlur(gray, (BLUR, BLUR), 0)


def analyse(frames, frame_times, region, length_m):
    """Run the analysis on BGR frames (oldest first).

    frames      : list of numpy arrays (same size)
    frame_times : seconds of each frame from the clip start
    region      : (x1, y1, x2, y2) detection region in frame pixels
    length_m    : real-world width of the region in metres (scale)

    Returns a dict {velocity, direction, color, color_name, color_rgb, rain,
    rain_points, pairs, region, scale} or None when the input is unusable.
    """
    if len(frames) < 2 or len(frame_times) != len(frames):
        return None
    height, width = frames[0].shape[:2]
    region = clamp_region(region, width, height)
    if region is None or not length_m or float(length_m) <= 0:
        return None
    x1, y1, x2, y2 = region
    scale = float(length_m) / float(x2 - x1)  # metres per pixel

    color_hex, color_rgb, color_name = dominant_color(frames[0][y1:y2, x1:x2])

    prev = _prepare(frames[0], region)
    velocities, right_votes, left_votes, rain_points = [], 0, 0, 0
    for index in range(1, len(frames)):
        dt = float(frame_times[index]) - float(frame_times[index - 1])
        gray = _prepare(frames[index], region)
        flow = cv2.calcOpticalFlowFarneback(prev, gray, None, 0.5, 3, 15, 1, 5, 1.2, 0)
        prev = gray
        if dt <= 0:
            continue
        fx, fy = flow[..., 0], flow[..., 1]

        # dominant horizontal direction of this pair (legacy: compare the mean
        # rightward and leftward magnitudes)
        right = fx[fx > 0]
        left = -fx[fx < 0]
        mean_right = float(right.mean()) if right.size else 0.0
        mean_left = float(left.mean()) if left.size else 0.0
        if mean_left > mean_right:
            left_votes += 1
            main = -fx  # analyse the leftward motion as positive values
            mean_main = mean_left
        else:
            right_votes += 1
            main = fx
            mean_main = mean_right
        if mean_main <= 0:
            continue

        # legacy filter: grid vectors close to the mean horizontal flow with
        # little vertical motion = the water surface; vertical ones = rain
        grid_x = main[::STEP, ::STEP]
        grid_y = fy[::STEP, ::STEP]
        band = mean_main / 20.0
        horizontal = (np.abs(grid_x - mean_main) <= band) & (
            np.abs(grid_y) < VERTICAL_LIMIT
        )
        mean_fy = float(fy.mean())
        vertical = (
            (np.abs(grid_y - mean_fy) <= abs(mean_fy) / 20.0 + 1e-6)
            & (np.abs(grid_x) < VERTICAL_LIMIT)
            & (np.abs(grid_y) >= VERTICAL_LIMIT)
        )
        rain_points += int(vertical.sum())
        if horizontal.any():
            displacement = float(grid_x[horizontal].mean())  # px per frame gap
            velocities.append(displacement * scale / dt)

    if not velocities:
        velocity = 0.0
    else:
        velocity = float(np.mean(velocities))
    return {
        "velocity": round(velocity, 3),
        "direction": "left" if left_votes > right_votes else "right",
        "color": color_hex,
        "color_rgb": list(color_rgb),
        "color_name": color_name,
        "rain": rain_points > RAIN_POINTS,
        "rain_points": rain_points,
        "pairs": len(velocities),
        "region": [x1, y1, x2, y2],
        "scale": round(scale, 6),
    }
