# app/routes/sse_routes.py
import time
import json
import queue
from flask import Blueprint, Response, request, jsonify
from flask_login import current_user
from app.services.sse_service import sse_manager
from app.logging_config import get_logger

logger = get_logger(__name__)

sse_bp = Blueprint("sse_bp", __name__)


@sse_bp.route("/stream")
def stream():
    """SSE endpoint for clients to receive real-time updates."""
    client_queue = queue.Queue(maxsize=10)

    # Get user ID if authenticated
    user_id = current_user.id if current_user.is_authenticated else None

    sse_manager.add_client(client_queue, user_id=user_id)

    def event_stream():
        try:
            while True:
                data = client_queue.get()  # Blocks until data is available
                json_data = json.dumps(data)
                yield f"data: {json_data}\n\n"
        except GeneratorExit:
            # Client disconnected
            sse_manager.remove_client(client_queue, user_id=user_id)
            logger.debug(f"SSE stream closed by client (user_id: {user_id})")

    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )


@sse_bp.route("/broadcast", methods=["POST"])
def broadcast():
    """
    Broadcast a message to all SSE clients.
    Example JSON: {"message": "System update complete", "type": "success"}
    """
    data = request.get_json()
    message = data.get("message", "")
    alert_type = data.get("type", "info")

    if not message:
        return jsonify({"error": "Message required"}), 400

    sse_manager.broadcast_alert(message, alert_type)
    return jsonify({"status": "Message broadcasted"}), 200


def redirect_user():
    """
    Redirect a specific user to a page.
    Example JSON: {"user_id": 123, "endpoint": "auth.login"}
    """
    data = request.get_json()
    user_id = data.get("user_id")
    endpoint = data.get("endpoint")

    if not user_id or not endpoint:
        return jsonify({"error": "user_id and endpoint required"}), 400

    # Build url_for kwargs
    url_kwargs = {}
    if data.get("external"):
        url_kwargs["_external"] = True
    if "params" in data:
        url_kwargs.update(data["params"])

    try:
        sse_manager.redirect_user(user_id, endpoint, **url_kwargs)
        return jsonify({"status": "Redirect sent to user", "user_id": user_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
