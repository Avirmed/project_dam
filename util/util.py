import os
import re
import math
import hmac
import hashlib
import ipaddress
from PIL import Image, ImageOps
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64
from bs4 import BeautifulSoup
import json

APP_MENU = {
    "main_menu": {
        "submenu": [
            {"name": "Home", "url": "/", "icon": "<i class='ti ti-smart-home'></i>"},
            {
                "name": "CCTV",
                "url": "/cctv",
                "icon": "<i class='bi bi-camera-video'></i>",
            },
            {
                "name": "Statistics",
                "url": "/statistics",
                "icon": "<i class='bi bi-image'></i>",
            },
            {
                "name": "Report",
                "url": "/report",
                "icon": "<i class='bi bi-file-earmark-check'></i>",
            },
            {
                "name": "Event Log",
                "url": "/events",
                "icon": "<i class='bi bi-file-earmark-text'></i>",
            },
        ],
    }
}


APP_DASHBOARD_MENU = {
    "main_menu": {
        "submenu": [
            {
                "name": "Dashboard",
                "url": "/dashboard",
                "icon": "<i class='ti ti-smart-home'></i>",
            },
            {
                "name": "Projects",
                "url": "/dashboard/projects",
                "icon": "<i class='bi bi-window-stack'></i>",
            },
            {
                "name": "River Basin",
                "url": "/dashboard/riverbasins",
                "icon": "<i class='bi bi-water'></i>",
            },
            {
                "name": "Stations",
                "url": "/dashboard/stations",
                "icon": "<i class='bi bi-router'></i>",
            },
            {
                "name": "Sensor",
                "url": "/dashboard/sensor",
                "icon": "<i class='bi bi-motherboard'></i>",
                "submenu": [
                    {
                        "name": "Sensors",
                        "url": "/dashboard/sensors",
                    },
                    {
                        "name": "Cameras",
                        "url": "/dashboard/cameras",
                    },
                    {
                        "name": "Sampling",
                        "url": "/dashboard/samplings",
                    },
                    {
                        "name": "Area",
                        "url": "/dashboard/areas",
                    },
                ],
            },
            {
                "name": "Services",
                "url": "/dashboard/services",
                "icon": "<i class='bi bi-hdd-network'></i>",
                "submenu": [
                    {
                        "name": "File Transfer",
                        "url": "/dashboard/filetransfer",
                    },
                    {
                        "name": "HTTP",
                        "url": "/dashboard/http",
                    },
                    {
                        "name": "HTTP Logs",
                        "url": "/dashboard/httplog",
                    },
                    {
                        "name": "CSV Logger",
                        "url": "/dashboard/csvlogger",
                    },
                ],
            },
        ],
    },
    "settings": {
        "name": "Settings",
        "submenu": [
            {
                "name": "Teams",
                "url": "/dashboard/teams",
                "icon": "<i class='bi bi-microsoft-teams'></i>",
            },
            {
                "name": "Users",
                "url": "/dashboard/users",
                "icon": "<i class='bi bi-person-gear'></i>",
            },
            {
                "name": "Settings",
                "url": "/dashboard/settings",
                "icon": "<i class='bi bi-gear-fill'></i>",
            },
        ],
    },
}


fileExtIconList = {}
fileExtIconDir = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "static",
    "css/bootstrap-icons/docs/content/icons",
)
pattern = r"^filetype-(.*?)\.md$"

for file in os.listdir(fileExtIconDir):
    match = re.match(pattern, file)
    if match:
        ext = match.group(1).lower()
        fileExtIconList[ext] = f"<i class='bi bi-filetype-{ext}'></i>"


def getFileTypeIcon(filename, filepath):
    icon = '<i class="bi bi-file-earmark-text"></i>'

    if filename is None or not filename or filepath is None or not filepath:
        return icon

    name, ext = os.path.splitext(filename)
    ext = ext.lower().lstrip(".")
    filepath = filepath.replace("\\", "/")
    extraAttr = ""

    if ext in fileExtIconList:
        icon = fileExtIconList[ext]

    if ext in ["jpg", "jpeg", "png", "gif"]:
        extraAttr = f'data-href="{filepath}" data-gallery="#attachFileGallery"'

    return f'<span class="fileType" data-type="{ext}" data-url="{filepath}" title="{filename}" {extraAttr}>{icon}</span>'


