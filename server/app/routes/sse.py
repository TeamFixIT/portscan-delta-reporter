# app/routes/sse_routes.py
import time
import json
import queue
from flask import Blueprint, Response, request, jsonify
from app.services.sse_service import sse_manager
from app.logging_config import get_logger

logger = get_logger(__name__)

sse_bp = Blueprint("sse_bp", __name__)


@sse_bp.route("/stream")
def stream():
    """SSE endpoint for clients to receive real-time updates."""
    client_queue = queue.Queue(maxsize=10)
    sse_manager.add_client(client_queue)

    def event_stream():
        try:
            while True:
                data = client_queue.get()  # Blocks until data is available
                json_data = json.dumps(data)
                yield f"data: {json_data}\n\n"
        except GeneratorExit:
            # Client disconnected
            sse_manager.remove_client(client_queue)
            logger.debug("SSE stream closed by client")

    # Important SSE headers
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


@sse_bp.route("/client_count")
def client_count():
    """Returns number of connected clients"""
    count = sse_manager.get_client_count()
    return jsonify({"clients": count})
