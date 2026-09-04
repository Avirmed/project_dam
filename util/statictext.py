import os
from util import util

APP_MENU = util.APP_MENU
APP_DASHBOARD_MENU = util.APP_DASHBOARD_MENU
APP_NAME = "DAM"
APP_LANG = "en"
APP_DIRECTORY = os.path.dirname(os.path.dirname(__file__))
APP_STATIC_PATH = os.path.join(APP_DIRECTORY, "static")
# tmp/ is reserved for chunked front-end uploads (*.partN, assembled files);
# /main/cleartmp drops leftovers older than 24 h.
APP_TMP_PATH = os.path.join(APP_DIRECTORY, "tmp")
# Private worker data, laid out per station like the legacy server's folder:
#   RTU Data/<SiteCode>/csv/<LoggerID>/           CSV Logger files
#   RTU Data/<SiteCode>/<CameraID>/images/        camera snapshots (archive)
#   RTU Data/<SiteCode>/<CameraID>/images_temp/   newest SNAPSHOT_TEMP_COUNT copies
#   RTU Data/<SiteCode>/<CameraID>/images_out/    images queued for the FTP upload
#   RTU Data/_security_in/                        security-camera event drop folder
#   RTU Data/_unassigned/<CameraID>/              cameras without a station
# Outside static/ so it is never web-served; git-ignored. RTU_DATA_PATH in .env
# moves it elsewhere. Public worker output goes under static/data/.
APP_DATA_PATH = os.getenv("RTU_DATA_PATH") or os.path.join(APP_DIRECTORY, "RTU Data")
APP_DATA_SECURITY_DIR = "_security_in"
APP_DATA_UNASSIGNED_DIR = "_unassigned"
# Station TLS certificates / private keys live outside static/ so they are never
# web-served. Excluded from the /main/init reflection (filesystem path).
APP_CERT_PATH = os.path.join(APP_DIRECTORY, "certs")
# Trained YOLO weights uploaded per camera (ai/trained_models/<CameraID>.pt),
# read by the separate ai/detect.py interpreter. Filesystem path: excluded from
# the /main/init reflection like the other APP_*_PATH constants.
APP_MODEL_PATH = os.path.join(APP_DIRECTORY, "ai", "trained_models")
APP_KEY = util.generate_key("KEY_", APP_NAME)
APP_IV = util.generate_key("IV_", APP_NAME)
APP_COLOR = "#0d6efd"

UPLOAD_CK_FOLDER_IMAGE = os.path.join(APP_STATIC_PATH, "data", "uploads", "images")
UPLOAD_CK_FOLDER_FILE = os.path.join(APP_STATIC_PATH, "data", "uploads", "files")


LoginIn = "Login"
LoginDescription = "Please enter your username and password."

Logout = "Logout"
Settings = "Settings"

LogoutURL = "/logout"
LogoutFunction = "#logout"
UserSettingsFunction = "#settings"

RememberMe = "Remember Me"
ForgotPassword = "Forgot Password?"

Searching = "Search..."
Search = "Search"
EmptyData = "No data found"
All = "All"
ViewAll = "View All"

Add = "Add"
Edit = "Edit"
Delete = "Delete"
Save = "Save"
Send = "Send"
Close = "Close"
Cancel = "Cancel"
Yes = "Yes"
No = "No"
Loading = "Loading..."
Download = "Download"
Upload = "Upload"
Back = "Back"
Clean = "Clean"
Choose = "Choose"
Generate = "Generate"
Browse = "Browse"
Calculate = "Calculate"
RequiredField = "Required Field"

WebSite = "Website"
Dashboard = "Dashboard"
More = "More"
Read = "Read"
ReadMore = "Read More"
Watch = "Watch"
DarkTheme = "Dark theme"

Numbering = "No."
Number = "Number"
ImageSource = "Image"
Status = "Status"
CreateDate = "Created Date"
UpdateDate = "Updated Date"
File = "File"
Size = "Size"
Color = "Color"
Video = "Video"
Audio = "Audio"
Field = "Field"
Value = "Value"
Notifications = "Notifications"

horizontal = "Horizontal"
vertical = "Vertical"

# ProfileChart - axis titles for the surveyed cross-section preview
# (profilechart.js, Sensor -> Flow tab).
ProfileChart = {
    "x": "x-axis [m]",
    "y": "y-axis [m]",
}

# DamChart - localized axis titles for the dam cross-section (damchart.js).
#   x : distance axis title, y : elevation axis title.
DamChart = {
    "x": "ระยะ (เมตร)",
    "y": "ระดับ (ม.รทก.)",
}


WaterLevelInfo = "สถานะน้ำท่า"
Station = "สถานี"
WaterLevelTypes = {
    0: {"text": "ปกติ", "text_en": "Normal WL", "color": "#70ad47"},
    1: {"text": "เตือนภัย", "text_en": "Warning WL", "color": "#ffc000"},
    2: {"text": "วิกฤต", "text_en": "Critical WL", "color": "#ff0000"},
    3: {"text": "ขัดข้อง", "text_en": "No connection", "color": "#7f7f7f"},
}

ProjectField = {
    "ProjectID": "ID",
    "ProjectName": "Project name",
    "CustomerName": "Customer name",
    "SortOrder": "Order",
    "Status": "Status",
    "ImageSource": "Picture",
    "Remark": "Remark",
}

RiverBasinField = {
    "RiverBasinID": "ID",
    "WatershedName": "Watershed name",
    "SortOrder": "Order",
    "Status": "Status",
    "ImageSource": "Picture",
    "Remark": "Remark",
}

Regions = {
    1: "Northern",
    2: "Northeastern",
    3: "Central",
    4: "Western",
    5: "Eastern",
    6: "Southern",
}

MeasuredValues = {
    1: "ระดับน้ำ",
    2: "ปริมาณน้ำฝน",
    3: "ระดับน้ำ และปริมาณน้ำฝน",
}

SiteInstalls = {
    1: "เขื่อน",
    2: "อ่างเก็บน้ำ",
    3: "ปตร.",
    4: "ฝาย",
    5: "สะพาน",
}

StationField = {
    "StationID": "ID",
    "ProjectID": "Project",
    "RiverBasinID": "River Basin",
    "Region": "Region",
    "MeasuredValue": "Measured Value",
    "SiteInstall": "Site Install",
    "DeviceID": "Device ID",
    "SiteCode": "Site code",
    "SiteName": "Site name",
    "Address": "Address",
    "Latitude": "Latitude",
    "Longitude": "Longitude",
    "Zoom": "Zoom",
    "SamplingID": "SamplingID",
    "Meta": "Meta Data",
    "Status": "Status",
    "ImageSource": "Picture",
    "Remark": "Remark",
}

StationFormTab = {
    "main": "Main",
    "station_configures": "Station configures",
    "water_configures": "Water configures",
    "api": "REST API Server",
    "ftp": "Upload image FTP",
}

