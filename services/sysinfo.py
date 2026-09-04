"""System information for the dashboard overview - stdlib only (psutil is not
part of the bundled interpreter and python313/ must not be modified).

  CPU      - Windows GetSystemTimes / Linux /proc/stat, sampled by the worker
             every few seconds (sample()); the first request samples inline.
  Memory   - Windows GlobalMemoryStatusEx / Linux /proc/meminfo, plus the app
             process working set.
  Disk     - shutil.disk_usage of the application drive.
  Folders  - sizes of the runtime folders (data/, static/data/, certs/, logs/),
             walked by the worker and cached for FOLDER_CACHE_SECONDS.
  Database - PostgreSQL size, connections, largest tables (pg_stat_user_tables).
"""

import ctypes
import os
import platform
import shutil
import sys
import time

from database import db
from sqlalchemy import text
from util import statictext

FOLDER_CACHE_SECONDS = 300
_cpu = {"prev": None, "percent": None}
_folders = {"at": 0.0, "items": None}


# ------------------------------------------------------------------ CPU
def _cpu_times():
    """(idle, total) in arbitrary units, or None when unsupported."""
    if os.name == "nt":

        class FILETIME(ctypes.Structure):
            _fields_ = [("low", ctypes.c_uint32), ("high", ctypes.c_uint32)]

        idle, kernel, user = FILETIME(), FILETIME(), FILETIME()
        if not ctypes.windll.kernel32.GetSystemTimes(
            ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)
        ):
            return None
        as_int = lambda t: (t.high << 32) | t.low  # noqa: E731
        # kernel time includes idle time
        return as_int(idle), as_int(kernel) + as_int(user)
    try:
        with open("/proc/stat") as f:
            fields = [int(x) for x in f.readline().split()[1:]]
        idle = fields[3] + (fields[4] if len(fields) > 4 else 0)
        return idle, sum(fields)
    except (OSError, ValueError, IndexError):
        return None


def sample():
    """Worker job: refresh the CPU percentage and, when stale, folder sizes."""
    now = _cpu_times()
    if now is not None and _cpu["prev"] is not None:
        d_idle = now[0] - _cpu["prev"][0]
        d_total = now[1] - _cpu["prev"][1]
        if d_total > 0:
            _cpu["percent"] = round(
                max(0.0, min(100.0, 100.0 * (1 - d_idle / d_total))), 1
            )
    _cpu["prev"] = now
    if time.time() - _folders["at"] >= FOLDER_CACHE_SECONDS:
        _folders["items"] = _folder_sizes()
        _folders["at"] = time.time()
    return None


def cpu_percent():
    if _cpu["percent"] is None:  # first call: short inline sample
        sample()
        time.sleep(0.25)
        sample()
    return _cpu["percent"]


# --------------------------------------------------------------- memory
def memory():
    total = available = rss = None
    if os.name == "nt":

        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            total, available = stat.ullTotalPhys, stat.ullAvailPhys

        class PMC(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.c_ulong),
                ("PageFaultCount", ctypes.c_ulong),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        pmc = PMC()
        pmc.cb = ctypes.sizeof(PMC)
        try:
            kernel32, psapi = ctypes.windll.kernel32, ctypes.windll.psapi
            # Declare the signatures: without them the pseudo-handle (-1) is
            # truncated to a 32-bit int and the call fails silently on x64.
            kernel32.GetCurrentProcess.restype = ctypes.c_void_p
            psapi.GetProcessMemoryInfo.argtypes = [
                ctypes.c_void_p,
                ctypes.POINTER(PMC),
                ctypes.c_ulong,
            ]
            if psapi.GetProcessMemoryInfo(
                kernel32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb
            ):
                rss = pmc.WorkingSetSize
        except (AttributeError, OSError):
            pass
    else:
        try:
            info = {}
            with open("/proc/meminfo") as f:
                for line in f:
                    key, _, rest = line.partition(":")
                    info[key] = int(rest.split()[0]) * 1024
            total, available = info.get("MemTotal"), info.get("MemAvailable")
            with open("/proc/self/status") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        rss = int(line.split()[1]) * 1024
        except (OSError, ValueError):
            pass
    used = (total - available) if total and available is not None else None
    return {
        "total": total,
        "available": available,
        "used": used,
        "percent": (
            round(100.0 * used / total, 1) if used is not None and total else None
        ),
        "process": rss,
    }


