import os
import re
import math
import hashlib
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
    "php", "phtml", "php3", "php4", "php5", "php7", "phps", "pht",
    "asp", "aspx", "jsp", "jspx", "cgi", "pl", "py", "pyc", "pyo", "rb",
    "sh", "bash", "zsh", "bat", "cmd", "com", "exe", "dll", "msi", "scr",
    "vbs", "vbe", "js", "mjs", "jse", "ws", "wsf", "jar", "war", "class",
    "so", "bin", "htaccess", "htpasswd", "ini", "conf", "config",
    "svg", "svgz", "html", "htm", "xhtml", "shtml", "xml", "swf",
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