# StationConfigures - river cross-section reference levels that drive the dam
# chart. All values are elevations in metres above a common datum (MSL / ม.รทก.).
# Two "Water Level Points" are captured along the structure:
#   _UP   = Point 1, upstream of the gate/weir.
#   _DOWN = Point 2, downstream of the gate/weir.
# Field meanings (standard hydrology / stage-monitoring terms):
#   LEFT_BANK_WL    - left bank crest level (ระดับตลิ่งซ้าย): bank-full elevation on the left.
#   RIGHT_BANK_WL   - right bank crest level (ระดับตลิ่งขวา): bank-full elevation on the right.
#   ZEROGATE        - staff-gauge zero / datum (ศูนย์เสาระดับ): the reference level (0.00)
#                     that all stage readings are measured from.
#   GROUND_LEVEL_WL - riverbed / thalweg level (ระดับท้องน้ำ): the lowest bed elevation.
#   WARNING         - warning stage (ระดับน้ำเตือนภัย): flood-watch threshold.
#   CRITICAL        - critical / danger stage (ระดับน้ำวิกฤต): overbank / critical-flood threshold.
# Expected order: GROUND_LEVEL < ZEROGATE <= WARNING < CRITICAL <= bank crest.
StationConfigures = [
    {
        "title": "ข้อมูลท้องน้ำจุดที่ 1 ( Water Level Point 1)",
        "fields": {
            "LEFT_BANK_WL_UP": {
                "title": "LEFT_BANK_WL_UP – ระดับตลิ่งซ้าย",
                "placeholder": "",
            },
            "RIGHT_BANK_WL_UP": {
                "title": "RIGHT_BANK_WL_UP – ระดับตลิ่งขวา",
                "placeholder": "",
            },
            "ZEROGATE_UP": {
                "title": "ZEROGATE_UP - ศูนย์เสาระดับ (ม.รทก / MSL)",
                "placeholder": "",
            },
            "ZEROGATE_UP_SL": {
                "title": "ZEROGATE_UP - ศูนย์เสาระดับ (ม.รสม / SL)",
                "placeholder": "",
            },
            "GROUND_LEVEL_WL_UP": {
                "title": "GROUND_LEVEL_WL_UP -ระดับท้องน้ำ",
                "placeholder": "",  # "Current Water Level – ZeroGate",
            },
            "WARNING_UP": {"title": "WARNING_UP – ระดับน้ำเตือนภัย", "placeholder": ""},
            "CRITICAL_UP": {"title": "CRITICAL_UP – ระดับน้ำวิกฤต", "placeholder": ""},
        },
    },
    {
        "title": "ข้อมูลท้องน้ำจุดที่ 2 ( Water Level Point 2)",
        "fields": {
            "LEFT_BANK_WL_DOWN": {
                "title": "LEFT_BANK_WL_DOWN – ระดับตลิ่งซ้าย",
                "placeholder": "",
            },
            "RIGHT_BANK_WL_DOWN": {
                "title": "RIGHT_BANK_WL_DOWN – ระดับตลิ่งขวา",
                "placeholder": "",
            },
            "ZEROGATE_DOWN": {
                "title": "ZEROGATE_DOWN - ศูนย์เสาระดับ (ม.รทก / MSL)",
                "placeholder": "",
            },
            "ZEROGATE_DOWN_SL": {
                "title": "ZEROGATE_DOWN - ศูนย์เสาระดับ (ม.รสม / SL)",
                "placeholder": "",
            },
            "GROUND_LEVEL_WL_DOWN": {
                "title": "GROUND_LEVEL_WL_DOWN -ระดับท้องน้ำ",
                "placeholder": "",  # "Current Water Level – ZeroGate",
            },
            "WARNING_DOWN": {
                "title": "WARNING_DOWN – ระดับน้ำเตือนภัย",
                "placeholder": "",
            },
            "CRITICAL_DOWN": {
                "title": "CRITICAL_DOWN – ระดับน้ำวิกฤต",
                "placeholder": "",
            },
        },
    },
]

WaterConfigures = [
    {
        "title": "Sensor – เซ็นเซอร์ (Mapping SQL DataSensor TO DataStation)",
        "fields": {
            "WaterLevelPoint1_UP": {
                "title": "Water Level Point 1 (UP)",
                "max": 100,
                "placeholder": "",
                "checkbox": True,
                "radio": ["MSL", "SL"],
            },
            "WaterLevelPoint2_DOWN": {
                "title": "Water Level Point 2 (DOWN)",
                "max": 101,
                "placeholder": "",
                "checkbox": True,
                "radio": ["MSL", "SL"],
            },
            "Velocity": {
                "title": "Velocity - ความเร็วกระแสน้ำ",
                "max": 101,
                "placeholder": "",
                "checkbox": True,
            },
            "FlowRate": {
                "title": "Flow Rate - อัตราการไหล",
                "max": 101,
                "placeholder": "",
                "checkbox": True,
            },
            "Direction": {
                "title": "Direction - ทิศทางการไหล",
                "max": 100,
                "placeholder": "",
                "checkbox": True,
            },
            "WaterColor": {
                "title": "Water Color - สีของน้ำ",
                "max": 100,
                "placeholder": "",
                "checkbox": True,
            },
            "Garbage": {
                "title": "Garbage - พื้นที่ตะกอน %",
                "max": 100,
                "placeholder": "",
                "checkbox": True,
            },
            "RainfallLevel": {
                "title": "ระดับน้ำฝน (Rainfall Level)",
                "max": 100,
                "placeholder": "",
                "checkbox": True,
            },
        },
    }
]

APIMethots = {
    "get": "GET",
    "post": "POST",
    "put": "PUT",
    "delete": "DELETE",
}

API_Protocols = {
    "http": "HTTP",
    "https": "HTTPS",
    "both": "Both (HTTP & HTTPS)",
}

API_HTTP_Sources = {
    "custom": "Custom",
    "ipv4": "Anywhere IPv4 (0.0.0.0/0)",
    "ipv6": "Anywhere IPv6 (::/0)",
}

API_SSL_Modes = {
    "off": "OFF",
    "one_way": "One-Way SSL (Standard HTTPS – Server Authenticated)",
    "two_way": "Two-Way SSL (Mutual TLS / mTLS – Highly Secure)",
}

API_Authentications = {
    "none": "None",
    "basic": "Basic Auth",
    "bearer": "Bearer Token",
    "key": "API Key",
}

# APIConfigures - per-station inbound "REST API Server" settings, stored as
# Station.Meta["API"] = {"status": bool, "configs": {<key>: <value>}}.
# Per-field attributes understood by dashboard/main/config_field.html + project.js:
#   type      : text | number | password | select | table | file | generate
#   show_when : {<other field>: [values]} - shown only while every listed field
#               holds one of its values (AND). Hidden fields still serialize; the
#               backend validator only checks fields that apply.
#   accept    : allowed extensions for type "file". The browser uploads straight to
#               `upload` (a /api/... route) and only the stored filename is kept in
#               Meta - certificate / private-key files never enter the JSON column.
#   generate  : /api/... route returning a fresh secret for a readonly field.
#   help      : small hint under the input.
#   column_options : type "table" only, {column: <option map>} renders that column
#                    as a select instead of free text.
# Protocol / listener port / SSL describe the reverse proxy in front of the app;
# the inbound endpoint itself is POST /api/inbound/<DeviceID>.
APIConfigures = [
    {
        "fields": {
            "Protocol": {
                "title": "Protocol",
                "placeholder": "",
                "select": API_Protocols,
            },
            "Port": {
                "title": "HTTP Port (Listener Port)",
                "placeholder": "0 – 65,535",
                "type": "number",
                "min": 0,
                "max": 65535,
                "show_when": {"Protocol": ["http", "both"]},
            },
            "HTTP_Source": {
                "title": "HTTP Source",
                "placeholder": "",
                "select": API_HTTP_Sources,
                "show_when": {"Protocol": ["http", "both"]},
            },
            "HTTP_Source_Custom": {
                "title": "HTTP Source (Custom IP / CIDR)",
                "placeholder": "203.0.113.10, 198.51.100.0/24",
                "help": "Comma-separated IP addresses or CIDR ranges allowed to call the API.",
                "show_when": {"Protocol": ["http", "both"], "HTTP_Source": ["custom"]},
            },
            "HTTPS_Port": {
                "title": "HTTPS Port (Listener Port)",
                "placeholder": "0 – 65,535",
                "type": "number",
                "min": 0,
                "max": 65535,
                "show_when": {"Protocol": ["https", "both"]},
            },
            "HTTPS_Source": {
                "title": "HTTPS Source",
                "placeholder": "",
                "select": API_HTTP_Sources,
                "show_when": {"Protocol": ["https", "both"]},
            },
            "HTTPS_Source_Custom": {
                "title": "HTTPS Source (Custom IP / CIDR)",
                "placeholder": "203.0.113.10, 198.51.100.0/24",
                "help": "Comma-separated IP addresses or CIDR ranges allowed to call the API.",
                "show_when": {
                    "Protocol": ["https", "both"],
                    "HTTPS_Source": ["custom"],
                },
            },
            "SSL_Mode": {
                "title": "SSL/TLS Mode",
                "placeholder": "",
                "select": API_SSL_Modes,
                "show_when": {"Protocol": ["https", "both"]},
            },
            "SSL_Cert": {
                "title": "SSL Certification File (.crt / .pem)",
                "type": "file",
                "accept": ".crt,.pem",
                "upload": "/api/stations/certupload",
                "show_when": {
                    "Protocol": ["https", "both"],
                    "SSL_Mode": ["one_way", "two_way"],
                },
            },
            "SSL_Key": {
                "title": "SSL Private Key File (.key)",
                "type": "file",
                "accept": ".key,.pem",
                "upload": "/api/stations/certupload",
                "show_when": {
                    "Protocol": ["https", "both"],
                    "SSL_Mode": ["one_way", "two_way"],
                },
            },
            "SSL_CA_Cert": {
                "title": "CA Client Root Certificate (.crt / .pem)",
                "type": "file",
                "accept": ".crt,.pem",
                "upload": "/api/stations/certupload",
                "help": "* Required only for Two-Way mTLS Mode",
                "show_when": {"Protocol": ["https", "both"], "SSL_Mode": ["two_way"]},
            },
            "divider-1": "",
            "Authentication": {
                "title": "Authentication",
                "placeholder": "",
                "select": API_Authentications,
            },
            "Auth_Username": {
                "title": "Username",
                "placeholder": "",
                "show_when": {"Authentication": ["basic"]},
            },
            "Auth_Password": {
                "title": "Password",
                "placeholder": "",
                "type": "password",
                "show_when": {"Authentication": ["basic"]},
            },
            "API_Key_Header": {
                "title": "API Key Header Name",
                "placeholder": "X-API-Key",
                "show_when": {"Authentication": ["key"]},
            },
            "Token": {
                "title": "Token",
                "type": "generate",
                "generate": "/api/stations/token",
                "help": "Send as 'Authorization: Bearer <token>' or in the API key header.",
                "show_when": {"Authentication": ["bearer", "key"]},
            },
            "divider-2": "",
            "Keys": {
                "title": "Inbound Data Mapping",
                "help": "(Fetch the custom mapping rules (JSONB dictionary) stored for that specific station to database)",
                "table": True,
                "headers": ["Device JSON Key", "Database Column"],
                "columns": ["key", "field"],
                "align": "start",
            },
        }
    }
]

