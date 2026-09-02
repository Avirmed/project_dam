from flask import Blueprint, request, jsonify

from models import StationData

inbound_bp = Blueprint("inbound_bp", __name__)


@inbound_bp.route("/<string:device_id>", methods=["POST"])
def receive(device_id):
    """Per-station REST API server entry point for field devices.

    No dashboard login: access is governed by the station's own REST API
    settings (status, source allow-list, authentication) inside
    StationData.ingest. Accepts a JSON object body (form-encoded is tolerated).
    """
    payload = request.get_json(silent=True)
    if payload is None and request.form:
        payload = request.form.to_dict()

    jsonResult = StationData.ingest(
        device_id, payload, request.remote_addr, request.scheme, request.headers
    )

    return jsonify(jsonResult), jsonResult["Code"]
