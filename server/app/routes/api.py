"""
API routes for client communication

All Routes in this file will be in relation to communication with scanning clients
"""

import logging
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import and_, or_
from sqlalchemy.exc import SQLAlchemyError
from app import db
from app.models.client import Client
from app.models.scan import Scan
from app.models.scan_task import ScanTask
from app.models.scan_result import ScanResult
import uuid
import json

bp = Blueprint("api", __name__)

logger = logging.getLogger(__name__)

# ============== CLIENT CRUD OPERATIONS ==============


@bp.route("/clients/register", methods=["POST"])
def register_client():
    """Register a new client or update existing one"""
    try:
        data = request.get_json()
        client_id = data.get("client_id")  # MAC address
        hostname = data.get("hostname")
        ip_address = data.get("ip_address")
        port = data.get("port")
        scan_range = data.get("scan_range")

        if not client_id:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "client_id (MAC address) is required",
                    }
                ),
                400,
            )

        # Check if client exists
        client = Client.query.filter_by(client_id=client_id).first()

        if client:
            # Update existing client
            client.hostname = hostname or client.hostname
            client.ip_address = ip_address or client.ip_address
            client.port = port or client.port
            client.scan_range = scan_range
            client.last_seen = datetime.utcnow()

            # Only mark online if approved
            if client.approved:
                client.mark_online()
                message = "Client updated successfully"
            else:
                message = "Client updated but awaiting approval"
        else:
            # Create new client (pending approval)
            client = Client(
                client_id=client_id,
                hostname=hostname,
                ip_address=ip_address,
                port=port,
                scan_range=scan_range,
                status="offline",
                last_seen=datetime.utcnow(),
                approved=False,  # New clients require approval
            )
            db.session.add(client)
            message = "Client registered successfully - awaiting approval"

        db.session.commit()

        return (
            jsonify(
                {
                    "status": "success",
                    "message": message,
                    "client": client.to_dict(),
                    "approved": client.approved,
                }
            ),
            200,
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Client registration failed: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/clients/<client_id>", methods=["GET"])
def get_client(client_id):
    """Get details of a specific client"""
    try:
        client = Client.query.filter_by(client_id=client_id).first()

        if not client:
            return jsonify({"status": "error", "message": "Client not found"}), 404

        # Include recent activity
        recent_tasks = (
            ScanTask.query.filter_by(client_id=client_id)
            .order_by(ScanTask.created_at.desc())
            .limit(10)
            .all()
        )

        return (
            jsonify(
                {
                    "status": "success",
                    "client": client.to_dict(),
                    "recent_tasks": [task.to_dict() for task in recent_tasks],
                }
            ),
            200,
        )

    except Exception as e:
        current_app.logger.error(f"Failed to get client: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/clients/<client_id>", methods=["PUT"])
def update_client(client_id):
    """Update client information"""
    try:
        client = Client.query.filter_by(client_id=client_id).first()

        if not client:
            return jsonify({"status": "error", "message": "Client not found"}), 404

        data = request.get_json()

        # Update allowed fields
        if "hostname" in data:
            client.hostname = data["hostname"]
        if "ip_address" in data:
            client.ip_address = data["ip_address"]
        if "status" in data and data["status"] in ["online", "offline", "scanning"]:
            # Only allow status changes if approved
            if client.approved or data["status"] == "offline":
                client.status = data["status"]

        client.last_seen = datetime.utcnow()
        db.session.commit()

        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Client updated successfully",
                    "client": client.to_dict(),
                }
            ),
            200,
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to update client: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/clients/<client_id>", methods=["DELETE"])
def delete_client(client_id):
    """Delete a client (soft delete by marking as inactive)"""
    try:
        client = Client.query.filter_by(client_id=client_id).first()

        if not client:
            return jsonify({"status": "error", "message": "Client not found"}), 404

        # Mark as offline instead of deleting (preserve history)
        client.mark_offline()
        db.session.commit()

        return (
            jsonify({"status": "success", "message": "Client marked as offline"}),
            200,
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to delete client: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/clients/<client_id>/heartbeat", methods=["POST"])
def client_heartbeat(client_id):
    """Update client heartbeat to maintain online status"""
    try:
        client = Client.query.filter_by(client_id=client_id).first()

        if not client:
            # Auto-register if not found (pending approval)
            data = request.get_json() or {}
            client = Client(
                client_id=client_id,
                hostname=data.get("hostname", "Unknown"),
                ip_address=data.get("ip_address", request.remote_addr),
                status="offline",
                approved=False,
            )
            db.session.add(client)
            db.session.commit()

            return (
                jsonify(
                    {
                        "status": "pending_approval",
                        "message": "Client registered but requires approval",
                        "approved": False,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                ),
                403,
            )

        # Check if client is approved
        if not client.approved:
            client.last_seen = datetime.utcnow()
            db.session.commit()

            return (
                jsonify(
                    {
                        "status": "pending_approval",
                        "message": "Client is not approved yet",
                        "approved": False,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                ),
                403,
            )

        # Client is approved - update heartbeat
        client.last_seen = datetime.utcnow()
        client.mark_online()

        # Update IP if changed
        data = request.get_json() or {}
        if "ip_address" in data:
            client.ip_address = data["ip_address"]

        db.session.commit()

        return (
            jsonify(
                {
                    "status": "success",
                    "approved": True,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
            200,
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Heartbeat failed: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ============== CLIENT APPROVAL ENDPOINTS ==============


@bp.route("/clients/<client_id>/approve", methods=["POST"])
@login_required
def approve_client(client_id):
    """Approve a client (requires login)"""
    try:
        client = Client.query.filter_by(client_id=client_id).first()

        if not client:
            return jsonify({"status": "error", "message": "Client not found"}), 404

        if client.approved:
            return (
                jsonify({"status": "success", "message": "Client is already approved"}),
                200,
            )

        # Approve the client
        client.approve(approved_by_user_id=current_user.id)

        logger.info(f"Client {client_id} approved by user {current_user.username}")

        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Client approved successfully",
                    "client": client.to_dict(),
                }
            ),
            200,
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to approve client: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/clients/<client_id>/revoke", methods=["POST"])
@login_required
def revoke_client_approval(client_id):
    """Revoke client approval (requires login)"""
    try:
        client = Client.query.filter_by(client_id=client_id).first()

        if not client:
            return jsonify({"status": "error", "message": "Client not found"}), 404

        if not client.approved:
            return (
                jsonify({"status": "success", "message": "Client is not approved"}),
                200,
            )

        # Revoke approval
        client.revoke_approval()

        logger.info(
            f"Client {client_id} approval revoked by user {current_user.username}"
        )

        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Client approval revoked successfully",
                    "client": client.to_dict(),
                }
            ),
            200,
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to revoke client approval: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ============== SCAN RESULTS ==============


@bp.route("/clients/<client_id>/results", methods=["POST"])
def receive_scan_results(client_id):
    """
    Receive structured scan results from client agents

    Expected payload structure:
    {
        "id": "result_789",
        "scan_id": "scan_123",
        "task_id": "task_456",
        "status": "completed",
        "scan_duration": 45.2,
        "parsed_results": {
            "192.168.1.1": {
                "hostname": "router.local",
                "state": "up",
                "open_ports": [53, 80, 443],
                "port_details": {
                    "53": {"protocol": "tcp", "name": "domain", "product": "", ...},
                    "80": {"protocol": "tcp", "name": "http", "product": "nginx", ...}
                }
            },
            ...
        },
        "summary_stats": {
            "total_targets": 10,
            "scanned_targets": 10,
            "targets_up": 8,
            "targets_down": 2,
            "error_targets": 0,
            "total_open_ports": 45
        },
        "error_message": null,
        "timestamp": "2025-10-07T12:34:56"
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        # Validate required fields
        required_fields = [
            "task_id",
            "result_id",
            "status",
            "parsed_results",
            "summary_stats",
        ]
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            return (
                jsonify(
                    {
                        "error": "Missing required fields",
                        "missing_fields": missing_fields,
                    }
                ),
                400,
            )

        result_id = data["result_id"]
        task_id = data["task_id"]

        # Check if result already exists
        scan_result = ScanResult.query.filter_by(id=result_id).first()

        if not scan_result:
            logger.warning(f"Error: Scan result {result_id} not found")
            return jsonify({"error": "Scan result not found"}), 404

        # Store the parsed results directly
        scan_result.parsed_results = data["parsed_results"]

        # Update summary statistics from client
        summary_stats = data["summary_stats"]
        scan_result.total_targets = summary_stats.get("total_targets", 0)
        scan_result.completed_targets = summary_stats.get(
            "scanned_targets", 0
        )  # Successfully scanned (up or down)
        scan_result.failed_targets = summary_stats.get(
            "error_targets", 0
        )  # Only actual errors
        scan_result.total_open_ports = summary_stats.get("total_open_ports", 0)

        # Track contributing clients
        if not scan_result.contributing_clients:
            scan_result.contributing_clients = []

        if client_id not in scan_result.contributing_clients:
            scan_result.contributing_clients.append(client_id)

        # Update timestamps
        if not scan_result.started_at:
            scan_result.started_at = datetime.utcnow()

        if data["status"] == "completed":
            # Update associated task if exists
            task = ScanTask.query.filter_by(task_id=task_id).first()

            if task:
                task.complete()
            from app import websocket_service

            websocket_service.broadcast_alert(
                f"Scan task {task_id} completed by client {client_id}",
                "info",
            )
        elif data["status"] == "failed":
            # scan_result.mark_failed() TODO only make scan_result failed if all tasks fail otherwise it should be partial do this inside task.mark_failed()
            # Update associated task
            task = ScanTask.query.filter_by(task_id=task_id).first()
            if task:
                task.mark_failed()

        scan_result.updated_at = datetime.utcnow()

        db.session.commit()

        logger.info(
            f"Received results from {client_id} for result {result_id}: "
            f"{scan_result.completed_targets}/{scan_result.total_targets} targets, "
            f"{scan_result.total_open_ports} open ports"
        )

        return (
            jsonify(
                {
                    "message": "Scan results received successfully",
                    "result_id": result_id,
                    "summary": {
                        "total_targets": scan_result.total_targets,
                        "completed_targets": scan_result.completed_targets,
                        "failed_targets": scan_result.failed_targets,
                        "total_open_ports": scan_result.total_open_ports,
                        "contributing_clients": len(scan_result.contributing_clients),
                    },
                }
            ),
            200,
        )

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error receiving scan results: {e}")
        return jsonify({"error": "Database error", "details": str(e)}), 500

    except Exception as e:
        logger.error(f"Error receiving scan results: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


# ============== HEALTH & MONITORING ==============


@bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint with system stats"""
    try:
        # Count active clients (seen in last 5 minutes)
        threshold = datetime.utcnow() - timedelta(minutes=5)
        active_clients = Client.query.filter(Client.last_seen >= threshold).count()

        # Count pending tasks
        pending_tasks = ScanTask.query.filter_by(status="pending").count()
        running_tasks = ScanTask.query.filter_by(status="running").count()

        return (
            jsonify(
                {
                    "status": "healthy",
                    "timestamp": datetime.utcnow().isoformat(),
                    "version": "1.0.0",
                    "stats": {
                        "active_clients": active_clients,
                        "pending_tasks": pending_tasks,
                        "running_tasks": running_tasks,
                    },
                }
            ),
            200,
        )

    except Exception as e:
        return (
            jsonify(
                {
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
            500,
        )


@bp.route("/stats", methods=["GET"])
def get_statistics():
    """Get system statistics"""
    try:
        # Time range (last 24 hours by default)
        hours = int(request.args.get("hours", 24))
        since = datetime.utcnow() - timedelta(hours=hours)

        stats = {
            "clients": {
                "total": Client.query.count(),
                "online": Client.query.filter_by(status="online").count(),
                "scanning": Client.query.filter_by(status="scanning").count(),
                "offline": Client.query.filter_by(status="offline").count(),
            },
            "tasks": {
                "total": ScanTask.query.filter(ScanTask.created_at >= since).count(),
                "pending": ScanTask.query.filter_by(status="pending").count(),
                "running": ScanTask.query.filter_by(status="running").count(),
                "completed": ScanTask.query.filter(
                    and_(ScanTask.status == "completed", ScanTask.completed_at >= since)
                ).count(),
                "failed": ScanTask.query.filter(
                    and_(ScanTask.status == "failed", ScanTask.completed_at >= since)
                ).count(),
            },
            "scans": {
                "total": ScanResult.query.filter(
                    ScanResult.created_at >= since
                ).count(),
                "completed": ScanResult.query.filter(
                    and_(
                        ScanResult.status == "completed", ScanResult.created_at >= since
                    )
                ).count(),
                "failed": ScanResult.query.filter(
                    and_(ScanResult.status == "failed", ScanResult.created_at >= since)
                ).count(),
            },
        }

        return (
            jsonify(
                {
                    "status": "success",
                    "period_hours": hours,
                    "since": since.isoformat(),
                    "stats": stats,
                }
            ),
            200,
        )

    except Exception as e:
        current_app.logger.error(f"Failed to get statistics: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