StationDataField = {
    "ID": "ID",
    "StationID": "Station",
    "SiteCode": "Site code",
    "SiteName": "Station",
    "DeviceID": "Device ID",
    "RecordTime": "Record time",
    "Data": "Mapped data",
    "Raw": "Raw payload",
    "CreateDate": "Created Date",
    # Station Data page (dashboard/stationdata): filters, tiles, chart, detail
    "Parameter": "Parameter",
    "Min": "Min",
    "Max": "Max",
    "Range": "Period",
    "DateFrom": "From",
    "DateTo": "To",
    "Bucket": "Resolution",
    "Chart": "Chart",
    "Detail": "Payload detail",
    "Total": "Payloads",
    "Stations": "Stations",
    "FirstRecord": "First record",
    "LastRecord": "Last record",
    "Points": "points",
    "Avg": "avg",
    "SelectStation": "Select one station to draw the chart.",
    "NoNumeric": "No numeric values for this parameter in the selected period.",
    "RawPurged": "raw payload removed by retention",
}

# Public front pages (templates/modules/*): map popup, station detail (design
# slide 8), CCTV (slides 4-7), Statistics / Report (slide 9), notifications.
FrontPage = {
    "Popup": {
        "WaterLevel": "Water Level",
        "FlowRate": "Flow Rate",
        "Velocity": "Water Flow Velocity",
        "VelocityShort": "Velocity",  # map popup tile (narrow)
        "Rainfall": "Rainfall",
        "LastUpdate": "Last Update",
        "More": "More",
        "Statistics": "Statistics",
        "NoData": "No data received yet",
    },
    "Station": {
        "Title": "Station",
        "Measurements": "Measurement Value - ข้อมูลตรวจวัด",
        "Specifications": "Station Specifications - ข้อมูลท้องน้ำของสถานี",
        "Info": "Station Specifications - ข้อมูลจำเพาะของสถานี",
        "Image": "Station Image",
        "CrossSection": "Cross-section · live water level",
        "CrossSectionZoom": "Click to enlarge",
        "Breadcrumb": "Station",
        "Cameras": "Cameras",
        "NoCameras": "No cameras configured",
        "Events": "Recent security events",
        "NoEvents": "No security events",
        "AllEvents": "All events",
        "Data": "Measurements",
        "OpenCCTV": "CCTV",
        "Above": "above",
        "Below": "below",
        "Warning": "warning",
        "Critical": "critical",
        "RainAcc": "Rain accumulated {n} day(s)",
        "LatestRainfall": "Latest Rainfall",
        "LastUpdate": "Last Update",
        "Point1": "ข้อมูลท้องน้ำจุดที่ 1 ( Water Level Point 1 )",
        "Point2": "ข้อมูลท้องน้ำจุดที่ 2 ( Water Level Point 2 )",
        "Name": "Station_Name - ชื่อสถานี",
        "Code": "Station_Code - รหัส",
        "RiverBasin": "River_Basin - ลุ่มน้ำ",
        "Project": "Project - โครงการ",
        "Latitude": "Latitude - ละติจูด",
        "Longitude": "Longitude - ลองจิจูด",
        "Location": "Location - ที่ตั้ง",
        "MeasuredValue": "Measured_Value - ค่าที่ตรวจวัด",
        "SiteInstall": "Site Install",
        "Region": "Region",
        "GoogleMap": "Google Maps",
        "Chart": "Last 7 days",
        "NotFound": "Station not found",
        "Back": "Back to map",
    },
    "CCTV": {
        "Title": "CCTV",
        "Stations": "Stations",
        "Search": "Search station",
        "CameraType": "Camera type",
        "NoCameras": "No cameras configured for this station",
        "NoSnapshot": "No snapshot yet",
        "Snapshot": "Snapshot",
        "TakenAt": "Taken at",
        "Download": "Download",
        "Enlarge": "Click to enlarge",
        "Animation": "Animation of the latest snapshots",
        "PrintReport": "Print Report",
        "SelectStation": "Select a station on the left",
        "Cameras": "camera(s)",
    },
    "Statistics": {
        "Title": "Station Statistics",
        "Parameters": "Parameters",
        "SelectStation": "Select a station to draw the charts",
        "NoData": "No data for this parameter in the selected period",
        "ExportCSV": "CSV",
        "Print": "PDF / Print",
        "Points": "points",
    },
    "Report": {
        "Title": "Report",
        "Hint": "Select the period and, optionally, the station; export with the buttons above the table.",
    },
    "Notifications": {
        "Title": "Notifications",
        "Empty": "No pending security events",
        "ViewAll": "View all events",
        "Pending": "pending",
    },
}

# Labels of the shared filter fields (templates/dashboard/main/filter_field.html).
FilterLabels = {
    "Project": "Project",
    "Watershed": "Watershed",
    "Station": "Station",
    "Region": "Region",
    "Status": "Status",
    "UserType": "User type",
    "Period": "Period",
    "Date": "Date",
    "DateFrom": "From",
    "DateTo": "To",
    "Parameter": "Parameter",
    "Min": "Min",
    "Max": "Max",
}

# Quick period filter on the Station Data page (seconds back from now;
# "custom" = use the From / To dates).
StationDataRanges = {
    "1h": {"text": "Last hour", "seconds": 3600},
    "6h": {"text": "Last 6 hours", "seconds": 6 * 3600},
    "24h": {"text": "Last 24 hours", "seconds": 24 * 3600},
    "7d": {"text": "Last 7 days", "seconds": 7 * 86400},
    "30d": {"text": "Last 30 days", "seconds": 30 * 86400},
    "custom": {"text": "Custom dates", "seconds": 0},
}

# Chart resolution: "auto" picks raw / hourly / daily from the row count.
StationDataBuckets = {
    "auto": "Auto",
    "raw": "Raw values",
    "hour": "Hourly average",
    "day": "Daily average",
}

