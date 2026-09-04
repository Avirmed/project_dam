"""Demo data simulator (development / demo installations only).

When the SIMULATOR_ENABLED setting is on, every 15-minute slot each active
station receives one realistic payload, written straight into tbl_station_data
(no HttpLog queue, no FTP): a diurnal water-level curve on top of the station's
own thresholds (Point 1 / Point 2), afternoon rain showers, velocity tied to the
level, FLOW from the mapped Flow sensor when configured (StationData.apply_flow),
plus POWER / VOLT / TEMP / HUM. A few stations are pinned to Warning / Critical
and a few stay silent so the map and the dashboard show every status.

backfill(days) writes the same curve for the past `days` (slots that already
hold a row are skipped) - used once to seed a demo database.
"""

import hashlib
import logging
import math
import random
from datetime import datetime, timedelta

from database import db
from models import Settings, Station, StationData
from util import statictext, util as Util

logger = logging.getLogger("worker")

SLOT_MINUTES = 15
# StationID -> scenario; everything else is "normal"
SCENARIOS = {
    3: "warning",
    7: "warning",
    12: "warning",
    5: "critical",
    17: "critical",
    9: "silent",
    21: "silent",
}


def enabled():
    value = str(Settings.load_settings().get("SIMULATOR_ENABLED", "0")).strip().lower()
    return value not in ("0", "false", "off", "no", "")


def _seed(station, suffix=""):
    return int(
        hashlib.md5(f"{station.StationID}:{suffix}".encode()).hexdigest()[:8], 16
    )


def _cfg(station):
    return ((station.Meta or {}).get("StationConfigures") or {}).get("configs") or {}


def _band(cfg, point):
    """(zero, warning, critical) of a point ("UP" / "DOWN"), None when unset."""
    zero = Util.safe_float(cfg.get(f"ZEROGATE_{point}"))
    warn = Util.safe_float(cfg.get(f"WARNING_{point}"))
    crit = Util.safe_float(cfg.get(f"CRITICAL_{point}"))
    if zero is None or warn is None or crit is None or warn <= zero or crit <= warn:
        return None
    return zero, warn, crit


def level_at(station, when, point="UP"):
    """Water level of one point at `when`: scenario band + weekly trend +
    diurnal sine + small noise. Deterministic per station and time."""
    band = _band(_cfg(station), point)
    if band is None:
        return None
    zero, warn, crit = band
    scenario = SCENARIOS.get(station.StationID, "normal")
    rng = random.Random(_seed(station, point))
    phase = rng.random() * 2 * math.pi
    span = warn - zero
    if scenario == "critical":
        base, amp = crit + (crit - warn) * 0.25, (crit - warn) * 0.15
    elif scenario == "warning":
        base, amp = warn + (crit - warn) * 0.35, (crit - warn) * 0.2
    else:
        base, amp = zero + span * (0.35 + 0.3 * rng.random()), span * 0.06
    hours = when.hour + when.minute / 60.0
    diurnal = math.sin((hours / 24.0) * 2 * math.pi + phase)
    weekly = (
        math.sin((when.timetuple().tm_yday / 7.0) * 2 * math.pi + phase) * amp * 0.5
    )
    noise = (
        random.Random(_seed(station, when.strftime("%Y%m%d%H%M"))).uniform(-1, 1)
        * amp
        * 0.15
    )
    return round(base + amp * diurnal + weekly + noise, 2)


def rain_at(station, when):
    """Rain in the 15-minute slot [mm]: showers mostly 14:00-19:00, some at night."""
    rng = random.Random(_seed(station, "rain" + when.strftime("%Y%m%d%H")))
    hour = when.hour
    chance = 0.35 if 14 <= hour <= 19 else (0.12 if hour >= 22 or hour <= 3 else 0.04)
    if rng.random() > chance:
        return 0.0
    burst = random.Random(
        _seed(station, "burst" + when.strftime("%Y%m%d%H%M"))
    ).uniform(0.2, 9.5)
    return round(burst, 2)


