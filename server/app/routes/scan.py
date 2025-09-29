"""
API routes for scan management
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import and_, or_
from app import db
from app.models.scan import Scan
from app.models.scan_task import ScanTask
from app.models.scan_result import ScanResult
from app.models.client import Client
import uuid
import json

bp = Blueprint("scan", __name__)

# ============== SCAN CRUD OPERATIONS ==============


@bp.route("/scans", methods=["GET"])
@login_required
def list_scans():
    """List all scans for current user with optional filtering"""
    try:
        # Query parameters
        is_active = request.args.get("is_active")
        is_scheduled = request.args.get("is_scheduled")
        limit = request.args.get("limit", 50, type=int)
        offset = request.args.get("offset", 0, type=int)

        # Base query - filter by user unless admin
        if current_user.is_admin:
            query = Scan.query
        else:
            query = Scan.query.filter_by(user_id=current_user.id)

        # Apply filters
        if is_active is not None:
            query = query.filter_by(is_active=is_active.lower() == "true")
        if is_scheduled is not None:
            query = query.filter_by(is_scheduled=is_scheduled.lower() == "true")

        # Order by creation date (newest first)
        query = query.order_by(Scan.created_at.desc())

        # Get total count before pagination
        total = query.count()

        # Apply pagination
        scans = query.limit(limit).offset(offset).all()

        # Serialize with additional metadata
        scans_data = []
        for scan in scans:
            scan_dict = scan.to_dict()
            # Add latest result info
            latest_result = scan.get_latest_result()
            if latest_result:
                scan_dict["latest_result"] = {
                    "id": latest_result.id,
                    "status": latest_result.status,
                    "start_time": (
                        latest_result.start_time.isoformat()
                        if latest_result.start_time
                        else None
                    ),
                    "ports_found": latest_result.ports_found,
                }
            scan_dict["result_count"] = scan.get_result_count()
            scan_dict["success_rate"] = scan.get_success_rate()
            scans_data.append(scan_dict)

        return (
            jsonify(
                {
                    "status": "success",
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "scans": scans_data,
                }
            ),
            200,
        )

    except Exception as e:
        current_app.logger.error(f"Failed to list scans: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/scans/<int:scan_id>", methods=["GET"])
@login_required
def get_scan(scan_id):
    """Get details of a specific scan"""
    try:
        # Get scan with access control
        if current_user.is_admin:
            scan = Scan.query.get(scan_id)
        else:
            scan = Scan.query.filter_by(id=scan_id, user_id=current_user.id).first()

        if not scan:
            return jsonify({"status": "error", "message": "Scan not found"}), 404

        # Get detailed information
        scan_dict = scan.to_dict()

        # Add recent results
        recent_results = (
            ScanResult.query.filter_by(scan_id=scan_id)
            .order_by(ScanResult.created_at.desc())
            .limit(10)
            .all()
        )
        scan_dict["recent_results"] = [result.to_dict() for result in recent_results]

        # Add statistics
        scan_dict["statistics"] = {
            "total_results": scan.get_result_count(),
            "success_rate": scan.get_success_rate(),
            "last_success": None,
            "last_failure": None,
        }

        # Get last success and failure
        last_success = (
            ScanResult.query.filter_by(scan_id=scan_id, status="completed")
            .order_by(ScanResult.created_at.desc())
            .first()
        )
        if last_success:
            scan_dict["statistics"][
                "last_success"
            ] = last_success.created_at.isoformat()

        last_failure = (
            ScanResult.query.filter_by(scan_id=scan_id, status="failed")
            .order_by(ScanResult.created_at.desc())
            .first()
        )
        if last_failure:
            scan_dict["statistics"][
                "last_failure"
            ] = last_failure.created_at.isoformat()

        return jsonify({"status": "success", "scan": scan_dict}), 200

    except Exception as e:
        current_app.logger.error(f"Failed to get scan: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/scans", methods=["POST"])
@login_required
def create_scan():
    """Create a new scan configuration"""
    try:
        data = request.get_json()

        # Validate required fields
        if not data.get("name"):
            return jsonify({"status": "error", "message": "Scan name is required"}), 400
        if not data.get("target"):
            return jsonify({"status": "error", "message": "Target is required"}), 400

        # Create new scan
        scan = Scan(
            user_id=current_user.id,
            name=data["name"],
            description=data.get("description", ""),
            target=data["target"],
            ports=data.get("ports", "1-1000"),
            scan_arguments=data.get("scan_arguments", ""),
            interval_minutes=data.get("interval_minutes", 60),
            is_active=data.get("is_active", True),
            is_scheduled=data.get("is_scheduled", False),
        )

        # Calculate next run if scheduled
        if scan.is_scheduled and scan.is_active:
            scan.next_run = datetime.utcnow() + timedelta(minutes=scan.interval_minutes)

        db.session.add(scan)
        db.session.commit()

        # Schedule if needed
        if scan.is_scheduled and scan.is_active:
            _schedule_scan(scan)

        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Scan created successfully",
                    "scan": scan.to_dict(),
                }
            ),
            201,
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to create scan: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/scans/<int:scan_id>", methods=["PUT"])
@login_required
def update_scan(scan_id):
    """Update an existing scan configuration"""
    try:
        # Get scan with access control
        if current_user.is_admin:
            scan = Scan.query.get(scan_id)
        else:
            scan = Scan.query.filter_by(id=scan_id, user_id=current_user.id).first()

        if not scan:
            return jsonify({"status": "error", "message": "Scan not found"}), 404

        data = request.get_json()

        # Track scheduling changes
        old_scheduled = scan.is_scheduled
        old_active = scan.is_active
        old_interval = scan.interval_minutes

        # Update fields
        if "name" in data:
            scan.name = data["name"]
        if "description" in data:
            scan.description = data["description"]
        if "target" in data:
            scan.target = data["target"]
        if "ports" in data:
            scan.ports = data["ports"]
        if "scan_arguments" in data:
            scan.scan_arguments = data["scan_arguments"]
        if "interval_minutes" in data:
            scan.interval_minutes = data["interval_minutes"]
        if "is_active" in data:
            scan.is_active = data["is_active"]
        if "is_scheduled" in data:
            scan.is_scheduled = data["is_scheduled"]

        scan.updated_at = datetime.utcnow()

        # Handle scheduling changes
        if (
            old_scheduled != scan.is_scheduled
            or old_active != scan.is_active
            or old_interval != scan.interval_minutes
        ):

            # Remove old schedule if exists
            if old_scheduled and old_active:
                _unschedule_scan(scan_id)

            # Add new schedule if needed
            if scan.is_scheduled and scan.is_active:
                scan.next_run = datetime.utcnow() + timedelta(
                    minutes=scan.interval_minutes
                )
                _schedule_scan(scan)
            else:
                scan.next_run = None

        db.session.commit()

        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Scan updated successfully",
                    "scan": scan.to_dict(),
                }
            ),
            200,
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to update scan: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/scans/<int:scan_id>", methods=["DELETE"])
@login_required
def delete_scan(scan_id):
    """Deactivate a scan configuration instead of deleting it"""
    try:
        # Get scan with access control
        if current_user.is_admin:
            scan = Scan.query.get(scan_id)
        else:
            scan = Scan.query.filter_by(id=scan_id, user_id=current_user.id).first()

        if not scan:
            return jsonify({"status": "error", "message": "Scan not found"}), 404

        # Unschedule
        _unschedule_scan(scan_id)

        # Deactivate scan instead of deleting
        scan.is_active = False
        scan.is_scheduled = False
        scan.next_run = None
        scan.updated_at = datetime.utcnow()
        db.session.commit()

        return (
            jsonify({"status": "success", "message": "Scan deactivated successfully"}),
            200,
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to deactivate scan: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ============== SCAN EXECUTION ==============


@bp.route("/scans/<int:scan_id>/execute", methods=["POST"])
@login_required
def execute_scan(scan_id):
    """Manually trigger a scan execution"""
    try:
        # Get scan with access control
        if current_user.is_admin:
            scan = Scan.query.get(scan_id)
        else:
            scan = Scan.query.filter_by(id=scan_id, user_id=current_user.id).first()

        if not scan:
            return jsonify({"status": "error", "message": "Scan not found"}), 404

        # Call the scheduler's _execute_scan function directly
        from app.scheduler import _execute_scan

        _execute_scan(scan_id)

        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Scan execution started",
                    "scan_id": scan_id,
                }
            ),
            202,
        )
    except Exception as e:
        current_app.logger.error(f"Failed to execute scan: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/scans/<int:scan_id>/toggle", methods=["POST"])
@login_required
def toggle_scan(scan_id):
    """Toggle scan active status"""
    try:
        # Get scan with access control
        if current_user.is_admin:
            scan = Scan.query.get(scan_id)
        else:
            scan = Scan.query.filter_by(id=scan_id, user_id=current_user.id).first()

        if not scan:
            return jsonify({"status": "error", "message": "Scan not found"}), 404

        # Toggle active status
        scan.is_active = not scan.is_active
        scan.updated_at = datetime.utcnow()

        # Handle scheduling
        if scan.is_scheduled:
            if scan.is_active:
                scan.next_run = datetime.utcnow() + timedelta(
                    minutes=scan.interval_minutes
                )
                _schedule_scan(scan)
            else:
                scan.next_run = None
                _unschedule_scan(scan_id)

        db.session.commit()

        return (
            jsonify(
                {
                    "status": "success",
                    "message": f"Scan {'activated' if scan.is_active else 'deactivated'}",
                    "scan": scan.to_dict(),
                }
            ),
            200,
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to toggle scan: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/scans/<int:scan_id>/schedule", methods=["POST"])
@login_required
def update_scan_schedule(scan_id):
    """Update scan scheduling"""
    try:
        # Get scan with access control
        if current_user.is_admin:
            scan = Scan.query.get(scan_id)
        else:
            scan = Scan.query.filter_by(id=scan_id, user_id=current_user.id).first()

        if not scan:
            return jsonify({"status": "error", "message": "Scan not found"}), 404

        data = request.get_json()

        # Update scheduling parameters
        if "is_scheduled" in data:
            scan.is_scheduled = data["is_scheduled"]
        if "interval_minutes" in data:
            scan.interval_minutes = data["interval_minutes"]

        scan.updated_at = datetime.utcnow()

        # Update scheduler
        if scan.is_scheduled and scan.is_active:
            scan.next_run = datetime.utcnow() + timedelta(minutes=scan.interval_minutes)
            _schedule_scan(scan)
        else:
            scan.next_run = None
            _unschedule_scan(scan_id)

        db.session.commit()

        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Schedule updated successfully",
                    "scan": scan.to_dict(),
                }
            ),
            200,
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to update schedule: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ============== SCHEDULER INTEGRATION ==============


def _schedule_scan(scan):
    """Add scan to scheduler"""
    try:
        from app.scheduler import scheduler_service

        job_id = f"scan_{scan.id}"

        # Remove existing job if any
        if scheduler_service.scheduler.get_job(job_id):
            scheduler_service.scheduler.remove_job(job_id)

        # Add new job
        scheduler_service.scheduler.add_job(
            func=_execute_scheduled_scan,
            trigger="interval",
            minutes=scan.interval_minutes,
            id=job_id,
            args=[scan.id],
            name=f"Scheduled scan: {scan.name}",
            replace_existing=True,
            max_instances=1,
        )

        current_app.logger.info(
            f"Scheduled scan {scan.id} with interval {scan.interval_minutes} minutes"
        )

    except Exception as e:
        current_app.logger.error(f"Failed to schedule scan {scan.id}: {str(e)}")


def _unschedule_scan(scan_id):
    """Remove scan from scheduler"""
    try:
        from app.scheduler import scheduler_service

        job_id = f"scan_{scan_id}"

        if scheduler_service.scheduler.get_job(job_id):
            scheduler_service.scheduler.remove_job(job_id)
            current_app.logger.info(f"Unscheduled scan {scan_id}")

    except Exception as e:
        current_app.logger.error(f"Failed to unschedule scan {scan_id}: {str(e)}")


def _execute_scheduled_scan(scan_id):
    """Execute a scheduled scan (called by scheduler)"""
    try:
        with current_app.app_context():
            scan = Scan.query.get(scan_id)

            if not scan or not scan.is_active:
                current_app.logger.warning(
                    f"Scheduled scan {scan_id} not found or inactive"
                )
                return

            # Check for available clients
            available_clients = Client.query.filter(
                and_(
                    Client.status.in_(["online", "idle"]),
                    Client.last_seen >= datetime.utcnow() - timedelta(minutes=5),
                )
            ).count()

            if available_clients == 0:
                current_app.logger.warning(
                    f"No clients available for scheduled scan {scan_id}"
                )
                return

            # Create scan task
            task_id = str(uuid.uuid4())
            targets = scan.target.split(",") if "," in scan.target else [scan.target]
            targets = [t.strip() for t in targets]

            task = ScanTask(
                task_id=task_id,
                targets=targets,
                ports=scan.ports,
                scan_type="tcp",
                priority=1,  # Lower priority for scheduled scans
                status="pending",
            )

            db.session.add(task)

            # Update scan
            scan.update_last_run()
            scan.next_run = datetime.utcnow() + timedelta(minutes=scan.interval_minutes)

            db.session.commit()

            current_app.logger.info(
                f"Executed scheduled scan {scan_id}, task {task_id}"
            )

    except Exception as e:
        current_app.logger.error(
            f"Failed to execute scheduled scan {scan_id}: {str(e)}"
        )
        db.session.rollback()


# ============== SCAN RESULTS ==============


@bp.route("/scans/<int:scan_id>/results", methods=["GET"])
@login_required
def get_scan_results(scan_id):
    """Get results for a specific scan"""
    try:
        # Verify access
        if current_user.is_admin:
            scan = Scan.query.get(scan_id)
        else:
            scan = Scan.query.filter_by(id=scan_id, user_id=current_user.id).first()

        if not scan:
            return jsonify({"status": "error", "message": "Scan not found"}), 404

        # Query parameters
        limit = request.args.get("limit", 20, type=int)
        offset = request.args.get("offset", 0, type=int)
        status = request.args.get("status")  # completed, failed, running

        # Build query
        query = ScanResult.query.filter(
            ScanResult.results_data.contains({"scan_config_id": scan_id})
        )

        if status:
            query = query.filter_by(status=status)

        # Order by creation date (newest first)
        query = query.order_by(ScanResult.created_at.desc())

        # Get total count
        total = query.count()

        # Apply pagination
        results = query.limit(limit).offset(offset).all()

        return (
            jsonify(
                {
                    "status": "success",
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "results": [result.to_dict() for result in results],
                }
            ),
            200,
        )

    except Exception as e:
        current_app.logger.error(f"Failed to get scan results: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