# StationDataKeys - the agreed "Database Column" names inside StationData.Data
# that the public site reads (map status, charts). Inbound Data Mapping rows
# must map the device keys onto these names for a station to get a live status.
StationDataKeys = {
    "WaterLevel": "WL",  # Water Level Point 1 -> compared with WARNING_UP / CRITICAL_UP
    "WaterLevel2": "WL2",  # Water Level Point 2 -> compared with WARNING_DOWN / CRITICAL_DOWN
    "Rainfall": "RAIN",
    "Velocity": "VELOCITY",  # surface velocity [m/s] from the device / camera
    "Flow": "FLOW",  # discharge [m³/s]; computed (A·k·v) when the device does not send it
    "Area": "AREA",  # wetted area [m²] used for the computed FLOW
    # camera analysis (services/ai_worker.py), text / flag values - kept out of the charts
    "Direction": "DIRECTION",  # surface flow direction: left / right (as seen by the camera)
    "WaterColor": "COLOR",  # dominant water colour #rrggbb
    "RainFlag": "RAIN_FLAG",  # 1 when the clip shows rain (vertical motion), else 0
}

# Labels / units of the StationData.Data columns shown as grid columns and
# chart parameters (keys = StationDataKeys values); "grid": False keeps a key
# out of the Station Data / Report grid (still stored and exported in Data).
StationDataParameters = {
    StationDataKeys["WaterLevel"]: {"text": "Water Level", "unit": "m"},
    StationDataKeys["WaterLevel2"]: {"text": "Water Level 2", "unit": "m"},
    StationDataKeys["Rainfall"]: {"text": "Rainfall", "unit": "mm"},
    StationDataKeys["Velocity"]: {"text": "Velocity", "unit": "m/s"},
    StationDataKeys["Flow"]: {"text": "Flow rate", "unit": "m³/s"},
    StationDataKeys["Area"]: {"text": "Wetted area", "unit": "m²"},
    # camera-analysis extras: kept in Data / exports, not shown as grid columns
    StationDataKeys["Direction"]: {"text": "Flow direction", "unit": "", "grid": False},
    StationDataKeys["WaterColor"]: {"text": "Water colour", "unit": "", "grid": False},
    StationDataKeys["RainFlag"]: {"text": "Rain detected", "unit": "", "grid": False},
}

# Settings rows rendered as an on/off switch on the dashboard Settings page
# (value stored as "1" / "0"); any name ending in _ENABLED is treated the same.
BooleanSettings = ["WORKER_ENABLED"]

# Retention defaults (days, 0 = keep forever) used when the Settings rows are
# missing; applied daily by services/retention.py.
DATA_RETENTION_DAYS = 730  # tbl_station_data rows
RAW_RETENTION_DAYS = 90  # raw device payload inside those rows
HTTPLOG_RETENTION_DAYS = 90  # delivered / failed HTTP logs
EVENTLOG_RETENTION_DAYS = 365  # security events + images
CSV_RETENTION_DAYS = (
    30  # CSV Logger files under RTU Data/<SiteCode>/csv (already sent by FTP)
)
SENT_IMAGE_RETENTION_DAYS = (
    7  # delivered camera images under RTU Data/<SiteCode>/<CameraID>/images_out/sent
)

# Camera snapshot refresh for the front CCTV page (services/snapshot.py);
# fallback when the SNAPSHOT_INTERVAL_MINUTES row is missing, 0 = off.
SNAPSHOT_INTERVAL_MINUTES = 5
# Pictures kept per camera in RTU Data/<SiteCode>/<CameraID>/images/ (oldest
# deleted after each download); fallback for the SNAPSHOT_KEEP_COUNT row,
# 0 = keep all.
SNAPSHOT_KEEP_COUNT = 100
# AI worker: frames extracted from each RTSP clip into images_temp/1..N.jpg
# (optical-flow input, animated into static/data/cameras/<CameraID>/image.gif);
# fallback for the AI_FRAME_COUNT row.
AI_FRAME_COUNT = 10

# AI worker (services/ai_worker.py): camera analysis every N minutes (0 = off)
# and the length of the RTSP clip it records per camera (raw_temp/).
AI_WORKER_INTERVAL_MINUTES = 15
AI_CLIP_SECONDS = 2

# Fallback when the DATA_TIMEOUT_MINUTES row is missing from Settings: a station
# whose latest payload is older than this is shown as "No connection".
DATA_TIMEOUT_MINUTES = 15

# Dashboard overview (/dashboard, GET /main/summary) - labels of every panel.
DashboardSummary = {
    "Title": "Dashboard",
    "Refresh": "Refresh",
    "Updated": "",
    "AutoRefresh": "{n} s",
    "Ago": "ago",
    "JustNow": "just now",
    "Stations": "Stations",
    "ActiveStations": "Stations",
    "PayloadsToday": "Today",
    "LastPayload": "Last",
    "Payloads24h": "Payloads · 24 h",
    "PerHour": "/ h",
    "StationStatus": "Status",
    "Attention": "Attention",
    "NoAttention": "All normal",
    "HttpDelivery": "HTTP",
    "SecurityEvents": "Events",
    "Worker": "Worker",
    "WorkerAlive": "Running",
    "WorkerStopped": "Stopped",
    "WorkerDisabled": "Off",
    "Job": "Job",
    "Interval": "Every",
    "LastRun": "Last",
    "NextRun": "Next",
    "Duration": "Time",
    "Runs": "Runs",
    "Errors": "Errors",
    "Result": "Result",
    "NeverRun": "-",
    "StartedAt": "Since",
    "LastTick": "Tick",
    "System": "System",
    "Uptime": "Uptime",
    "CPU": "CPU",
    "Memory": "Memory",
    "ProcessMemory": "App",
    "Disk": "Disk",
    "Free": "free",
    "Used": "used",
    "Database": "Database",
    "DbSize": "DB size",
    "Connections": "conn.",
    "Tables": "Tables",
    "Rows": "rows",
    "Folders": "Folders",
    "Files": "files",
    "Python": "Python",
    "PostgreSQL": "PostgreSQL",
    "Mode": "Mode",
    "Debug": "Debug",
    "Production": "Production",
    "Host": "Host",
    "PID": "PID",
    "Total": "Total",
    "Timeout": "> {n} min silent = No connection",
    "OpenStation": "Open",
    # duration suffixes: 2d 3h 15m 9s
    "Days": "d",
    "Hours": "h",
    "Minutes": "m",
    "Seconds": "s",
}

# Worker job names shown on the dashboard (keys = services/scheduler.py register()).
WorkerJobs = {
    "http_sender": "HTTP sender",
    "csv_logger": "CSV logger",
    "event_watcher": "Security event watcher",
    "image_uploader": "Image uploader (FTP)",
    "snapshot": "Camera snapshot",
    "sysinfo": "System monitor",
    "retention": "Data retention",
    "ai_worker": "AI worker (camera analysis)",
}

ConnectionModes = {
    "active": "Active Mode",
    "passive": "Passive Mode",
}

FileLargeTransfers = {
    "sm": "sm",
    "lg": "lg",
}

TransferTypes = {
    "binary": "binary",
    "ascii": "ascii",
}

TLSs = {
    "NoTLSSupport": "NoTLSSupport",
    "UseExplicitTLS": "UseExplicitTLS",
    "UseImplicitTLS": "UseImplicitTLS",
    "UseRequireTLS": "UseRequireTLS",
}

DirectoryStructures = {
    1: "Save in the Root directory",
    2: "Save in Parent directory",
    3: "Save in Child directory",
}

FTPConfigures = [
    {
        "fields": {
            "ServerIPAddress": {"title": "Server IP Address", "placeholder": ""},
            "Username": {"title": "Username", "placeholder": ""},
            "Password": {"title": "Password", "placeholder": "", "type": "password"},
            "ConnectionModes": {
                "title": "Connection Mode",
                "placeholder": "",
                "select": ConnectionModes,
            },
            "FileLargeTransfer": {
                "title": "File Large Transfer",
                "placeholder": "",
                "select": FileLargeTransfers,
            },
            "Port": {"title": "Port", "placeholder": ""},
            "Timeout": {"title": "Timeout", "placeholder": ""},
            "TransferType": {
                "title": "Transfer Type",
                "placeholder": "",
                "select": TransferTypes,
            },
            "TLS": {"title": "TLS", "placeholder": "", "select": TLSs},
            "DirectoryStructure": {
                "title": "Directory Structure",
                "placeholder": "",
                "select": DirectoryStructures,
            },
            "ParentDirectory": {"title": "Parent Directory", "placeholder": ""},
            "ChildDirectory": {"title": "Child Directory", "placeholder": ""},
        }
    }
]

