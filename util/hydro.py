"""Hydraulic helpers for the Flow sensor (design rev.22 slide 9).

The surveyed cross-section is a polygon of (x, y) points entered in order
(CustomProfile). From it the wetted area for any water level is computed, which
feeds the Profile table (level -> area [m2]); level-dependent tables (Profile,
FlowCalcTable) are read back with linear interpolation.

    Q [m3/s] = A(h) * k(h) * v_surface
"""


def _num(value):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def parse_points(rows, ref="Level"):
    """[{x, y}, ...] -> [(x, y_up), ...]. With the "Depth" reference the y values
    grow downwards, so they are flipped to keep "up" positive internally."""
    points = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        x, y = _num(row.get("x")), _num(row.get("y"))
        if x is None or y is None:
            continue
        points.append((x, -y if ref == "Depth" else y))
    return points


def polygon_area(points):
    """Shoelace formula (absolute value) for a closed polygon."""
    n = len(points)
    if n < 3:
        return 0.0
    total = 0.0
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        total += x1 * y2 - x2 * y1
    return abs(total) / 2.0


def _crossing(a, b, level):
    t = (level - a[1]) / (b[1] - a[1])
    return (a[0] + (b[0] - a[0]) * t, level)


def clip_below(points, level):
    """Part of the closed polygon lying at or below `level`
    (Sutherland-Hodgman against the half-plane y <= level)."""
    result = []
    n = len(points)
    for i in range(n):
        current, previous = points[i], points[i - 1]
        cur_in, prev_in = current[1] <= level, previous[1] <= level
        if cur_in:
            if not prev_in:
                result.append(_crossing(previous, current, level))
            result.append(current)
        elif prev_in:
            result.append(_crossing(previous, current, level))
    return result


def wetted_area(points, level):
    """Area [m2] of the cross-section polygon under a horizontal water line."""
    if len(points) < 3:
        return 0.0
    return polygon_area(clip_below(points, level))


def wetted_width(points, level, delta=1e-4):
    """Width of the water surface at `level` = dA/dh (central difference)."""
    return (wetted_area(points, level + delta) - wetted_area(points, level - delta)) / (
        2 * delta
    )


def profile_levels(points, step=0.01, max_rows=200):
    """Levels for the Profile table, as in the design example (slide 9):
    every surveyed y is a breakpoint; between two breakpoints extra rows every
    `step` are added only where the section widens or narrows (the area curve
    is non-linear there); where the walls are vertical the area is linear and
    the two breakpoints are enough."""
    breaks = sorted(set(round(p[1], 6) for p in points))
    if len(breaks) < 2:
        return breaks
    while True:
        levels = []
        for a, b in zip(breaks, breaks[1:]):
            levels.append(a)
            inner = min(step / 4, (b - a) / 4)
            if inner <= 0:
                continue
            sloped = (
                abs(wetted_width(points, a + inner) - wetted_width(points, b - inner))
                > 1e-6
            )
            if sloped:
                k = 1
                while a + k * step < b - step / 2:
                    levels.append(round(a + k * step, 6))
                    k += 1
        levels.append(breaks[-1])
        if len(levels) <= max_rows or step >= 1:
            return levels
        step *= 2


def build_profile(rows, ref="Level", step=0.01, decimals=4):
    """Profile table rows [{"WaterLevel", "Area"}] from the surveyed polygon:
    breakpoints at every surveyed y plus `step` rows inside sloped zones
    (see profile_levels), so the table stays compact while linear
    interpolation between rows reproduces the exact wetted area."""
    points = parse_points(rows, ref)
    if len(points) < 3:
        return []
    profile = []
    for h in profile_levels(points, step):
        # "Depth" levels are distances below the reference (downward-looking
        # sensor): depth 0 = water at the reference, a larger depth = lower water.
        level = -h if ref == "Depth" else h
        level = 0.0 if abs(level) < 1e-9 else level
        profile.append(
            {
                "WaterLevel": f"{level:.3f}",
                "Area": f"{wetted_area(points, h):.{decimals}f}",
            }
        )
    profile.sort(key=lambda r: float(r["WaterLevel"]))
    return profile


def compute_flow(profile_rows, cal_rows, level, velocity):
    """Q = A(h) * k(h) * v.

    profile_rows : Profile table [{WaterLevel, Area}]  -> wetted area A(h)
    cal_rows     : FLOW CAL. TABLE [{WaterLevel, Coefficient}] -> k(h), 1.0 when empty
    level        : water level h in the profile's reference
    velocity     : measured surface velocity v [m/s]
    Returns (flow, area, k) or None when a value is missing / not numeric.
    """
    h, v = _num(level), _num(velocity)
    if h is None or v is None:
        return None
    area = interpolate(profile_rows, h)
    if area is None:
        return None
    k = interpolate(cal_rows, h, "WaterLevel", "Coefficient")
    if k is None:
        k = 1.0
    return (area * k * v, area, k)


def interpolate(rows, level, x_key="WaterLevel", y_key="Area"):
    """Linear interpolation in a two-column table (clamped at both ends);
    None when the table is empty."""
    table = sorted(
        (
            (_num(r.get(x_key)), _num(r.get(y_key)))
            for r in rows or []
            if isinstance(r, dict)
        ),
        key=lambda p: (p[0] is None, p[0]),
    )
    table = [(x, y) for x, y in table if x is not None and y is not None]
    if not table:
        return None
    if level <= table[0][0]:
        return table[0][1]
    if level >= table[-1][0]:
        return table[-1][1]
    for (x1, y1), (x2, y2) in zip(table, table[1:]):
        if x1 <= level <= x2:
            if x2 == x1:
                return y2
            return y1 + (y2 - y1) * (level - x1) / (x2 - x1)
    return table[-1][1]
