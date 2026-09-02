"""Deliver queued HttpLog rows to their HTTP service (design slides 3 / 17 / 18).

For every Queue row whose NextAttempt is due: build the request from the row
(URL / method / body already rendered at enqueue time) plus the service's
current settings (timeout, authentication, Verify SSL), send it with the
standard library, and record the response code / body. 2xx -> Sent; anything
else -> retry after RetryDelay until RetryAttempts are used up -> Failed.
"""

import base64
import logging
import ssl
import urllib.error
import urllib.request
from datetime import datetime

from models import HttpLog
from util import util as Util

logger = logging.getLogger("worker")

BATCH_SIZE = 25
RESPONSE_LIMIT = 4000  # characters of response body kept in the log
USER_AGENT = "DAM-Worker/1.0"


def _auth_headers(cfg):
    auth = (cfg.get("Authentication") or "none").lower()
    if auth == "basic":
        token = base64.b64encode(
            f"{cfg.get('Auth_Username') or ''}:{cfg.get('Auth_Password') or ''}".encode(
                "utf-8"
            )
        ).decode("ascii")
        return {"Authorization": f"Basic {token}"}
    if auth == "bearer":
        return {"Authorization": f"Bearer {cfg.get('Token') or ''}"}
    if auth == "key":
        name = str(cfg.get("API_Key_Header") or "X-API-Key").strip() or "X-API-Key"
        return {name: str(cfg.get("Token") or "")}
    return {}


def _ssl_context(cfg):
    verify = cfg.get("VerifySSL")
    if verify in (False, 0, "0", "false", "False", "", None):
        return ssl._create_unverified_context()
    return ssl.create_default_context()


def deliver(row):
    """Send one queued row and update it in place."""
    service = row.http
    cfg = {}
    if service is not None:
        request_cfg = (service.Meta or {}).get("Request") or {}
        cfg = request_cfg.get("configs") or {} if isinstance(request_cfg, dict) else {}

    method = (row.Method or cfg.get("Method") or "post").upper()
    timeout = Util.safe_int(cfg.get("Timeout"), 10) or 10
    body = row.Request if method in ("POST", "PUT") and row.Request else None
    content_type = (
        "application/json"
        if (cfg.get("ContentType") or "json") == "json"
        else "text/plain"
    )

    headers = {"User-Agent": USER_AGENT}
    headers.update(_auth_headers(cfg))
    if body is not None:
        headers["Content-Type"] = f"{content_type}; charset=utf-8"

    if not row.URL:
        row.mark_attempt_failed(None, "Missing URL", cfg)
        return

    try:
        request = urllib.request.Request(
            row.URL,
            data=body.encode("utf-8") if body is not None else None,
            method=method,
            headers=headers,
        )
        with urllib.request.urlopen(
            request, timeout=timeout, context=_ssl_context(cfg)
        ) as response:
            code = response.status
            text = response.read(RESPONSE_LIMIT).decode("utf-8", "replace")
        row.mark_sent(code, text)
        logger.info("HttpLog %s sent -> %s %s", row.ID, code, row.URL)
    except urllib.error.HTTPError as e:
        try:
            text = e.read(RESPONSE_LIMIT).decode("utf-8", "replace")
        except Exception:
            text = str(e)
        row.mark_attempt_failed(e.code, text, cfg)
        logger.warning(
            "HttpLog %s HTTP %s (attempt %s) %s", row.ID, e.code, row.Attempts, row.URL
        )
    except Exception as e:
        row.mark_attempt_failed(None, f"{type(e).__name__}: {e}", cfg)
        logger.warning("HttpLog %s error (attempt %s): %s", row.ID, row.Attempts, e)


def send_pending():
    """Worker job: deliver due Queue rows, oldest first."""
    now = datetime.now()
    rows = (
        HttpLog.query.filter(
            HttpLog.Status == HttpLog.STATUS_QUEUE,
            (HttpLog.NextAttempt.is_(None)) | (HttpLog.NextAttempt <= now),
        )
        .order_by(HttpLog.ID.asc())
        .limit(BATCH_SIZE)
        .all()
    )
    for row in rows:
        deliver(row)
    return len(rows)