HTTPConfigures = [
    {
        "fields": {
            "URL": {"title": "Server URL (Host URL)", "placeholder": ""},
            "WL": {"title": "WL", "placeholder": ""},
            "HYDRO": {"title": "HYDRO", "min": 1, "max": 8, "placeholder": ""},
            "RF": {"title": "RF", "placeholder": ""},
            "SITE": {"title": "SITE", "placeholder": ""},
            "DT": {"title": "DT", "placeholder": ""},
            "BASIN": {"title": "BASIN", "min": 1, "max": 25, "placeholder": ""},
        }
    }
]

SensorTypes = {
    "WaterLevel": "Water Level",
    "Velocity": "Velocity",
    "FlowRate": "Flow Rate",
    "Direction": "Direction",
    "Garbage": "Garbage",
    "WaterColor": "Water Color",
    "RainfallLevel": "Rainfall Level",
}

SensorField = {
    "ID": "ID",
    "SensorID": "Sensor ID",
    "SensorName": "Sensor Name",
    "SensorType": "Sensor Type",
    "WaterLevels": "Water Level",
    "Velocities": "Velocity",
    "Flow": "Flow (cross-section)",
    "Direction": "Move",
    "Garbage": "Garbage",
    "Color": "Color",
    "RainLevel": "Rain Level",
    "ProfileChart": "Cross-section preview",
    "Status": "Status",
    "Remark": "Remark",
}

SensorFormTab = {
    "main": "Main",
    "water_configures": "Water Level",
    "velocities_configures": "Velocity",
    "flow_configures": "Flow",
    "direction_configures": "Direction",
    "garbage_configures": "Garbage",
    "rainlevel_configures": "Rain Level",
}

# Image-analysis detection region shared by the Velocity / Garbage / Rain Level
# tabs: two corner points (pixels) per row, as on the design (Point 1 x/y, Point 2 x/y).
SensorPointsTable = {
    "headers": ["Point 1 x", "Point 1 y", "Point 2 x", "Point 2 y"],
    "columns": ["p1x", "p1y", "p2x", "p2y"],
}

# Which pixel row a Sampling table refers to (AI worker, ai/detect.py level_from)
LevelFroms = {
    "frame": "Full frame",
    "crop": "Detection region",
}

# Water Level tab: Sampling tables per camera (several rows = several gauges, the
# lowest reading wins), the optional region handed to the YOLO model (empty =
# whole frame) and whether the Sampling pixel rows were surveyed on the full
# frame or on that region.
SensorWaterLevelConfigures = [
    {
        "fields": {
            "WaterLevel": {
                "title": "Water Level",
                "placeholder": "",
                "table": True,
                "headers": ["Sampling", "CameraID", "SamplingID"],
                "columns": ["Sampling", "CameraID", "SamplingID"],
                "align": "end",
            },
            "Points": {
                "title": "Detection region (optional)",
                "placeholder": "",
                "table": True,
                "headers": SensorPointsTable["headers"],
                "columns": SensorPointsTable["columns"],
                "align": "end",
                "help": "Region of the camera frame given to the water-level model; leave empty for the whole frame.",
            },
            "LevelFrom": {
                "title": "Sampling pixel rows refer to",
                "placeholder": "",
                "select": LevelFroms,
            },
        }
    }
]

SensorVelocityConfigures = [
    {
        "fields": {
            "Points": {
                "title": "Detection points",
                "placeholder": "",
                "table": True,
                "headers": SensorPointsTable["headers"],
                "columns": SensorPointsTable["columns"],
                "align": "end",
            },
            # Real-world width (m) of the detection region: optical-flow pixel
            # displacement is scaled by Length / region width to get m/s.
            "Length": {
                "title": "Region length (m)",
                "placeholder": "",
                "type": "number",
                "min": 0,
                "step": "0.01",
                "help": "Distance in metres covered by the detection region horizontally (Point 1 x to Point 2 x).",
            },
            # Level-depending velocity calibration: coefficient (k) and offset
            # applied when the water level reaches the given level.
            "CalTable": {
                "title": "LEVEL DEPENDING VELOCITY CAL. TABLE",
                "placeholder": "",
                "table": True,
                "headers": ["Coefficient (k)", "Level", "Offset"],
                "columns": ["coefficient", "level", "offset"],
                "align": "end",
            },
        }
    }
]

Moves = {
    "RightLeft": "Right - Left",
    "LeftRight": "Left - Right",
    "ForwardBackward": "Forward - Backward",
    "BackwardForward": "Backward - Forward",
}

SensorDirectionConfigures = [
    {
        "fields": {
            "Move": {"title": "Move", "placeholder": "", "select": Moves},
        }
    }
]

SensorGarbageConfigures = [
    {
        "fields": {
            # colour of the detected garbage / sediment area (design slide 9)
            "Color": {
                "title": "Color",
                "placeholder": "",
                "type": "color",
                "default": "#ffffff",
            },
            "Points": {
                "title": "Detection points",
                "placeholder": "",
                "table": True,
                "headers": SensorPointsTable["headers"],
                "columns": SensorPointsTable["columns"],
                "align": "end",
            },
        }
    }
]

SensorRainLevelConfigures = [
    {
        "fields": {
            "Points": {
                "title": "Detection points",
                "placeholder": "",
                "table": True,
                "headers": SensorPointsTable["headers"],
                "columns": SensorPointsTable["columns"],
                "align": "end",
            },
        }
    }
]

AreaRefs = {
    "Level": "Level",
    "Depth": "Depth",
}

# SensorFlowConfigures - the Flow tab of a sensor (design rev.22 slide 9), stored
# as Sensor.Meta["Flow"] = {"status": bool, "configs": {...}}:
#   AreaRef       - y-axis reference of the surveyed points: Level (elevation, up)
#                   or Depth (below the reference, down).
#   AreaDate      - survey date (วันที่ทำการสำรวจ).
#   CustomProfile - surveyed cross-section polygon, points in order (x across the
#                   channel [m], y per AreaRef [m]); e.g. the red outline of a culvert.
#   Profile       - water level -> wetted area [m²]. Filled by the "Calculate"
#                   button (POST /api/sensors/profile -> util/hydro.py) or typed
#                   in; saved as entered.
#   FlowCalcTable - level-depending flow coefficient k = reference velocity /
#                   measured surface velocity (RTQ-Log "LEVEL DEPENDING FLOW CAL.
#                   TABLE"), linear interpolation between levels.
# Flow Q [m³/s] = Area(h) × k(h) × surface velocity - computed on every inbound
# payload (StationData.apply_flow) for the station whose Water configures
# "Flow Rate" row points at this sensor (checked + text = SensorID), using the
# mapped WL and VELOCITY values; stored as FLOW / AREA in StationData.Data.
SensorFlowConfigures = [
    {
        "fields": {
            "AreaRef": {
                "title": "Ref.",
                "placeholder": "",
                "select": AreaRefs,
                "help": "Level: y = elevation (up). Depth: y = distance below the reference, as read by a downward-looking sensor (depth 0 = water at the reference).",
            },
            "AreaDate": {
                "title": "วันที่ทำการสำรวจ (Survey Date)",
                "placeholder": "",
                "type": "date",
            },
            "divider-1": "",
            "CustomProfile": {
                "title": "Custom Profile",
                "help": "Surveyed cross-section points in order: x across the channel [m], y per Ref. [m].",
                "table": True,
                "headers": ["x-axis", "y-axis"],
                "columns": ["x", "y"],
                "align": "start",
            },
            "Profile": {
                "title": "Profile",
                "help": "Water level → wetted area. Press Calculate to derive it from the Custom Profile (a row at every surveyed level, extra 0.01 m rows only where the section widens); rows are saved exactly as shown, so a table from survey software can be entered as-is.",
                "table": True,
                "headers": ["Water Level (before convert) [m]", "Area [m²]"],
                "columns": ["WaterLevel", "Area"],
                "align": "start",
            },
            "FlowCalcTable": {
                "title": "LEVEL DEPENDING FLOW CAL. TABLE",
                "help": "Coefficient k = reference velocity / measured surface velocity per water level; interpolated linearly.",
                "table": True,
                "headers": ["Water Level (before convert)", "Coefficient (k)"],
                "columns": ["WaterLevel", "Coefficient"],
                "align": "start",
            },
        },
    },
]