# ----------------------------------------------------------------- disk
def disk():
    usage = shutil.disk_usage(statictext.APP_DIRECTORY)
    drive = os.path.splitdrive(statictext.APP_DIRECTORY)[0] or "/"
    return {
        "path": drive,
        "total": usage.total,
        "used": usage.used,
        "free": usage.free,
        "percent": round(100.0 * usage.used / usage.total, 1) if usage.total else None,
    }


# -------------------------------------------------------------- folders
def _folder_size(path):
    total = files = 0
    for folder, _dirs, names in os.walk(path):
        for name in names:
            try:
                total += os.path.getsize(os.path.join(folder, name))
                files += 1
            except OSError:
                pass
    return total, files


def _folder_sizes():
    base = statictext.APP_DIRECTORY
    targets = [
        ("data/csv", os.path.join(statictext.APP_DATA_PATH, "csv")),
        ("data/security_in", os.path.join(statictext.APP_DATA_PATH, "security_in")),
        ("data/images_out", os.path.join(statictext.APP_DATA_PATH, "images_out")),
        (
            "static/data/events",
            os.path.join(statictext.APP_STATIC_PATH, "data", "events"),
        ),
        (
            "static/data/cameras",
            os.path.join(statictext.APP_STATIC_PATH, "data", "cameras"),
        ),
        (
            "static/data/uploads",
            os.path.join(statictext.APP_STATIC_PATH, "data", "uploads"),
        ),
        ("certs", statictext.APP_CERT_PATH),
        ("logs", os.path.join(base, "logs")),
        ("tmp", statictext.APP_TMP_PATH),
    ]
    items = []
    for label, path in targets:
        if not os.path.isdir(path):
            items.append({"name": label, "size": 0, "files": 0, "exists": False})
            continue
        size, files = _folder_size(path)
        items.append({"name": label, "size": size, "files": files, "exists": True})
    return items


def folders():
    if _folders["items"] is None:
        _folders["items"] = _folder_sizes()
        _folders["at"] = time.time()
    return _folders["items"]


# ------------------------------------------------------------- database
def database():
    info = {"size": None, "connections": None, "version": None, "tables": []}
    try:
        info["size"] = db.session.execute(
            text("SELECT pg_database_size(current_database())")
        ).scalar()
        info["connections"] = db.session.execute(
            text(
                "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()"
            )
        ).scalar()
        version = db.session.execute(text("SELECT version()")).scalar() or ""
        info["version"] = " ".join(version.split()[:2])
        rows = db.session.execute(text("""
                SELECT relname, n_live_tup, pg_total_relation_size(relid)
                FROM pg_stat_user_tables
                ORDER BY pg_total_relation_size(relid) DESC
                LIMIT 8
                """)).all()
        info["tables"] = [
            {"name": r[0], "rows": int(r[1] or 0), "size": int(r[2] or 0)} for r in rows
        ]
    except Exception as e:  # never break the dashboard because of a DB detail
        info["error"] = f"{type(e).__name__}: {e}"[:200]
        db.session.rollback()
    return info


# ------------------------------------------------------------- snapshot
def snapshot(started_at):
    from datetime import datetime

    return {
        "uptime": int((datetime.now() - started_at).total_seconds()),
        "started_at": started_at,
        "cpu": cpu_percent(),
        "cpu_count": os.cpu_count(),
        "memory": memory(),
        "disk": disk(),
        "folders": folders(),
        "database": database(),
        "python": platform.python_version(),
        "platform": f"{platform.system()} {platform.release()}",
        "host": platform.node(),
        "pid": os.getpid(),
        "debug": bool(sys.flags.debug)
        or os.getenv("APP_DEBUG", "").lower() in ("true", "1", "t", "yes"),
    }
