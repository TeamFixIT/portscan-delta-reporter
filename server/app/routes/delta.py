"""
Delta Report Routes Blueprint
Provides web UI and API endpoints for delta reports
"""

from flask import Blueprint, render_template, jsonify, request, Response, abort
from flask_login import login_required, current_user
from app.models.delta_report import DeltaReport
from app.models.scan import Scan
from app.services.delta_service import DeltaReportService
from app import db
import zipfile
from io import BytesIO

# Create blueprint
bp = Blueprint("delta", __name__, url_prefix="/delta")


# ============================================================================
# WEB UI ROUTES
# ============================================================================


@bp.route("/scan/<int:scan_id>")
@login_required
def scan_delta_reports(scan_id):
    """
    Render the delta reports page for a specific scan.

    URL: /delta/scan/5
    """
    scan = Scan.query.get_or_404(scan_id)

    # Check authorization
    if scan.user_id != current_user.id and not current_user.is_admin:
        abort(403)

    return render_template("dashboard/reports.html", scan=scan)


# ============================================================================
# API ENDPOINTS
# ============================================================================


@bp.route("/api/scan/<int:scan_id>/reports", methods=["GET"])
@login_required
def get_scan_reports_api(scan_id):
    """
    Get paginated delta reports for a scan (API).

    Query Parameters:
        - page (int): Page number (default: 1)
        - per_page (int): Items per page (default: 10, max: 100)
        - only_changes (bool): Only show reports with changes (default: false)

    URL: /delta/api/scan/5/reports?page=1&per_page=10&only_changes=true
    """
    scan = Scan.query.get_or_404(scan_id)

    # Check authorization
    if scan.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    # Get query parameters
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 10, type=int), 100)
    only_changes = request.args.get("only_changes", "false").lower() == "true"

    # Get paginated reports
    result = scan.get_delta_reports(
        page=page, per_page=per_page, only_with_changes=only_changes
    )

    return jsonify(result)


@bp.route("/api/report/<int:report_id>", methods=["GET"])
@login_required
def get_report_api(report_id):
    """
    Get a specific delta report with full details (API).

    Query Parameters:
        - include_data (bool): Include full delta_data (default: false)

    URL: /delta/api/report/123?include_data=true
    """
    report = DeltaReport.query.get_or_404(report_id)

    # Check authorization
    scan = report.scan
    if scan.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    include_data = request.args.get("include_data", "false").lower() == "true"

    return jsonify(report.to_dict(include_delta_data=include_data))


@bp.route("/api/report/<int:report_id>/export/csv", methods=["GET"])
@login_required
def export_report_csv_api(report_id):
    """
    Export a delta report as CSV (API).

    URL: /delta/api/report/123/export/csv
    """
    report = DeltaReport.query.get_or_404(report_id)

    # Check authorization
    scan = report.scan
    if scan.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    # Generate CSV
    csv_content = report.to_csv()

    # Create filename
    filename = f"delta_report_{report.report_id}_{report.created_at.strftime('%Y%m%d_%H%M%S')}.csv"

    # Return as downloadable file
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@bp.route("/api/report/<string:report_id>", methods=["DELETE"])
@login_required
def delete_report_api(report_id):
    """
    Delete a specific delta report (API).

    URL: /delta/api/report/abc-123-def (DELETE)
    """
    report = DeltaReport.query.filter_by(report_id=report_id).first_or_404()

    # Check authorization
    scan = report.scan
    if scan.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    db.session.delete(report)
    db.session.commit()

    return jsonify({"message": "Delta report deleted successfully"})


@bp.route("/api/scan/<int:scan_id>/generate", methods=["POST"])
@login_required
def generate_report_api(scan_id):
    """
    Manually trigger delta report generation for the latest scan result (API).

    URL: /delta/api/scan/5/generate (POST)
    """
    scan = Scan.query.get_or_404(scan_id)

    # Check authorization
    if scan.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    # Generate delta report
    delta_report = scan.auto_generate_delta_report()

    if delta_report:
        return (
            jsonify(
                {
                    "message": "Delta report generated successfully",
                    "report": delta_report.to_dict(),
                }
            ),
            201,
        )
    else:
        return (
            jsonify(
                {
                    "error": "Could not generate delta report",
                    "reason": "No previous baseline scan available or latest scan not completed",
                }
            ),
            400,
        )


@bp.route("/api/scan/<int:scan_id>/summary", methods=["GET"])
@login_required
def get_scan_summary_api(scan_id):
    """
    Get a summary of all delta reports for a scan (API).

    Query Parameters:
        - days (int): Include last N days (default: 30)

    URL: /delta/api/scan/5/summary?days=7
    """
    scan = Scan.query.get_or_404(scan_id)

    # Check authorization
    if scan.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    days = request.args.get("days", 30, type=int)
    summary = DeltaReportService.get_change_summary(scan_id, days=days)

    return jsonify(summary)