CameraTypes = {
    "Sensor": "Sensor",
    "Overview": "Overview",
    "Security": "Security",
}

# YOLO inference size per camera model (Camera configures form)
ModelImageSizes = {
    "640": "640 px",
    "1024": "1024 px",
}

CameraSources = {
    "FTP": "FTP",
    "RTSP": "RTSP ( Real-Time Streaming Protocol )",
}

Resolutions = {
    "2592_1944": "5 MP ( 2592 × 1944 )",
    "2560_1440": "4 MP ( 2560 x 1440 )",
    "2688_1520": "4 MP ( 2688 x 1520 )",
    "1920_1080": "2 MP ( 1920 x 1080 )",
    "1280_720": "1 MP ( 1280 x 720 )",
}

CameraField = {
    "ID": "ID",
    "CameraID": "CameraID",
    "CameraName": "Camera Name",
    "CameraConfigures": "Camera Configures",
    "UploadConfigures": "Upload JPG Configures",
    "StationID": "StationID",
    "CameraType": "Camera Type",
    "CCTV_NO": "CCTV NO",
    "CameraSource": "Camera Source",
    "Resolution": "Resolution",
    "RSTP_IP": "RSTP IP",
    "TrainedModel": "Profile (Model Trained)",
    "TrainedModelHelp": "YOLO weights (.pt) used by the AI water-level detector; stored as ai/trained_models/<CameraID>.pt. Save the camera first.",
    "TrainedModelRemove": "Remove the uploaded model file",
    "ModelImageSize": "Model image size",
    "ModelImageSizeHelp": "Inference size the model was trained with (640 for most stations, 1024 for the TS.KB type).",
    "Port": "Port",
    "Username": "Username",
    "Password": "Password",
    "ChannelsID": "Channels ID",
    "FPS": "FPS",
    "ISAPI_Port": "ISAPI Port",
    "Links": "Generated links (RTSP / ISAPI)",
    "StreamURL": "RTSP stream link",
    "SnapshotURL": "ISAPI snapshot link",
    "LinksHelp": "Built from RTSP IP, Port, Username, Password, Channels ID and ISAPI Port: "
    "rtsp://user:pass@ip:port/Streaming/Channels/<ID> and http://user:pass@ip:isapi_port/ISAPI/Streaming/channels/<ID>/picture",
    "LastUploadRun": "Last upload",
    "LastUploadResult": "Last upload result",
    "SnapshotImage": "Latest snapshot",
    "SnapshotTime": "Snapshot taken at",
    "SnapshotHelp": "Refreshed by the worker every SNAPSHOT_INTERVAL_MINUTES from the ISAPI snapshot link into RTU Data/<SiteCode>/<CameraID>/images and shown on the front CCTV page (the AI worker animation takes precedence when present).",
    "Onvif": "Onvif (ONVIF Profile G Specification )",
    "Onvif_IP": "Onvif IP",
    "Onvif_Port": "Port",
    "Onvif_UserName": "Username",
    "Onvif_Password": "Password",
    "Status": "Status",
    "Remark": "Remark",
}

# File field of the camera form (rendered by dashboard/main/config_field.html):
# uploads go straight to `upload`, the remove button POSTs `remove`, and only
# the stored file name lives in Meta.CameraConfigures.configs.TrainedModel.
CameraModelField = {
    "title": CameraField["TrainedModel"],
    "type": "file",
    "accept": ".pt",
    "upload": "/api/cameras/modelupload",
    "remove": "/api/cameras/modeldelete",
    "help": CameraField["TrainedModelHelp"],
    "remove_title": CameraField["TrainedModelRemove"],
}

CameraFormTab = {
    "main": "Main",
    "camera_configures": CameraField["CameraConfigures"],
    "upload_configures": CameraField["UploadConfigures"],
}

UploadConfigures = [
    {
        "fields": {
            "ServerIPAddress": {"title": "Server IP Address", "placeholder": ""},
            "ConnectionModes": {
                "title": "Connection Mode",
                "placeholder": "",
                "select": ConnectionModes,
            },
            "FileLargeTransfer": {
                "title": "File Large Transfer",
                "placeholder": "",
                "select": FileLargeTransfers,
            },
            "Port": {"title": "Port", "placeholder": ""},
            "Timeout": {"title": "Timeout", "placeholder": ""},
            "Username": {"title": "Username", "placeholder": ""},
            "Password": {"title": "Password", "placeholder": "", "type": "password"},
            "TransferType": {
                "title": "Transfer Type",
                "placeholder": "",
                "select": TransferTypes,
            },
            "TLS": {"title": "TLS", "placeholder": "", "select": TLSs},
            "DirectoryStructure": {
                "title": "Directory Structure",
                "placeholder": "",
                "select": DirectoryStructures,
            },
            "ParentDirectory": {"title": "Parent Directory", "placeholder": ""},
            "ChildDirectory": {"title": "Child Directory", "placeholder": ""},
        }
    }
]

SamplingField = {
    "ID": "ID",
    "SamplingID": "SamplingID",
    "SamplingName": "Sampling Name",
    "SamplingDate": "วันที่สร้าง (Creation Date)",
    "SamplingConfigures": "Camera Configures",
    "PixelY": "Pixel Y (row on the frame)",
    "Level": "Water level (m)",
    "TableHelp": "Surveyed pairs of camera pixel row and water level; the detector fits a cubic spline through them (rows sorted by pixel).",
    "Status": "Status",
    "Remark": "Remark",
}

SamplingFormTab = {
    "main": "Main",
    "sampling_configures": SamplingField["SamplingConfigures"],
}

SamplingConfigures = [
    {
        "title": SamplingField["SamplingConfigures"],
        "fields": {
            # Calibration table used by ai/calibration.py: x = pixel row of the
            # waterline on the camera frame, y = the water level surveyed for it.
            "CameraConfigures": {
                "title": "Camera Configures",
                "placeholder": "",
                "table": True,
                "headers": [SamplingField["PixelY"], SamplingField["Level"]],
                "columns": ["x", "y"],
                "align": "start",
                "help": SamplingField["TableHelp"],
            },
        },
    },
]

FileTransferField = {
    "ID": "ID",
    "StationID": "Site",
    "SiteName": "Site",
    "Hostname": "Hostname",
    "Connection": "Connection",
    "Status": "Status",
    "Remark": "Remark",
}

FileTransferFormTab = {
    "main": "Main",
    "configures": "Connection",
}

HTTP_SourceTypes = {
    "static": "Static Value",
    "sensor": "Sensor Data",
    "datetime": "Datetime",
}

HTTP_ContentTypes = {
    "json": "JSON",
    "text": "Plain Text",
}

# HTTPServiceConfigures - outbound HTTP delivery settings per station, stored as
# Http.Meta["Request"] = {"status": bool, "configs": {...}}. Group 1 = request +
# parameter mapping, group 2 = "Advanced Settings" (retry / SSL). Credential
# fields appear per authentication type (show_when); the mapping's Source Type
# column is a dropdown (HTTP_SourceTypes) and the form previews the resulting
# payload from the mapping rows.
HTTPServiceConfigures = [
    {
        "fields": {
            "Method": {"title": "HTTP Method", "placeholder": "", "select": APIMethots},
            "ContentType": {
                "title": "Content Type",
                "placeholder": "",
                "select": HTTP_ContentTypes,
            },
            "Timeout": {
                "title": "Timeout (seconds)",
                "placeholder": "",
                "type": "number",
                "min": 0,
            },
            "Authentication": {
                "title": "Authentication",
                "placeholder": "",
                "select": API_Authentications,
            },
            "Auth_Username": {
                "title": "Username",
                "placeholder": "",
                "show_when": {"Authentication": ["basic"]},
            },
            "Auth_Password": {
                "title": "Password",
                "placeholder": "",
                "type": "password",
                "show_when": {"Authentication": ["basic"]},
            },
            "Token": {
                "title": "Token",
                "placeholder": "",
                "help": "Bearer token or API key issued by the remote server.",
                "show_when": {"Authentication": ["bearer", "key"]},
            },
            "API_Key_Header": {
                "title": "API Key Header Name",
                "placeholder": "X-API-Key",
                "show_when": {"Authentication": ["key"]},
            },
            "divider-1": "",
            "Mapping": {
                "title": "Parameter Mapping",
                "help": "Static Value: sent as-is. Sensor Data: the device/sensor key to read. Datetime: format such as yyyymmddHHMM.",
                "table": True,
                "headers": [
                    "Source Type",
                    "Parameter Name (for API)",
                    "Source Value / Display Name",
                ],
                "columns": ["source_type", "param", "value"],
                "column_options": {"source_type": HTTP_SourceTypes},
                "align": "start",
            },
        }
    },
    {
        "title": "Advanced Settings",
        "fields": {
            "RetryAttempts": {
                "title": "Retry Attempts",
                "placeholder": "2",
                "type": "number",
                "min": 0,
            },
            "RetryDelay": {
                "title": "Retry Delay (seconds)",
                "placeholder": "10",
                "type": "number",
                "min": 0,
            },
            "VerifySSL": {
                "title": "Verify SSL Certificate",
                "type": "checkbox",
            },
        },
    },
]

