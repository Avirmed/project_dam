"""Pixel row -> water level conversion.

A Sampling record stores the surveyed calibration table as rows of
{"x": <pixel y on the camera frame>, "y": <water level, m>} (statictext
SamplingConfigures). This is the same data the legacy server kept in
`<station>_sampling_N.txt` and turned into a level with a cubic spline; the
spline is extrapolated past both ends exactly like the legacy `cubic_spline()`.

Pure numpy/scipy - safe to import from the web process.
"""

import numpy as np
from scipy.interpolate import CubicSpline


def _num(value):
    try:
        text = str(value).strip()
        return float(text) if text else None
    except (TypeError, ValueError):
        return None


def parse_rows(rows):
    """Normalise calibration rows into a list of (pixel_y, level) floats.

    Accepts Sampling rows ({"x": .., "y": ..}), 2-item sequences or strings
    "pixel,level"; blank / non-numeric rows are skipped, duplicated pixels keep
    the last value, and the result is sorted by pixel (ascending), which is the
    order CubicSpline requires.
    """
    points = {}
    for row in rows or []:
        if isinstance(row, dict):
            pixel, level = _num(row.get("x")), _num(row.get("y"))
        elif isinstance(row, str):
            parts = row.split(",")
            pixel, level = (
                (_num(parts[0]), _num(parts[1])) if len(parts) >= 2 else (None, None)
            )
        else:
            try:
                pixel, level = _num(row[0]), _num(row[1])
            except (TypeError, IndexError):
                pixel, level = None, None
        if pixel is None or level is None:
            continue
        points[pixel] = level
    return sorted(points.items())


def load_sampling_file(path):
    """Read a legacy `<station>_sampling_N.txt` (lines "pixel,level")."""
    with open(path, encoding="utf-8") as fp:
        return parse_rows([line for line in fp if line.strip()])


def pixel_to_level(rows, pixel_y):
    """Water level (m) for a pixel row, or None when the table cannot be used.

    Returns (level, in_range): `in_range` is False when `pixel_y` lies outside
    the surveyed pixel span and the value is an extrapolation (the legacy code
    flagged this for multi-gauge stations; callers may reject such readings).
    """
    points = parse_rows(rows)
    if pixel_y is None or len(points) < 2:
        return None, False

    xs = np.array([p for p, _ in points], dtype=float)
    ys = np.array([lvl for _, lvl in points], dtype=float)
    y = float(pixel_y)
    in_range = bool(xs[0] <= y <= xs[-1])

    if len(points) == 2:  # not enough knots for a cubic: straight line
        level = (
            float(np.interp(y, xs, ys))
            if in_range
            else float(ys[0] + (ys[1] - ys[0]) * (y - xs[0]) / (xs[1] - xs[0]))
        )
        return level, in_range

    # Same as the legacy cubic_spline(): default (not-a-knot) spline evaluated
    # with the end pieces beyond the surveyed span.
    spline = CubicSpline(xs, ys, extrapolate=True)
    return float(spline(y)), in_range
