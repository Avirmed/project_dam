import os

from flask import (
    Blueprint,
    render_template,
    request,
    url_for,
    jsonify,
    abort,
    send_from_directory,
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from util import statictext

ckfinder_bp = Blueprint("ckfinder_bp", __name__)

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "bmp", "svg", "webp"}
ALLOWED_FILE_EXTENSIONS = {
    "pdf",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "ppt",
    "pptx",
    "txt",
    "rtf",
    "zip",
    "rar",
    "7z",
    "tar",
    "gz",
    "py",
    "js",
    "html",
    "css",
    "json",
    "xml",
    "csv",
    "mp3",
    "wav",
    "ogg",
    "mp4",
    "avi",
    "mov",
    "wmv",
    "jpg",
    "jpeg",
    "png",
    "gif",
    "bmp",
    "svg",
    "webp",
}


def get_user_path(base_folder):
    user_id = str(current_user.get_id())
    path = os.path.join(base_folder, user_id)
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    return path, user_id


def allowed_image(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS
    )


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_FILE_EXTENSIONS
    )


def human_readable_size(file_path):
    size_bytes = os.path.getsize(file_path)
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


@ckfinder_bp.route("/")
def index():
    error_code = 400
    abort(error_code, description=statictext.ResponseCode[error_code])


@ckfinder_bp.route("/browse/images")
@login_required
def browse_images():
    func_num = request.args.get("CKEditorFuncNum", 1)
    user_path, user_id = get_user_path(statictext.UPLOAD_CK_FOLDER_IMAGE)

    files = [f for f in os.listdir(user_path) if allowed_image(f)]
    files_url = [
        url_for("ckfinder_bp.uploaded_file", filename=f"images/{user_id}/{f}")
        for f in files
    ]
    files_and_urls = list(zip(files, files_url))

    return render_template(
        "ckfinder/browse_images.html",
        files_and_urls=files_and_urls,
        func_num=func_num,
        StaticText=statictext,
    )


@ckfinder_bp.route("/browse/files")
@login_required
def browse_files():
    func_num = request.args.get("CKEditorFuncNum", 1)
    user_path, user_id = get_user_path(statictext.UPLOAD_CK_FOLDER_FILE)

    files = [f for f in os.listdir(user_path) if allowed_file(f)]

    files_and_urls = []
    for f in files:
        file_path = os.path.join(user_path, f)
        url = url_for("ckfinder_bp.uploaded_file", filename=f"files/{user_id}/{f}")
        size = human_readable_size(file_path)
        files_and_urls.append((f, url, size))

    return render_template(
        "ckfinder/browse_files.html",
        files_and_urls=files_and_urls,
        func_num=func_num,
        StaticText=statictext,
    )


@ckfinder_bp.route("/upload/image", methods=["POST"])
@login_required
def upload_image():
    if "upload" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["upload"]
    if file.filename == "" or not allowed_image(file.filename):
        return jsonify({"error": "Invalid file"}), 400

    user_path, user_id = get_user_path(statictext.UPLOAD_CK_FOLDER_IMAGE)
    filename = secure_filename(file.filename)
    file.save(os.path.join(user_path, filename))

    func_num = request.args.get("CKEditorFuncNum")
    url = url_for("ckfinder_bp.uploaded_file", filename=f"images/{user_id}/{filename}")
    return f"<script>window.parent.CKEDITOR.tools.callFunction({func_num}, '{url}', 'Upload successful');</script>"


@ckfinder_bp.route("/upload/file", methods=["POST"])
@login_required
def upload_file():
    if "upload" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["upload"]
    if file.filename == "" or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file"}), 400

    user_path, user_id = get_user_path(statictext.UPLOAD_CK_FOLDER_FILE)
    filename = secure_filename(file.filename)
    file.save(os.path.join(user_path, filename))

    func_num = request.args.get("CKEditorFuncNum")
    url = url_for("ckfinder_bp.uploaded_file", filename=f"files/{user_id}/{filename}")
    return f"<script>window.parent.CKEDITOR.tools.callFunction({func_num}, '{url}', 'Upload successful');</script>"


@ckfinder_bp.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename):
    # filename жишээ: images/1/pic.jpg
    parts = filename.split("/")
    if len(parts) < 3:
        abort(404)

    folder_type = parts[0]
    user_id = parts[1]
    actual_name = "/".join(parts[2:])

    if user_id != str(current_user.get_id()):
        abort(403)

    base_dir = (
        statictext.UPLOAD_CK_FOLDER_IMAGE
        if folder_type == "images"
        else statictext.UPLOAD_CK_FOLDER_FILE
    )
    return send_from_directory(os.path.join(base_dir, user_id), actual_name)


@ckfinder_bp.route("/delete/file", methods=["POST"])
@login_required
def delete_file():
    filepath = request.form.get("filepath")  # images/1/pic.jpg
    if not filepath or filepath.count("/") < 2:
        return jsonify({"error": "Invalid path"}), 400

    parts = filepath.split("/")
    folder_type, user_id, filename = parts[0], parts[1], "/".join(parts[2:])

    if user_id != str(current_user.get_id()):
        return jsonify({"error": "Unauthorized"}), 403

    base_dir = (
        statictext.UPLOAD_CK_FOLDER_IMAGE
        if folder_type == "images"
        else statictext.UPLOAD_CK_FOLDER_FILE
    )
    abs_path = os.path.normpath(os.path.join(base_dir, user_id, filename))

    if os.path.exists(abs_path) and os.path.isfile(abs_path):
        try:
            os.remove(abs_path)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return jsonify({"error": "File not found"}), 404
