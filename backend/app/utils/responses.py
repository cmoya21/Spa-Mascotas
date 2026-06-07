from flask import jsonify


def success(data=None, message=None, status=200):
    payload = {"success": True}
    if message:
        payload["message"] = message
    if data is not None:
        payload["data"] = data
    return jsonify(payload), status


def error(message, status=400, code=None, details=None):
    payload = {"success": False, "message": message}
    if code:
        payload["code"] = code
    if details:
        payload["details"] = details
    return jsonify(payload), status
