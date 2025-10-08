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
            client.scan_range = scan_range
            client.last_seen = datetime.utcnow()
            client.mark_online()
            message = "Client updated successfully"
        else:
            # Create new client
            client = Client(
                client_id=client_id,
                hostname=hostname,
                ip_address=ip_address,
                scan_range=scan_range,
                status="online",
                last_seen=datetime.utcnow(),
            )
            db.session.add(client)
            message = "Client registered successfully"

        db.session.commit()

        return (
            jsonify(
                {"status": "success", "message": message, "client": client.to_dict()}
            ),
            200,
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Client registration failed: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/clients", methods=["GET"])
def list_clients():
    """List all registered clients with optional filtering"""
    try:
        # Optional query parameters
        status = request.args.get("status")  # online, offline, scanning
        active_only = request.args.get("active_only", "false").lower() == "true"

        query = Client.query

        if status:
            query = query.filter_by(status=status)

        if active_only:
            # Consider clients active if seen in last 5 minutes
            threshold = datetime.utcnow() - timedelta(minutes=5)
            query = query.filter(Client.last_seen >= threshold)

        clients = query.order_by(Client.last_seen.desc()).all()

        return (
            jsonify(
                {
                    "status": "success",
                    "count": len(clients),
                    "clients": [client.to_dict() for client in clients],
                }
            ),
            200,
        )

    except Exception as e:
        current_app.logger.error(f"Failed to list clients: {str(e)}")
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
            # Auto-register if not found
            data = request.get_json() or {}
            client = Client(
                client_id=client_id,
                hostname=data.get("hostname", "Unknown"),
                ip_address=data.get("ip_address", request.remote_addr),
                status="online",
            )
            db.session.add(client)

        client.last_seen = datetime.utcnow()
        client.mark_online()

        # Update IP if changed
        data = request.get_json() or {}
        if "ip_address" in data:
            client.ip_address = data["ip_address"]

        db.session.commit()

        return (
            jsonify({"status": "success", "timestamp": datetime.utcnow().isoformat()}),
            200,
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Heartbeat failed: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ============== SCAN RESULTS ==============


@bp.route("/scan-results", methods=["POST"])
def receive_scan_results():
    """
    Receive structured scan results from client agents

    Expected payload structure:
    {
        "scan_id": "scan_123",
        "task_id": "task_456",
        "result_id": "result_789",
        "client_id": "client_001",
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
            "client_id",
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
        client_id = data["client_id"]
        task_id = data["task_id"]

        # Check if result already exists
        scan_result = ScanResult.query.filter_by(result_id=result_id).first()

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
            scan_result.mark_complete()
            # Update associated task if exists
            task = ScanTask.query.filter_by(task_id=task_id).first()

            if task:
                task.complete()
        elif data["status"] == "failed":
            scan_result.mark_failed()
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


@bp.route("/scan-results/<result_id>", methods=["GET"])
def get_scan_result(result_id):
    """Get a specific scan result by ID"""
    try:
        scan_result = ScanResult.query.filter_by(result_id=result_id).first()

        if not scan_result:
            return jsonify({"error": "Scan result not found"}), 404

        return (
            jsonify(
                {
                    "result_id": scan_result.result_id,
                    "scan_id": scan_result.scan_id,
                    "parsed_results": scan_result.parsed_results,
                    "summary": {
                        "total_targets": scan_result.total_targets,
                        "completed_targets": scan_result.completed_targets,
                        "failed_targets": scan_result.failed_targets,
                        "total_open_ports": scan_result.total_open_ports,
                    },
                    "contributing_clients": scan_result.contributing_clients,
                    "timestamps": {
                        "created_at": (
                            scan_result.created_at.isoformat()
                            if scan_result.created_at
                            else None
                        ),
                        "started_at": (
                            scan_result.started_at.isoformat()
                            if scan_result.started_at
                            else None
                        ),
                        "completed_at": (
                            scan_result.completed_at.isoformat()
                            if scan_result.completed_at
                            else None
                        ),
                        "updated_at": (
                            scan_result.updated_at.isoformat()
                            if scan_result.updated_at
                            else None
                        ),
                    },
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error retrieving scan result: {e}")
        return jsonify({"error": "Internal server error"}), 500


@bp.route("/scan-results/<result_id>/targets", methods=["GET"])
def get_scan_result_targets(result_id):
    """Get detailed target information from a scan result"""
    try:
        scan_result = ScanResult.query.filter_by(result_id=result_id).first()

        if not scan_result:
            return jsonify({"error": "Scan result not found"}), 404

        # Optional filters
        state_filter = request.args.get("state")  # 'up', 'down', 'error'
        min_ports = request.args.get("min_ports", type=int)  # Minimum open ports

        parsed_results = scan_result.parsed_results or {}
        filtered_results = {}

        for target, data in parsed_results.items():
            # Apply filters
            if state_filter and data.get("state") != state_filter:
                continue

            if min_ports and len(data.get("open_ports", [])) < min_ports:
                continue

            filtered_results[target] = data

        return (
            jsonify(
                {
                    "result_id": result_id,
                    "total_results": len(parsed_results),
                    "filtered_results": len(filtered_results),
                    "targets": filtered_results,
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error retrieving target results: {e}")
        return jsonify({"error": "Internal server error"}), 500


@bp.route("/scan-results/<result_id>/summary", methods=["GET"])
def get_scan_result_summary(result_id):
    """Get a quick summary of scan results"""
    try:
        scan_result = ScanResult.query.filter_by(result_id=result_id).first()

        if not scan_result:
            return jsonify({"error": "Scan result not found"}), 404

        # Calculate additional statistics
        parsed_results = scan_result.parsed_results or {}

        # Top services found
        service_counts = {}
        port_counts = {}

        for target, data in parsed_results.items():
            port_details = data.get("port_details", {})
            for port, details in port_details.items():
                service_name = details.get("name", "unknown")
                service_counts[service_name] = service_counts.get(service_name, 0) + 1
                port_counts[port] = port_counts.get(port, 0) + 1

        # Sort and get top 10
        top_services = sorted(service_counts.items(), key=lambda x: x[1], reverse=True)[
            :10
        ]
        top_ports = sorted(port_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        return (
            jsonify(
                {
                    "result_id": result_id,
                    "summary": {
                        "total_targets": scan_result.total_targets,
                        "completed_targets": scan_result.completed_targets,
                        "failed_targets": scan_result.failed_targets,
                        "total_open_ports": scan_result.total_open_ports,
                        "unique_services": len(service_counts),
                        "unique_ports": len(port_counts),
                    },
                    "top_services": [
                        {"name": name, "count": count} for name, count in top_services
                    ],
                    "top_ports": [
                        {"port": port, "count": count} for port, count in top_ports
                    ],
                    "contributing_clients": scan_result.contributing_clients,
                    "duration": {
                        "started_at": (
                            scan_result.started_at.isoformat()
                            if scan_result.started_at
                            else None
                        ),
                        "completed_at": (
                            scan_result.completed_at.isoformat()
                            if scan_result.completed_at
                            else None
                        ),
                    },
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error generating scan summary: {e}")
        return jsonify({"error": "Internal server error"}), 500


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
