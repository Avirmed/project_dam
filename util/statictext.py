import os
from util import util

APP_MENU = util.APP_MENU
APP_DASHBOARD_MENU = util.APP_DASHBOARD_MENU
APP_NAME = "DAM"
APP_LANG = "en"
APP_DIRECTORY = os.path.dirname(os.path.dirname(__file__))
APP_STATIC_PATH = os.path.join(APP_DIRECTORY, "static")
APP_TMP_PATH = os.path.join(APP_DIRECTORY, "tmp")
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

x_axis = "x-axis"
y_axis = "y-axis"
horizontal = "Horizontal"
vertical = "Vertical"
water_level_convert = "Water Level (before convert) [m]"
area_m2 = "Area [m²]"
coefficient = "Coefficient (k)"


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
    "StationConfigures": "Station configures",
    "WaterConfigures": "Water configures",
    "SensorConfigures": "Sensor configures",
    "API": "API",
    "CSV": "Upload CSV FTP",
    "HTTP": "HTTP",
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
            "ZEROGATE_UP": {"title": "ZEROGATE_UP - ศูนย์เสาระดับ", "placeholder": ""},
            "GROUND_LEVEL_WL_UP": {
                "title": "GROUND_LEVEL_WL_UP -ระดับท้องน้ำ",
                "placeholder": "" # "Current Water Level – ZeroGate",
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
                "title": "ZEROGATE_DOWN - ศูนย์เสาระดับ",
                "placeholder": "",
            },
            "GROUND_LEVEL_WL_DOWN": {
                "title": "GROUND_LEVEL_WL_DOWN -ระดับท้องน้ำ",
                "placeholder": "" # "Current Water Level – ZeroGate",
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

APIConfigures = [
    {
        "fields": {
            "URL": {"title": "Server URL (Host URL)", "placeholder": ""},
            "Method": {"title": "Method", "placeholder": "", "select": APIMethots},
            "HeaderKey": {"title": "Header Key", "placeholder": ""},
            "Value": {"title": "Value", "placeholder": ""},
            "Keys": {
                "title": "Keys",
                "placeholder": "",
                "table": True,
                "headers": ["Key"],
                "columns": ["key"],
                "align": "start",
            },
        }
    }
]

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

CSVConfigures = [
    {
        "fields": {
            "ServerIPAddress": {"title": "Server IP Address", "placeholder": ""},
            "Username": {"title": "Username", "placeholder": ""},
            "Password": {"title": "Password", "placeholder": ""},
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
    "Flow": "AreaID",
    "Direction": "Move",
    "Garbage": "Garbage",
    "Color": "Color",
    "RainLevel": "Rain Level",
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
        }
    }
]

SensorVelocityConfigures = [
    {
        "fields": {
            "Velocity": {
                "title": "Velocity",
                "placeholder": "",
                "table": True,
                "headers": ["Point 1", "Point 1", "Horizontal", "Vertical"],
                "columns": ["Sampling", "CameraID", "SamplingID"],
                "align": "center",
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
            "Garbage": {
                "title": "Garbage",
                "placeholder": "",
                "table": True,
                "headers": ["Point 1", "Point 1", "Horizontal", "Vertical"],
                "columns": ["Sampling", "CameraID", "SamplingID"],
                "align": "center",
            },
        }
    }
]

SensorRainLevelConfigures = [
    {
        "fields": {
            "RainLevel": {
                "title": "Rain Level",
                "placeholder": "",
                "table": True,
                "headers": ["Point 1", "Point 1", "Horizontal", "Vertical"],
                "columns": ["Sampling", "CameraID", "SamplingID"],
                "align": "center",
            },
        }
    }
]

AreaRefs = {
    "Level": "Level",
    "Depth": "Depth",
}

AreaField = {
    "ID": "ID",
    "AreaID": "AreaID",
    "AreaRef": "Ref.",
    "AreaDate": "วันที่ทำการสำรวจ (Survey Date)",
    "CustomProfile": "Custom Profile",
    "Profile": "Profile",
    "FlowCalcTable": "FLOW CAL. TABLE",
    "Status": "Status",
    "Remark": "Remark",
}

AreaFormTab = {
    "main": "Main",
    "configures": "Configures",
}

AreaConfigures = [
    {
        "title": AreaField["CustomProfile"],
        "fields": {
            "CustomProfile": {
                "title": "Custom Profile",
                "placeholder": "",
                "table": True,
                "headers": ["x-axis", "y-axis"],
                "columns": ["x", "y"],
                "align": "start",
            },
        },
    },
    {
        "title": AreaField["Profile"],
        "fields": {
            "Profile": {
                "title": "Profile",
                "placeholder": "",
                "table": True,
                "headers": ["Water Level (before convert) [m]", "Area [m²]"],
                "columns": ["WaterLevel", "Area"],
                "align": "start",
            },
        },
    },
    {
        "title": AreaField["FlowCalcTable"],
        "fields": {
            "FlowCalcTable": {
                "title": "Custom Profile",
                "placeholder": "",
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
    "Port": "Port",
    "Username": "Username",
    "Password": "Password",
    "ChannelsID": "Channels ID",
    "FPS": "FPS",
    "Onvif": "Onvif (ONVIF Profile G Specification )",
    "Onvif_IP": "Onvif IP",
    "Onvif_Port": "Port",
    "Onvif_UserName": "Username",
    "Onvif_Password": "Password",
    "Status": "Status",
    "Remark": "Remark",
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
            "Password": {"title": "Password", "placeholder": ""},
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
            "CameraConfigures": {
                "title": "Camera Configures",
                "placeholder": "",
                "table": True,
                "headers": ["x-axis", "y-axis"],
                "columns": ["x", "y"],
                "align": "start",
            },
        },
    },
]

TeamField = {
    "TeamID": "TeamID",
    "TeamName": "Team Name",
    "RiverBasins": "Watersheds",
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
    "Check": '<i class="bi bi-check-circle"></i>',
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
