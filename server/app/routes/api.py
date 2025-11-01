"""
API routes for client communication

All Routes in this file will be in relation to communication with scanning clients
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timezone, timedelta
from sqlalchemy import and_, or_
from sqlalchemy.exc import SQLAlchemyError
from app import db
from app.models.client import Client
from app.models.scan import Scan
from app.models.scan_task import ScanTask
from app.models.scan_result import ScanResult
from app.services.sse_service import sse_manager

import uuid
import json

bp = Blueprint("api", __name__)

from app.logging_config import get_logger

logger = get_logger(__name__)

# ============== CLIENT CRUD OPERATIONS ==============


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
        logger.error(f"Failed to get client: {str(e)}")
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
            if client.is_approved or data["status"] == "offline":
                client.status = data["status"]

        client.last_seen = datetime.now(timezone.utc)
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
        logger.error(f"Failed to update client: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/clients/<client_id>/toggle", methods=["POST"])
def toggle_client(client_id):
    """Delete a client"""
    try:
        client = Client.query.filter_by(client_id=client_id).first()

        if not client:
            return jsonify({"status": "error", "message": "Client not found"}), 404

        # Mark as offline instead of deleting (preserve history)
        client.mark_offline()
        client.is_hidden = not client.is_hidden
        db.session.commit()
        logger.info(f"Client marked as offline: {client_id}")
        return (
            jsonify({"status": "success", "message": "Client marked as offline"}),
            200,
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to delete client: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/clients/<client_id>/heartbeat", methods=["POST"])
def client_heartbeat(client_id):
    """Handle client heartbeat - registers new clients and updates existing ones"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ["client_id", "hostname", "ip_address", "port", "scan_range"]
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

        client_id = data["client_id"]
        hostname = data["hostname"]
        ip_address = data["ip_address"]
        port = data["port"]
        scan_range = data["scan_range"]

        # Check if client exists
        client = Client.query.filter_by(client_id=client_id).first()

        if client:
            # Update existing client
            client.hostname = hostname or client.hostname
            client.ip_address = ip_address or client.ip_address
            client.port = port or client.port
            client.scan_range = scan_range
            client.last_seen = datetime.now(timezone.utc)

            # Check approval status and respond accordingly
            if not client.is_approved:
                message = "Client updated but awaiting approval"
                status_code = 403
            else:
                client.mark_online()
                message = "Client updated successfully"
                status_code = 200
        else:
            # Create new client (pending approval)
            client = Client(
                client_id=client_id,
                hostname=hostname,
                ip_address=ip_address,
                port=port,
                scan_range=scan_range,
                status="offline",
                last_seen=datetime.now(timezone.utc),
                is_approved=False,  # New clients require approval
            )
            db.session.add(client)
            message = f"New client registered: {client_id} ({ip_address})"
            status_code = 403  # Return 403 for unapproved clients

            logger.info(message)
            sse_manager.broadcast_alert(message, "info")

        db.session.commit()

        return (
            jsonify(
                {
                    "status": "success",
                    "message": message,
                    "approved": client.is_approved,
                }
            ),
            status_code,
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Heartbeat failed: {str(e)}")
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

        if client.is_approved:
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
        logger.error(f"Failed to approve client: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/clients/<client_id>/revoke", methods=["POST"])
@login_required
def revoke_client_approval(client_id):
    """Revoke client approval (requires login)"""
    try:
        client = Client.query.filter_by(client_id=client_id).first()

        if not client:
            return jsonify({"status": "error", "message": "Client not found"}), 404

        if not client.is_approved:
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
        logger.error(f"Failed to revoke client approval: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ============== SCAN RESULTS ==============


@bp.route("/clients/<client_id>/results", methods=["POST"])
def receive_scan_results(client_id):
    """
    Receive structured scan results from client agents and merge them into the existing ScanResult.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        # Validate required fields
        required_fields = ["result_id", "task_id", "status", "parsed_results"]
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

        # Check if result exists
        scan_result = ScanResult.query.filter_by(id=result_id).first()
        if not scan_result:
            logger.warning(f"Error: Scan result {result_id} not found")
            return jsonify({"error": "Scan result not found"}), 404
        # CRITICAL FIX: Create a deep copy to avoid reference issues
        existing_results = (
            dict(scan_result.parsed_results) if scan_result.parsed_results else {}
        )
        new_results = data.get("parsed_results", {})

        logger.info(
            f"Merging results from {client_id}: {len(new_results)} new IPs into {len(existing_results)} existing IPs"
        )

        # Merge strategy: Update or add IP entries, combine open_ports if needed
        for ip, new_data in new_results.items():
            if ip in existing_results:
                # Merge existing and new data for this IP
                existing_data = existing_results[ip]
                existing_data["hostname"] = new_data.get(
                    "hostname", existing_data.get("hostname", "")
                )
                existing_data["state"] = new_data.get(
                    "state", existing_data.get("state", "unknown")
                )

                # Combine open_ports (remove duplicates)
                existing_ports = set(existing_data.get("open_ports", []))
                new_ports = set(new_data.get("open_ports", []))
                existing_data["open_ports"] = sorted(list(existing_ports | new_ports))

                # Merge port_details
                existing_details = existing_data.get("port_details", {})
                new_details = new_data.get("port_details", {})
                existing_details.update(new_details)
                existing_data["port_details"] = existing_details

                logger.debug(f"Merged data for existing IP {ip}")
            else:
                # Add new IP entry (make a deep copy to avoid reference issues)
                existing_results[ip] = dict(new_data)
                logger.debug(f"Added new IP {ip}")

        scan_result.parsed_results = existing_results

        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(scan_result, "parsed_results")

        print(f"Final merged IPs: {list(existing_results.keys())}")
        logger.info(f"Total IPs after merge: {len(existing_results)}")

        # Recompute summary statistics based on parsed_results
        total_targets = len(existing_results)
        completed_targets = sum(
            1
            for ip, data in existing_results.items()
            if data.get("state") in ["up", "down"]
        )
        targets_up = sum(
            1 for ip, data in existing_results.items() if data.get("state") == "up"
        )
        targets_down = sum(
            1 for ip, data in existing_results.items() if data.get("state") == "down"
        )
        total_open_ports = sum(
            len(data.get("open_ports", [])) for ip, data in existing_results.items()
        )

        scan_result.total_targets = total_targets
        scan_result.completed_targets = completed_targets
        scan_result.failed_targets = data.get("summary_stats", {}).get(
            "error_targets", 0
        )
        scan_result.total_open_ports = total_open_ports

        # Track contributing clients
        if not scan_result.contributing_clients:
            scan_result.contributing_clients = []
        if client_id not in scan_result.contributing_clients:
            scan_result.contributing_clients.append(client_id)

        # Update timestamps
        if not scan_result.started_at:

            scan_result.started_at = datetime.now(timezone.utc)

        scan_result.updated_at = datetime.now(timezone.utc)

        # Update status and task
        task = ScanTask.query.filter_by(task_id=task_id).first()
        if data["status"] == "completed":
            if task:
                task.complete()

        elif data["status"] == "failed":
            if task:
                task.mark_failed()
                scan_result.status = "partial"

        # Update overall status
        all_tasks = ScanTask.query.filter_by(scan_id=scan_result.scan_id).all()
        if all(task.status == "completed" for task in all_tasks):
            scan_result.status = "completed"
            scan_result.completed_at = datetime.now(timezone.utc)
        elif any(task.status == "failed" for task in all_tasks):
            scan_result.status = "partial"

        from app.services.alert_service import check_for_critical_ports

        # Detect and update alerts for critical services
        created_alerts, resolved_alerts = check_for_critical_ports(
            result_id, existing_results
        )
        if created_alerts or resolved_alerts:
            logger.info(
                f"{len(created_alerts)} new alerts, {len(resolved_alerts)} resolved alerts processed."
            )
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
        threshold = datetime.now(timezone.utc) - timedelta(minutes=5)
        active_clients = Client.query.filter(Client.last_seen >= threshold).count()

        # Count pending tasks
        pending_tasks = ScanTask.query.filter_by(status="pending").count()
        running_tasks = ScanTask.query.filter_by(status="running").count()

        return (
            jsonify(
                {
                    "status": "healthy",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
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
                    "timestamp": datetime.now(timezone.utc).isoformat(),
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
        since = datetime.now(timezone.utc) - timedelta(hours=hours)

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
        logger.error(f"Failed to get statistics: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