# --- Secure chunked-upload helpers (used by the /fileupload routes) ---
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif"}

# Extensions that could be executed or served as code on the server. These are
# rejected for every upload, even when no whitelist is enforced.
DANGEROUS_UPLOAD_EXTENSIONS = {
    "php",
    "phtml",
    "php3",
    "php4",
    "php5",
    "php7",
    "phps",
    "pht",
    "asp",
    "aspx",
    "jsp",
    "jspx",
    "cgi",
    "pl",
    "py",
    "pyc",
    "pyo",
    "rb",
    "sh",
    "bash",
    "zsh",
    "bat",
    "cmd",
    "com",
    "exe",
    "dll",
    "msi",
    "scr",
    "vbs",
    "vbe",
    "js",
    "mjs",
    "jse",
    "ws",
    "wsf",
    "jar",
    "war",
    "class",
    "so",
    "bin",
    "htaccess",
    "htpasswd",
    "ini",
    "conf",
    "config",
    "svg",
    "svgz",
    "html",
    "htm",
    "xhtml",
    "shtml",
    "xml",
    "swf",
}


def get_safe_extension(filename, allowed=ALLOWED_IMAGE_EXTENSIONS):
    """Return the lowercased extension if the file is safe to store, else None.

    A file with no extension or a server-dangerous extension (scripts,
    executables, or files that could be served back as code) is always
    rejected. When `allowed` is given (defaults to images) the extension must
    also be in that whitelist; pass allowed=None to accept any non-dangerous
    file (e.g. for general multi-file uploads).
    """
    ext = os.path.splitext(filename or "")[1].lower().lstrip(".")
    if not ext or ext in DANGEROUS_UPLOAD_EXTENSIONS:
        return None
    if allowed is not None and ext not in allowed:
        return None
    return ext


def build_upload_filename(upload_time, filename, ext):
    """Build a collision-resistant, traversal-safe upload filename.

    The client-supplied `upload_time` is stripped to [A-Za-z0-9_], so it can
    never contain path separators or "..", and `ext` must already be validated
    with get_safe_extension. Result: "<time>_<md5(filename+time)>.<ext>".
    """
    safe_time = re.sub(r"[^A-Za-z0-9_]", "", upload_time or "")
    digest = hashlib.md5(((filename or "") + (upload_time or "")).encode()).hexdigest()
    return f"{safe_time}_{digest}.{ext}"


# --- Station REST API server (inbound) helpers ---
# Certificate / private-key uploads for the per-station TLS settings.
ALLOWED_CERT_EXTENSIONS = {"crt", "pem", "key"}


def parse_source_list(raw):
    """Parse a comma/semicolon separated list of IPs or CIDR ranges into
    ip_network objects. Raises ValueError on any malformed entry."""
    nets = []
    for part in str(raw or "").replace(";", ",").split(","):
        part = part.strip()
        if part:
            nets.append(ipaddress.ip_network(part, strict=False))
    return nets


def is_source_allowed(remote_addr, mode, custom_list=None):
    """Check a client address against an API source rule.

    mode: "" / None (no restriction), "ipv4" (any IPv4), "ipv6" (any IPv6) or
    "custom" (must fall inside one of the networks in `custom_list`).
    """
    try:
        addr = ipaddress.ip_address(str(remote_addr or "").split("%")[0])
    except ValueError:
        return False

    # IPv4 clients behind a dual-stack proxy show up as ::ffff:a.b.c.d
    if addr.version == 6 and addr.ipv4_mapped is not None:
        addr = addr.ipv4_mapped

    if not mode:
        return True
    if mode == "ipv4":
        return addr.version == 4
    if mode == "ipv6":
        return addr.version == 6
    if mode == "custom":
        try:
            nets = parse_source_list(custom_list)
        except ValueError:
            return False
        return any(addr in net for net in nets)
    return False


