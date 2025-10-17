"""
Delta Report Routes Blueprint
Provides API endpoints for delta reports
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
bp = Blueprint("delta", __name__)


@bp.route("/scan/<int:scan_id>/reports", methods=["GET"])
@login_required
def get_scan_reports(scan_id):
    """
    Get paginated delta reports for a scan (API).

    Query Parameters:
        - page (int): Page number (default: 1)
        - per_page (int): Items per page (default: 10, max: 100)
        - only_changes (bool): Only show reports with changes (default: false)

    URL: /api/scan/5/reports?page=1&per_page=10&only_changes=true
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


@bp.route("/report/<int:report_id>", methods=["GET"])
@login_required
def get_report(report_id):
    """
    Get a specific delta report with full details (API).

    Query Parameters:
        - include_data (bool): Include full delta_data (default: false)

    URL: /api/report/123?include_data=true
    """
    report = DeltaReport.query.get_or_404(report_id)

    # Check authorization
    scan = report.scan
    if scan.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    include_data = request.args.get("include_data", "false").lower() == "true"

    return jsonify(report.to_dict(include_delta_data=include_data))


@bp.route("/report/<int:report_id>/export/csv", methods=["GET"])
@login_required
def export_report_csv(report_id):
    """
    Export a delta report as CSV (API).

    URL: /api/report/123/export/csv
    """
    report = DeltaReport.query.get_or_404(report_id)

    # Check authorization
    scan = report.scan
    if scan.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    # Generate CSV
    csv_content = report.to_csv()

    # Create filename
    filename = (
        f"delta_report_{report.id}_{report.created_at.strftime('%Y%m%d_%H%M%S')}.csv"
    )

    # Return as downloadable file
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@bp.route("/report/<int:report_id>", methods=["DELETE"])
@login_required
def delete_report(report_id):
    """
    Delete a specific delta report (API).

    URL: /api/report/abc-123-def (DELETE)
    """
    report = DeltaReport.query.get_or_404(report_id)

    # Check authorization
    scan = report.scan
    if scan.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    db.session.delete(report)
    db.session.commit()

    return jsonify({"message": "Delta report deleted successfully"})


@bp.route("/scan/<int:scan_id>/summary", methods=["GET"])
@login_required
def get_scan_summary(scan_id):
    """
    Get a summary of all delta reports for a scan (API).

    Query Parameters:
        - days (int): Include last N days (default: 30)

    URL: /api/scan/5/summary?days=7
    """
    scan = Scan.query.get_or_404(scan_id)

    # Check authorization
    if scan.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    days = request.args.get("days", 30, type=int)
    summary = DeltaReportService.get_change_summary(scan_id, days=days)

    return jsonify(summary)


@bp.route("/user/reports", methods=["GET"])
@login_required
def get_user_reports():
    """
    Get all delta reports for the current user across all scans (API).

    Query Parameters:
        - page (int): Page number (default: 1)
        - per_page (int): Items per page (default: 10)
        - only_changes (bool): Only show reports with changes (default: false)

    URL: /api/user/reports?page=1&per_page=20&only_changes=true
    """
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 10, type=int), 100)
    only_changes = request.args.get("only_changes", "false").lower() == "true"

    result = DeltaReportService.get_reports_by_user(
        user_id=current_user.id, page=page, per_page=per_page, only_changes=only_changes
    )

    return jsonify(result)


@bp.route("/scan/<int:scan_id>/export-all", methods=["GET"])
@login_required
def export_all_reports(scan_id):
    """
    Export all delta reports for a scan as a ZIP file (API).

    URL: /api/scan/5/export-all
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