@bp.route("/api/scan/<int:scan_id>/export-all", methods=["GET"])
@login_required
def export_all_reports_api(scan_id):
    """
    Export all delta reports for a scan as a ZIP file (API).

    URL: /delta/api/scan/5/export-all
    """
    scan = Scan.query.get_or_404(scan_id)

    # Check authorization
    if scan.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    # Get all reports for this scan
    reports = (
        DeltaReport.query.filter_by(scan_id=scan_id)
        .order_by(DeltaReport.created_at.desc())
        .all()
    )

    if not reports:
        return jsonify({"error": "No reports found"}), 404

    # Create zip file
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for report in reports:
            csv_content = report.to_csv()
            filename = f"delta_report_{report.created_at.strftime('%Y%m%d_%H%M%S')}_{report.id}.csv"
            zip_file.writestr(filename, csv_content)

    zip_buffer.seek(0)

    # Create filename
    zip_filename = f"delta_reports_scan_{scan_id}_{scan.name.replace(' ', '_')}.zip"

    return Response(
        zip_buffer.getvalue(),
        mimetype="application/zip",
        headers={"Content-Disposition": f"attachment; filename={zip_filename}"},
    )


@bp.route("/api/user/reports", methods=["GET"])
@login_required
def get_user_reports_api():
    """
    Get all delta reports for the current user across all scans (API).

    Query Parameters:
        - page (int): Page number (default: 1)
        - per_page (int): Items per page (default: 10)
        - only_changes (bool): Only show reports with changes (default: false)

    URL: /delta/api/user/reports?page=1&per_page=20&only_changes=true
    """
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 10, type=int), 100)
    only_changes = request.args.get("only_changes", "false").lower() == "true"

    result = DeltaReportService.get_reports_by_user(
        user_id=current_user.id, page=page, per_page=per_page, only_changes=only_changes
    )

    return jsonify(result)


@bp.route("/api/user/critical", methods=["GET"])
@login_required
def get_critical_changes_api():
    """
    Get delta reports with critical changes for the current user (API).

    Query Parameters:
        - severity (str): 'low', 'medium', 'high' (default: medium)

    URL: /delta/api/user/critical?severity=high
    """
    severity = request.args.get("severity", "medium")

    if severity not in ["low", "medium", "high"]:
        return jsonify({"error": "Invalid severity level"}), 400

    reports = DeltaReportService.get_critical_changes(
        user_id=current_user.id, severity_threshold=severity
    )

    return jsonify(
        {
            "severity": severity,
            "count": len(reports),
            "reports": [r.to_dict() for r in reports],
        }
    )


@bp.route("/api/host-history/<int:scan_id>/<host_ip>", methods=["GET"])
@login_required
def get_host_history_api(scan_id, host_ip):
    """
    Get change history for a specific host (API).

    Query Parameters:
        - limit (int): Number of reports to check (default: 10)

    URL: /delta/api/host-history/5/192.168.1.10?limit=20
    """
    scan = Scan.query.get_or_404(scan_id)

    # Check authorization
    if scan.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    limit = request.args.get("limit", 10, type=int)

    history = DeltaReportService.get_host_change_history(
        scan_id=scan_id, host_ip=host_ip, limit=limit
    )

    return jsonify({"scan_id": scan_id, "host_ip": host_ip, "history": history})


@bp.route("/api/port-history/<int:scan_id>/<host_ip>/<int:port>", methods=["GET"])
@login_required
def get_port_history_api(scan_id, host_ip, port):
    """
    Get change history for a specific port on a host (API).

    Query Parameters:
        - limit (int): Number of reports to check (default: 10)

    URL: /delta/api/port-history/5/192.168.1.10/80?limit=20
    """
    scan = Scan.query.get_or_404(scan_id)

    # Check authorization
    if scan.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    limit = request.args.get("limit", 10, type=int)

    history = DeltaReportService.get_port_change_history(
        scan_id=scan_id, host_ip=host_ip, port=port, limit=limit
    )

    return jsonify(
        {"scan_id": scan_id, "host_ip": host_ip, "port": port, "history": history}
    )


# ============================================================================
# ERROR HANDLERS
# ============================================================================


@bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    if request.path.startswith("/delta/api/"):
        return jsonify({"error": "Resource not found"}), 404
    return render_template("errors/404.html"), 404


@bp.errorhandler(403)
def forbidden(error):
    """Handle 403 errors"""
    if request.path.startswith("/delta/api/"):
        return jsonify({"error": "Forbidden"}), 403
    return render_template("errors/403.html"), 403


@bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    db.session.rollback()
    if request.path.startswith("/delta/api/"):
        return jsonify({"error": "Internal server error"}), 500
    return render_template("errors/500.html"), 500


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def register_delta_routes(app):
    """
    Register the delta blueprint with the Flask app.

    Usage in app/__init__.py:
        from routes.delta_routes import register_delta_routes
        register_delta_routes(app)
    """
    app.register_blueprint(bp)