def _port_ok(value):
    if value in (None, ""):
        return True
    try:
        port = int(str(value).strip())
    except (TypeError, ValueError):
        return False
    return 0 <= port <= 65535


def _sources_ok(raw):
    try:
        return len(parse_source_list(raw)) > 0
    except ValueError:
        return False


def validate_api_config(api):
    """Validate Station.Meta["API"] = {"status": bool, "configs": {...}}.

    Returns None when the settings are coherent, otherwise the
    statictext.Messages key describing the first problem. Only the settings that
    apply to the chosen protocol / SSL mode / authentication are checked, and a
    disabled server (status false) is never rejected so drafts can be saved.
    """
    if not isinstance(api, dict) or not api.get("status"):
        return None

    cfg = api.get("configs") or {}
    if not isinstance(cfg, dict):
        return "ApiConfigInvalid"

    protocol = cfg.get("Protocol") or "http"

    if protocol in ("http", "both"):
        if not _port_ok(cfg.get("Port")):
            return "ApiPortInvalid"
        if cfg.get("HTTP_Source") == "custom" and not _sources_ok(
            cfg.get("HTTP_Source_Custom")
        ):
            return "ApiSourceInvalid"

    if protocol in ("https", "both"):
        if not _port_ok(cfg.get("HTTPS_Port")):
            return "ApiPortInvalid"
        if cfg.get("HTTPS_Source") == "custom" and not _sources_ok(
            cfg.get("HTTPS_Source_Custom")
        ):
            return "ApiSourceInvalid"

        ssl_mode = cfg.get("SSL_Mode") or "off"
        if ssl_mode in ("one_way", "two_way") and not (
            cfg.get("SSL_Cert") and cfg.get("SSL_Key")
        ):
            return "ApiCertRequired"
        if ssl_mode == "two_way" and not cfg.get("SSL_CA_Cert"):
            return "ApiCaRequired"

    auth = cfg.get("Authentication") or "none"
    if auth in ("bearer", "key") and not str(cfg.get("Token") or "").strip():
        return "ApiTokenRequired"
    if auth == "basic" and not (
        str(cfg.get("Auth_Username") or "").strip()
        and str(cfg.get("Auth_Password") or "")
    ):
        return "ApiBasicRequired"

    return None


def check_inbound_auth(cfg, headers):
    """Authenticate an inbound device request against the station's API
    settings (None / Basic Auth / Bearer Token / API Key). Constant-time
    comparisons; `headers` is any case-insensitive mapping (request.headers)."""
    auth = cfg.get("Authentication") or "none"
    if auth == "none":
        return True

    if auth == "basic":
        header = str(headers.get("Authorization") or "")
        if not header.lower().startswith("basic "):
            return False
        try:
            user, _, password = (
                base64.b64decode(header[6:].strip()).decode("utf-8").partition(":")
            )
        except Exception:
            return False
        return hmac.compare_digest(
            user, str(cfg.get("Auth_Username") or "")
        ) and hmac.compare_digest(password, str(cfg.get("Auth_Password") or ""))

    token = str(cfg.get("Token") or "")
    if not token:
        return False

    if auth == "bearer":
        header = str(headers.get("Authorization") or "")
        if not header.lower().startswith("bearer "):
            return False
        return hmac.compare_digest(header[7:].strip(), token)

    if auth == "key":
        name = str(cfg.get("API_Key_Header") or "X-API-Key").strip() or "X-API-Key"
        return hmac.compare_digest(str(headers.get(name) or ""), token)

    return False


def lookup_path(data, path):
    """Resolve a dotted path ("DI0.state", "items.0.value") inside nested
    dicts / lists. Returns None when any segment is missing."""
    current = data
    for part in str(path or "").split("."):
        if part == "":
            continue
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            return None
        if current is None:
            return None
    return current