def payload_for(station, when):
    """Mapped Data dict (device-like strings) for one station and slot, or None
    for silent stations."""
    if SCENARIOS.get(station.StationID) == "silent":
        return None
    wl = level_at(station, when, "UP")
    if wl is None:
        return None
    keys = statictext.StationDataKeys
    rng = random.Random(_seed(station, "misc" + when.strftime("%Y%m%d%H%M")))
    band = _band(_cfg(station), "UP")
    depth = max(
        0.05,
        wl
        - (Util.safe_float(_cfg(station).get("GROUND_LEVEL_WL_UP")) or (band[0] - 3)),
    )
    velocity = round(0.35 + 0.22 * depth + rng.uniform(-0.08, 0.08), 2)
    data = {
        keys["WaterLevel"]: f"{wl:.2f}",
        keys["Rainfall"]: f"{rain_at(station, when):.2f}",
        keys["Velocity"]: f"{max(velocity, 0.05):.2f}",
        "POWER": f"{rng.uniform(12.2, 13.9):.2f}",
        "VOLT": f"{rng.uniform(12.6, 14.1):.2f}",
        "TEMP": f"{26 + 6 * math.sin(((when.hour - 6) / 24.0) * 2 * math.pi) + rng.uniform(-0.6, 0.6):.2f}",
        "HUM": f"{68 + 12 * math.cos((when.hour / 24.0) * 2 * math.pi) + rng.uniform(-2, 2):.2f}",
        "DateTime": when.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    wl2 = level_at(station, when, "DOWN")
    if wl2 is not None:
        data[keys["WaterLevel2"]] = f"{wl2:.2f}"
    # FLOW from the mapped Flow sensor (design slide 9) or a plausible synthetic value
    if not StationData.apply_flow(station, data):
        # synthetic wetted area (trapezoid-like growth with depth) and the matching
        # discharge Q = A * v, so every parameter chart has demo data
        area = max(0.0, depth * 3.2 + rng.uniform(-0.15, 0.15))
        data[keys["Area"]] = f"{area:.4f}"
        data[keys["Flow"]] = f"{max(0.0, area * max(velocity, 0.05) + rng.uniform(-0.4, 0.4)):.2f}"
    return data


def slot(when):
    return when.replace(
        minute=(when.minute // SLOT_MINUTES) * SLOT_MINUTES, second=0, microsecond=0
    )


def write_slot(station, when, existing=None):
    """Insert the payload of `when` unless that (station, time) row exists."""
    if existing is not None and when in existing:
        return False
    if (
        existing is None
        and StationData.query.filter(
            StationData.StationID == station.StationID, StationData.RecordTime == when
        ).first()
    ):
        return False
    data = payload_for(station, when)
    if data is None:
        return False
    db.session.add(
        StationData(
            StationID=station.StationID,
            DeviceID=station.DeviceID,
            RecordTime=when,
            Data=data,
            Raw={"simulated": True, **data},
            CreateDate=datetime.now(),
        )
    )
    return True


def backfill(days=7, until=None):
    """Seed the past `days` for every active station; returns rows written."""
    until = slot(until or datetime.now())
    start = until - timedelta(days=days)
    written = 0
    for station in Station.query.filter(Station.Status == 1).all():
        existing = {
            t
            for (t,) in db.session.query(StationData.RecordTime)
            .filter(
                StationData.StationID == station.StationID,
                StationData.RecordTime >= start,
            )
            .all()
        }
        when = start
        while when <= until:
            if write_slot(station, when, existing):
                written += 1
            when += timedelta(minutes=SLOT_MINUTES)
        db.session.commit()
    return written


_last_slot = None


def run():
    """Worker job: one payload per active station per 15-minute slot."""
    global _last_slot
    if not enabled():
        return None
    now = slot(datetime.now())
    if _last_slot == now:
        return None
    _last_slot = now
    written = 0
    for station in Station.query.filter(Station.Status == 1).all():
        if write_slot(station, now):
            written += 1
    db.session.commit()
    return {"payloads": written}