HttpField = {
    "ID": "ID",
    "StationID": "Site",
    "SiteName": "Site",
    "URL": "Server URL (Host URL)",
    "Request": "Request",
    "Example": "ตัวอย่าง (Example payload)",
    "Status": "Status",
    "Remark": "Remark",
}

HttpFormTab = {
    "main": "Main",
    "configures": "Request",
}

HttpLogField = {
    "ID": "ID",
    "SiteName": "Site",
    "DeviceID": "device_id",
    "Method": "Method",
    "URL": "URL",
    "Request": "Request body",
    "Content": "content",
    "ResponseCode": "Response code",
    "Response": "Response",
    "Attempts": "Attempts",
    "NextAttempt": "Next attempt",
    "SentDate": "Sent",
    "Status": "Status",
    "CreateDate": "Date",
    "DateFrom": "วันที่ (From)",
    "DateTo": "ถึงวันที่ (To)",
    "Total": "ทั้งหมด",
    "Detail": "Delivery detail",
}

# Security camera events (design slide 10, public "Event Log" page).
EventLogField = {
    "ID": "ID",
    "Title": "Security - ระบบรักษาความปลอดภัย",
    "CameraID": "Camera",
    "StationID": "Station – สถานีโทรมาตร",
    "Image": "Picture",
    "WatershedName": "River - ลุ่มน้ำ",
    "EventTime": "Date Time",
    "Event": "Event – เหตุการณ์",
    "IP": "IP address",
    "Channel": "Channel",
    "Status": "Status",
    "Action": "Action",
    "Remark": "Remark",
    "DateFrom": "Since Date",
    "DateTo": "To Date",
    "Total": "ทั้งหมด",
}

EventLogStatuses = {
    0: {
        "text": "Pending",
        "class": "app-badge badge text-bg-secondary",
        "pill": "status-pill status-pill-pending",
    },
    1: {
        "text": "Approve",
        "class": "app-badge badge text-bg-danger",
        "pill": "status-pill status-pill-approve",
    },
    2: {
        "text": "Reject",
        "class": "app-badge badge text-bg-dark",
        "pill": "status-pill status-pill-reject",
    },
}
# Row action menu of the Event Log grids (one dropdown instead of two buttons)
EventLogActions = {"Menu": "Action", "SetStatus": "Set status"}

# Delivery lifecycle of an outbound HTTP payload (design slide 18).
HttpLogStatuses = {
    0: {"text": "Queue", "class": "app-badge badge text-bg-secondary"},
    1: {"text": "Sent (Success)", "class": "app-badge badge text-bg-success"},
    2: {"text": "Failed", "class": "app-badge badge text-bg-danger"},
}

# CSVLoggerConfigures - stored as CsvLogger.Meta["Logger"]; executed by the
# worker (services/csv_logger.py): one row per LogInterval into a daily CSV
# that is then uploaded through the logger's File Transfer connection.
CSVLoggerConfigures = [
    {
        "fields": {
            "LogInterval": {
                "title": "Log Interval (minutes)",
                "placeholder": "15",
                "help": "Time taken to save data to a CSV file (minutes); rows are aligned to the clock.",
                "type": "number",
                "min": 1,
            },
            "DeviceNameFirstLine": {
                "title": "Place Device Name on the first line of CSV Header",
                "type": "checkbox",
            },
            "Mapping": {
                "title": "Parameter Mapping",
                "help": (
                    "Drag rows to rearrange the column order. Source variable placeholders: "
                    "%DEVICENAME% device name, %DATETIME% (YYYY-MM-DD HH:MM:SS), %DATE% (YYYY-MM-DD), "
                    "%DATE_DMY% (DD/MM/YY), %TIME% (HH:MM:SS), %<column>% = value from the station's "
                    "mapped data, e.g. %WL%, %RAIN%. Any other text is written as-is."
                ),
                "table": True,
                "headers": [
                    "Header Name (FILE_HEADER)",
                    "Source Variable (FILE_FORMAT)",
                ],
                "columns": ["header", "source"],
                "align": "start",
            },
        }
    }
]

CsvLoggerField = {
    "ID": "ID",
    "FileTransferID": "File Transfer",
    "FileTransferHostname": "File Transfer",
    "FilenameFormat": "Filename Format",
    "FilenameFormatHelp": (
        "Placeholders: @DEVICENAME (site code), @DATE (YYYY-MM-DD) and date/time codes "
        "%Y %y %m %d %H %M %S. Example: @DEVICENAME_DataRecovery_%d%m%Y.csv -> TC.04_DataRecovery_12052026.csv"
    ),
    "Logger": "Logger",
    "LastRun": "Last run",
    "LastResult": "Last result",
    "Status": "Status",
    "Remark": "Remark",
}

CsvLoggerFormTab = {
    "main": "Main",
    "configures": "Logger",
}

TeamField = {
    "TeamID": "TeamID",
    "TeamName": "Team Name",
    "Stations": "Stations",
    "Users": "Users",
    "Status": "Status",
    "ImageSource": "Picture",
    "Remark": "Remark",
}

TeamFormTab = {
    "main": "Main",
    "team_configures": "Team members",
}

"""------------------------------------------------------------------------------------------------------------- """


UserTypes = {
    1: "Administrator",
    2: "Supervisor",
    3: "Staff",
    4: "Guest",
}

UserField = {
    "UserID": "ID",
    "UserName": "Username",
    "Password": "Password",
    "PasswordConfirm": "Confirm Password",
    "Email": "Email",
    "FirstName": "First Name",
    "LastName": "Last Name",
    "UserType": "Type",
    "Image": "Picture",
    "ImageSource": "Picture",
    "Status": "Status",
    "MultiLogin": "Allow multiple logins",
    "Remark": "Remark",
    "Theme": "Theme",
}

CKFinderFields = {
    "ImageTitle": "CKFinder - Image",
    "FileTitle": "CKFinder - File",
}