def apply_key_mapping(payload, rows):
    """Apply Inbound Data Mapping rows [{"key": <device key>, "field": <column>}]
    to a device payload -> {column: value}. Blank rows and missing keys are
    skipped so partial payloads never fail."""
    mapped = {}
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        key = str(row.get("key") or "").strip()
        field = str(row.get("field") or "").strip()
        if not key or not field:
            continue
        value = lookup_path(payload, key)
        if value is not None:
            mapped[field] = value
    return mapped


def extractPrefixedData(array, prefix):
    return [
        {key[len(prefix) : -1]: value} for key, value in array if key.startswith(prefix)
    ]


def generate_key(prefix, passphrase):
    hashed_bytes = hashlib.md5((prefix + passphrase).encode()).digest()
    return base64.b64encode(hashed_bytes).decode()


def app_encrypt(txt):
    key = base64.b64decode(os.environ.get("APP_KEY"))
    iv = base64.b64decode(os.environ.get("APP_IV"))

    cipher = AES.new(key, AES.MODE_CBC, iv)
    data = str(txt).encode()
    ct_bytes = cipher.encrypt(pad(data, AES.block_size))
    return base64.b64encode(ct_bytes).decode()


def app_decrypt(enc_str):
    key = base64.b64decode(os.environ.get("APP_KEY"))
    iv = base64.b64decode(os.environ.get("APP_IV"))

    cipher = AES.new(key, AES.MODE_CBC, iv)
    ct = base64.b64decode(enc_str)
    pt = unpad(cipher.decrypt(ct), AES.block_size)
    return pt.decode()


def cropImage(nw, nh, source, dest, quality=100):
    with Image.open(source) as img:
        imgw, imgh = img.size

        is_png = dest.lower().endswith(".png")

        if is_png:
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA")
        else:
            if img.mode in ("RGBA", "P"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(
                    img, mask=img.split()[3] if img.mode == "RGBA" else None
                )
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")

        if not nw and not nh:
            nw, nh = imgw, imgh
        elif not nw:
            ratio = nh / imgh
            nw = int(imgw * ratio)
        elif not nh:
            ratio = nw / imgw
            nh = int(imgh * ratio)

        if imgw <= nw and imgh <= nh:
            final_img = img
        else:
            if (imgw / imgh) == (nw / nh):
                final_img = img.resize((nw, nh), Image.Resampling.LANCZOS)
            else:
                final_img = ImageOps.fit(img, (nw, nh), Image.Resampling.LANCZOS)

        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if is_png:
            final_img.save(dest, "PNG", optimize=True)
        else:
            final_img.save(dest, "JPEG", quality=quality, optimize=True)


def rotateImage(source, dest, direction, quality=100):
    with Image.open(source) as img:
        if direction == "CW":
            rotated = img.rotate(-90, expand=True)
        elif direction == "CCW":
            rotated = img.rotate(90, expand=True)
        else:
            raise ValueError("Direction must be 'left' or 'right'.")

        rotated.save(dest, quality=quality)


def fileSizeConverter(bytes, decimals=2):
    if not bytes:
        return "0 Bytes"

    k = 1024
    dm = max(decimals, 0)
    sizes = ["Bytes", "KB", "MB", "GB", "TB", "PB"]
    i = int(math.floor(math.log(bytes, k)))
    size = round(bytes / math.pow(k, i), dm)

    return f"{size} {sizes[i]}"


def strip_html(text):
    return BeautifulSoup(text, "html.parser").get_text()


def ensure_int_list(raw_data):
    if not raw_data:
        return []

    if isinstance(raw_data, str):
        try:
            raw_data = json.loads(raw_data)
        except (json.JSONDecodeError, ValueError):
            raw_data = raw_data.strip("[]").split(",")

    if isinstance(raw_data, list):
        clean_list = []
        for item in raw_data:
            try:
                if item is not None and str(item).strip():
                    clean_list.append(int(str(item).strip()))
            except (ValueError, TypeError):
                continue
        return clean_list

    return []
