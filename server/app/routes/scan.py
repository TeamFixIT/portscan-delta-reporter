"""
API routes for scan management
"""

from flask import Blueprint, request, jsonify, current_app, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import and_, or_
from app import db
from app.models.scan import Scan
from app.models.scan_task import ScanTask
from app.models.scan_result import ScanResult
from app.models.client import Client
from app.scheduler import scheduler_service
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
                    "started_at": (
                        latest_result.started_at.isoformat()
                        if latest_result.started_at
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
            # Use initial_interval if provided for immediate first execution
            initial_interval = data.get("initial_interval", 1)
            scan.next_run = datetime.utcnow() + timedelta(minutes=initial_interval)

        db.session.add(scan)
        db.session.commit()

        # Schedule if needed
        if scan.is_scheduled and scan.is_active:
            scheduler_service.schedule_scan(scan)

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


@bp.route("/scans/<int:scan_id>", methods=["POST", "PUT"])
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
            if request.accept_mimetypes.accept_html:
                flash("Scan not found", "danger")
                return redirect(url_for("dashboard.scans"))
            return jsonify({"status": "error", "message": "Scan not found"}), 404

        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form

        # Track old schedule state
        old_scheduled = scan.is_scheduled
        old_active = scan.is_active
        old_interval = scan.interval_minutes

        # Update fields if provided
        for field in [
            "name",
            "description",
            "target",
            "ports",
            "scan_arguments",
        ]:
            if field in data:
                setattr(scan, field, data[field])

        # Handle interval_minutes with type conversion
        if "interval_minutes" in data:
            scan.interval_minutes = int(data["interval_minutes"])

        if "is_active" in data:
            scan.is_active = (
                data["is_active"]
                if isinstance(data["is_active"], bool)
                else data["is_active"] in ("true", "on", "1")
            )
        else:
            scan.is_active = False

        if "is_scheduled" in data:
            scan.is_scheduled = (
                data["is_scheduled"]
                if isinstance(data["is_scheduled"], bool)
                else data["is_scheduled"] in ("true", "on", "1")
            )
        else:
            scan.is_scheduled = False

        scan.updated_at = datetime.utcnow()

        # Handle scheduling changes
        if (
            old_scheduled != scan.is_scheduled
            or old_active != scan.is_active
            or old_interval != scan.interval_minutes
        ):

            if old_scheduled and old_active:
                scheduler_service.unschedule_scan(scan_id)

            if scan.is_scheduled and scan.is_active:
                scan.next_run = datetime.utcnow() + timedelta(
                    minutes=scan.interval_minutes
                )
                scheduler_service.schedule_scan(scan)
            else:
                scan.next_run = None

        db.session.commit()

        if not request.is_json:
            flash("Scan updated successfully!", "success")
            return redirect(url_for("dashboard.scans"))

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

        if not request.is_json:
            flash(f"Error updating scan: {str(e)}", "danger")
            return redirect(url_for("dashboard.scans"))

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
        scheduler_service.unschedule_scan(scan_id)

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


@bp.route("/scans/<int:scan_id>/execute", methods=["POST"])
@login_required
def execute_scan(scan_id):
    """Manually trigger a scan execution"""
    try:
        # Access control
        if current_user.is_admin:
            scan = Scan.query.get(scan_id)
        else:
            scan = Scan.query.filter_by(id=scan_id, user_id=current_user.id).first()

        if not scan:
            return jsonify({"status": "error", "message": "Scan not found"}), 404

        from app.scheduler import _execute_scan

        result = _execute_scan(scan_id)

        status_code = 200 if result["status"] == "success" else 500
        return jsonify(result), status_code

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
                if not scan.next_run or scan.next_run <= datetime.utcnow():
                    scan.next_run = datetime.utcnow() + timedelta(
                        minutes=scan.interval_minutes
                    )
                scheduler_service.schedule_scan(scan)

            else:
                scheduler_service.unschedule_scan(scan_id)

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