Messages = {
    "Title": "Notification",
    "LoginSuccess": "Login successful.",
    "LoginFailed": "Login failed.",
    "LogoutSuccess": "Logout successful.",
    "LogoutFailed": "An error occurred while logging out.",
    "UserNameIsRequired": "Please enter your username.",
    "UserPasswordIsRequired": "Please enter your password.",
    "UserNotFound": "User not found.",
    "UserAlreadyExists": "User already exists.",
    "UserCreated": "User information has been successfully registered.",
    "UserUpdated": "User information has been successfully updated.",
    "UserDeleted": "User information has been successfully deleted.",
    "UserNotDeleted": "An error occurred while deleting the user.",
    "UserNotUpdated": "An error occurred while updating the user.",
    "UserNotCreated": "An error occurred while creating the user.",
    "NoPermission": "You do not have permission to access this page.",
    "SettingsUpdated": "Settings have been successfully updated.",
    "SettingsNotUpdated": "An error occurred while updating the settings.",
    "SettingsNotFound": "Settings not found.",
    "SettingsCreated": "Settings have been successfully created.",
    "SettingsNotCreated": "An error occurred while creating the settings.",
    "SettingsDeleted": "Settings have been successfully deleted.",
    "SuccessSaved": "Data has been successfully saved.",
    "SuccessCreated": "Data has been successfully created.",
    "SuccessUpdated": "Data has been successfully updated.",
    "SuccessDeleted": "Data has been successfully deleted.",
    "UnsuccessDeleted": "An error occurred while deleting the data.",
    "DeleteQuestion": "Are you sure you want to delete?",
    "Error": "An error occurred.",
    "InvalidAccess": "Invalid access attempt.",
    "NoInternetConnection": "Please check your internet connection.",
    "FileSizeExceeded": "The file size exceeds the allowed limit.",
    "FileUploadError": "An error occurred while uploading the file.",
    "FileDeleteError": "An error occurred while deleting the file.",
    "FileDownloadError": "An error occurred while downloading the file.",
    "CannotAddDataAtThisLevel": "You cannot add data at this level.",
    "CannotDeleteTreeDataWithChildren": "Cannot delete because child records exist.",
    "TableNotFound": "Table not found.",
    "LettersOnly": "Please enter letters only.",
    "DuplicatedNumber": "Duplicate number found.",
    "CKEditorNotFound": "CKEditor window not found!",
    "Uploading": "Uploading...",
    "UploadSuccess": "File uploaded successfully.",
    "UploadFailed": "An error occurred while uploading.",
    "SaveFirstToUpload": "Save the record first, then upload files.",
    "InvalidFileType": "This file type is not allowed.",
    "TokenGenerated": "A new token has been generated. Save the form to apply it.",
    "CertUploaded": "Certificate file uploaded successfully.",
    "ModelUploaded": "Model file uploaded successfully.",
    "ModelDeleted": "Model file removed.",
    "DeleteFileQuestion": "Remove this file?",
    "ApiConfigInvalid": "REST API settings are invalid.",
    "ApiPortInvalid": "Listener port must be a number between 0 and 65,535.",
    "ApiSourceInvalid": "Custom source must be a comma-separated list of IP addresses or CIDR ranges.",
    "ApiCertRequired": "SSL certificate and private key files are required when SSL/TLS mode is enabled.",
    "ApiCaRequired": "A CA client root certificate is required for Two-Way (mTLS) mode.",
    "ApiTokenRequired": "Generate a token for Bearer Token / API Key authentication.",
    "ApiBasicRequired": "Username and password are required for Basic Auth.",
    "InboundReceived": "Data received.",
    "InboundStationNotFound": "No station matches this Device ID.",
    "InboundDisabled": "The REST API server is disabled for this station.",
    "InboundUnauthorized": "Authentication failed.",
    "InboundForbiddenSource": "The request source address is not allowed.",
    "InboundInvalidPayload": "The request body must be a JSON object.",
    "EventUpdated": "Event status updated.",
    "ProfileCalculated": "Profile table computed from the Custom Profile. Save the sensor to keep it.",
    "ProfileNeedsPoints": "Enter at least 3 Custom Profile points (x, y) first.",
}

Icon = {
    "WebSite": '<i class="fa fa-laptop"></i>',
    "Add": '<i class="bi bi-plus-lg"></i>',
    "AddCircle": '<i class="bi bi-plus-circle"></i>',
    "AddSquare": '<i class="ti ti-square-rounded-plus"></i>',
    "Search": '<i class="bi bi-search"></i>',
    "Info": '<i class="bi bi-info-circle"></i>',
    "x": '<i class="bi bi-x"></i>',
    "X": '<i class="bi bi-x-lg"></i>',
    "-": '<i class="bi bi-dash"></i>',
    "Login": '<i class="fa fa-sign-in"></i>',
    "Logout": '<i class="fa fa-sign-out"></i>',
    "Save": '<i class="bi bi-floppy"></i>',
    "Delete": '<i class="ti ti-trash"></i>',
    "Loading": '<i class="fa fa-circle-o-notch fa-spin"></i>',
    "LoadingCog": '<i class="fa fa-cog fa-spin fa-fw"></i>',
    "DatabaseGear": '<i class="bi bi-database-fill-gear"></i>',
    "Calculator": '<i class="bi bi-calculator"></i>',
    "Check": '<i class="bi bi-check-circle"></i>',
    "Refresh": '<i class="bi bi-arrow-clockwise"></i>',
    "Station": '<i class="bi bi-router"></i>',
    "WaterLevel": '<i class="bi bi-water"></i>',
    "Data": '<i class="bi bi-database"></i>',
    "Location": '<i class="bi bi-geo-alt"></i>',
    "Camera": '<i class="bi bi-camera-video"></i>',
    "Chart": '<i class="bi bi-graph-up"></i>',
    "Uncheck": '<i class="bi bi-x-circle"></i>',
    "CheckFill": '<i class="bi bi-check-circle-fill"></i>',
    "UncheckFill": '<i class="bi bi-x-circle-fill"></i>',
    "Checkbox": '<i class="bi bi-check2-square"></i>',
    "Calendar": '<i class="bi bi-calendar-week"></i>',
    "UserSettings": '<i class="bi bi-person-fill-gear"></i>',
    "VerticalDots": '<i class="bi bi-three-dots-vertical"></i>',
    "ReadMore": '<i class="fa fa-check-square-o"></i>',
    "Section": '<i class="bi bi-card-list"></i>',
    "Edit": '<i class="ti ti-edit"></i>',
    "File": '<i class="bi bi-file-earmark-text"></i>',
    "Video": '<i class="bi bi-film"></i>',
    "Audio": '<i class="bi bi-music-note-beamed"></i>',
    "Webcam": '<i class="bi bi-camera-reels"></i>',
    "Download": '<i class="bi bi-download"></i>',
    "DownloadCloud": '<i class="bi bi-cloud-arrow-down"></i>',
    "Upload": '<i class="bi bi-cloud-upload"></i>',
    "Copy": '<i class="bi bi-arrow-down-right-circle"></i>',
    "copy": '<i class="bi bi-copy"></i>',
    "paste": '<i class="bi bi-clipboard-plus"></i>',
    "laquo": '<i class="bi bi-chevron-left"></i>',
    "raquo": '<i class="bi bi-chevron-right"></i>',
    "List": '<i class="bi bi-list"></i>',
    "CodeSquare": '<i class="bi bi-code-square"></i>',
    "CardList": '<i class="bi bi-card-list"></i>',
    "JournalText": '<i class="bi bi-journal-text"></i>',
    "Photos": '<i class="bi bi-images"></i>',
    "Files": '<i class="bi bi-files"></i>',
    "GripHorizontal": '<i class="bi bi-grip-horizontal"></i>',
    "GripVertical": '<i class="bi bi-grip-vertical"></i>',
    "MetaData": '<i class="bi bi-ui-checks-grid"></i>',
    "email": '<i class="bi bi-envelope-fill"></i>',
    "phone": '<i class="bi bi-telephone-fill"></i>',
    "web": '<i class="bi bi-globe-asia-australia"></i>',
    "address": '<i class="bi bi-geo-alt-fill"></i>',
}

StatusLabel = {
    1: {"text": "Active", "class": "app-badge badge text-bg-danger"},
    0: {"text": "Inactive", "class": "app-badge badge text-bg-success"},
}

Export = {
    "Excel": "<i class='ti ti-file-type-xls'></i> Excel",
    "CSV": "<i class='ti ti-file-type-csv'></i> CSV",
    "PDF": "<i class='ti ti-file-type-pdf'></i> PDF",
    "Print": "<i class='ti ti-printer'></i> Print",
}

ResponseCode = {
    200: "Request completed successfully.",
    201: "New resource created successfully.",
    204: "Success, but no content to return.",
    400: "Bad request.",
    401: "Authentication required.",
    403: "Access is forbidden.",
    404: "Resource not found.",
    405: "Method not allowed.",
    422: "Validation failed. One or more fields are invalid.",
    500: "Internal server error.",
    502: "Bad gateway or upstream server error.",
    503: "Service unavailable or temporarily overloaded.",
}

Images = {
    "App-Logo": "/static/images/logo.png",
    "App-Icon": "/static/images/favicon.ico",
    "Logo": "/static/images/logo.png",
    "Logo-Dark": "/static/images/logo.png",
    "Logo-Small": "/static/images/logo.png",
    "Profile": "/static/images/default/user.jpg",
    "Blank": "/static/images/default/blank.png",
    "BlankCover": "/static/images/default/blank_cover.png",
}
