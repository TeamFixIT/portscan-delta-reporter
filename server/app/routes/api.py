"""
API routes for client communication
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import and_, or_
from app import db
from app.models.client import Client
from app.models.scan import Scan
from app.models.scan_task import ScanTask
from app.models.scan_result import ScanResult
import uuid
import json

bp = Blueprint("api", __name__)

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


# ============== TASK MANAGEMENT ==============


@bp.route("/scan-tasks/<client_id>", methods=["GET"])
def get_scan_tasks(client_id):
    """Get pending scan tasks for a client"""
    try:
        # Update client last seen
        client = Client.query.filter_by(client_id=client_id).first()
        if client:
            client.last_seen = datetime.utcnow()
            client.mark_online()
            db.session.commit()

        # Get next pending task for this client
        task = (
            ScanTask.query.filter(
                and_(
                    or_(
                        ScanTask.client_id == client_id,
                        ScanTask.client_id == None,  # Unassigned tasks
                    ),
                    ScanTask.status == "pending",
                )
            )
            .order_by(ScanTask.priority.desc(), ScanTask.created_at.asc())
            .first()
        )

        if task:
            # Assign task to client if not already assigned
            if not task.client_id:
                task.assign_to_client(client_id)
                db.session.commit()

            # Get associated scan for additional context
            scan = None
            if hasattr(task, "scan_id"):
                scan = Scan.query.get(task.scan_id)

            response_data = {
                "scan_id": task.task_id,
                "targets": (
                    task.targets if isinstance(task.targets, list) else [task.targets]
                ),
                "ports": task.ports,
                "scan_type": task.scan_type,
                "timeout": 300,  # Default timeout
                "priority": task.priority,
            }

            # Add scan metadata if available
            if scan:
                response_data["scan_name"] = scan.name
                response_data["scan_arguments"] = scan.scan_arguments

            return jsonify(response_data), 200

        # No tasks available
        return jsonify({}), 204  # No Content

    except Exception as e:
        current_app.logger.error(f"Failed to get scan tasks: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/scan-tasks", methods=["POST"])
def create_scan_task():
    """Create a new scan task"""
    try:
        data = request.get_json()

        # Generate task ID
        task_id = str(uuid.uuid4())

        # Create scan task
        task = ScanTask(
            task_id=task_id,
            targets=data.get("targets", []),
            ports=data.get("ports", "1-1000"),
            scan_type=data.get("scan_type", "tcp"),
            priority=data.get("priority", 1),
            status="pending",
            client_id=data.get("client_id"),  # Optional pre-assignment
        )

        db.session.add(task)
        db.session.commit()

        return (
            jsonify({"status": "success", "task_id": task_id, "task": task.to_dict()}),
            201,
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to create scan task: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ============== SCAN RESULTS ==============


@bp.route("/scan-results", methods=["POST"])
def receive_scan_results():
    """Receive scan results from clients (supports partial updates)"""
    try:
        data = request.get_json()
        # Extract data
        scan_id = data.get("scan_id")
        client_id = data.get("client_id")
        task_id = data.get("task_id")
        status = data.get("status")  # 'in_progress', 'completed', 'failed'

        if not scan_id or not client_id:
            return (
                jsonify(
                    {"status": "error", "message": "scan_id and client_id are required"}
                ),
                400,
            )

        # Update client status
        client = Client.query.filter_by(client_id=client_id).first()
        if client:
            client.last_seen = datetime.utcnow()
            if status == "in_progress":
                client.mark_scanning()
            elif status in ["completed", "failed"]:
                client.mark_online()

        # Find or create scan result
        scan_result = (
            ScanResult.query.filter_by(scan_id=scan_id)
            .filter(ScanResult.status.in_(["running", "pending"]))
            .first()
        )

        if not scan_result:
            # Create new scan result
            scan_result = ScanResult(
                scan_id=scan_id,
                client_id=client_id,
                status="running",
                start_time=datetime.fromisoformat(
                    data.get("timestamp", datetime.utcnow().isoformat())
                ),
                results_data={},
            )
            db.session.add(scan_result)

        # Update scan result based on status
        if status == "in_progress":
            # Partial update - merge results
            existing_data = scan_result.results_data or {}
            new_data = data.get("partial_results", {})

            # Merge open_ports if provided
            if "open_ports" in data:
                target = data.get("target")
                if target:
                    if "hosts" not in existing_data:
                        existing_data["hosts"] = {}
                    if target not in existing_data["hosts"]:
                        existing_data["hosts"][target] = {"ports": []}

                    # Add new ports (avoid duplicates)
                    existing_ports = {
                        p["port"]
                        for p in existing_data["hosts"][target].get("ports", [])
                    }
                    for port_info in data["open_ports"]:
                        if port_info["port"] not in existing_ports:
                            existing_data["hosts"][target]["ports"].append(port_info)

            scan_result.results_data = existing_data

        elif status == "completed":
            # Prepare results_data for mark_completed
            results_data = scan_result.results_data or {}
            if "open_ports" in data:
                target = data.get("target")
                if target:
                    if "hosts" not in results_data:
                        results_data["hosts"] = {}
                    # Merge ports if host already exists
                    existing_ports = []
                    if target in results_data["hosts"]:
                        existing_ports = results_data["hosts"][target].get("ports", [])
                    # Avoid duplicates by port number
                    new_ports = data["open_ports"]
                    existing_port_nums = {p["port"] for p in existing_ports}
                    merged_ports = existing_ports + [
                        p for p in new_ports if p["port"] not in existing_port_nums
                    ]
                    results_data["hosts"][target] = {
                        "ports": merged_ports,
                        "status": "up",
                    }
            scan_result.mark_completed(results_data)
            # Update associated task if exists
            task = ScanTask.query.filter_by(task_id=task_id).first()

            if task:
                task.complete()

        elif status == "failed":
            # Mark as failed
            scan_result.mark_failed(data.get("error_message", "Unknown error"))

            # Update associated task
            task = ScanTask.query.filter_by(task_id=task_id).first()
            if task:
                task.mark_failed()

        db.session.commit()

        return (
            jsonify(
                {
                    "status": "success",
                    "message": f"Result received ({status})",
                    "scan_id": scan_id,
                }
            ),
            200,
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to process scan result: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/scan-results/<scan_id>/progress", methods=["GET"])
def get_scan_progress(scan_id):
    """Get current progress of a scan"""
    try:
        result = ScanResult.query.filter_by(scan_id=scan_id).first()

        if not result:
            return jsonify({"status": "error", "message": "Scan not found"}), 404

        # Calculate progress
        total_hosts = 1  # Could be extracted from task
        scanned_hosts = (
            len(result.results_data.get("hosts", {})) if result.results_data else 0
        )
        progress = (scanned_hosts / total_hosts) * 100 if total_hosts > 0 else 0

        return (
            jsonify(
                {
                    "status": "success",
                    "scan_id": scan_id,
                    "scan_status": result.status,
                    "progress": progress,
                    "hosts_scanned": scanned_hosts,
                    "ports_found": result.ports_found or 0,
                    "start_time": (
                        result.start_time.isoformat() if result.start_time else None
                    ),
                    "duration": result.duration_seconds,
                }
            ),
            200,
        )

    except Exception as e:
        current_app.logger.error(f"Failed to get scan progress: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


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
