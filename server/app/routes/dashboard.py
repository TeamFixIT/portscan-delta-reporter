"""
Dashboard routes for web interface
"""

from app import db
from flask import (
    Blueprint,
    render_template,
    jsonify,
    abort,
    request,
    redirect,
    url_for,
    flash,
    send_file,
)
import os
from pathlib import Path
from flask_login import login_required, current_user
from app.models.client import Client
from app.models.scan import Scan
from app.models.scan_task import ScanTask
from app.models.scan_result import ScanResult
from app.models.delta_report import DeltaReport
from app.models.alert import Alert
import csv
import json
import io
import click
from datetime import datetime, timedelta

bp = Blueprint("dashboard", __name__)


@bp.route("/")
@login_required
def index():
    count = 0
    """Dashboard home"""
    active_clients = Client.query.filter_by(status="online").count()
    recent_scans = Scan.query.filter(
        Scan.last_run >= datetime.utcnow() - timedelta(hours=24)
    ).count()
    reports_count = DeltaReport.query.count()
    return render_template(
        "dashboard/index.html",
        stats={
            "clients": active_clients,
            "scans": recent_scans,
            "reports": reports_count,
        },
        show_sidebar=True,
    )


@bp.route("/scans")
@login_required
def scans():
    scan_list = Scan.query.all()
    for scan in scan_list:
        scan.tasks = (
            ScanTask.query.filter_by(scan_id=scan.id)
            .order_by(ScanTask.created_at.asc())
            .all()
        )
        # Add this to fetch results
        scan.results_list = (
            ScanResult.query.filter_by(scan_id=scan.id)
            .order_by(ScanResult.started_at.desc())
            .all()
        )
    return render_template("dashboard/scans.html", scans=scan_list, show_sidebar=True)


@bp.route("/scans/create", methods=["GET"])
@login_required
def create_scan():
    """Render the create scan page"""
    return render_template("dashboard/create_scan.html")


@bp.route("/scans/<int:scan_id>")
@login_required
def view_scan(scan_id):
    scan = Scan.query.get_or_404(scan_id)

    task_page = request.args.get("task_page", 1, type=int)
    result_page = request.args.get("result_page", 1, type=int)

    tasks_pagination = (
        ScanTask.query.filter_by(scan_id=scan.id)
        .order_by(ScanTask.created_at.desc())
        .paginate(page=task_page, per_page=10)
    )

    results_pagination = (
        ScanResult.query.filter_by(scan_id=scan.id)
        .order_by(ScanResult.started_at.desc())
        .paginate(page=result_page, per_page=5)
    )

    return render_template(
        "dashboard/view_scan.html",
        scan=scan,
        tasks_pagination=tasks_pagination,
        results_pagination=results_pagination,
        show_sidebar=True,
    )


@bp.route("/scans/<int:scan_id>/edit", methods=["GET"])
@login_required
def edit_scan(scan_id):
    scan = Scan.query.get_or_404(scan_id)
    return render_template("dashboard/edit_scan.html", scan=scan)


@bp.route("/clients")
@login_required
def clients():
    """View connected clients"""
    client_list = Client.query.order_by(Client.last_seen.desc()).all()
    return render_template(
        "dashboard/clients.html", clients=client_list, show_sidebar=True
    )


@bp.route("/reports")
@login_required
def reports():
    """
    Render the delta reports page.
    """
    reports_list = DeltaReport.query.all()
    return render_template(
        "dashboard/reports.html", reports=reports_list, show_sidebar=True
    )


@bp.route("/reports/<int:report_id>")
@login_required
def view_delta_report(report_id):
    """
    View detailed delta report with all changes
    """
    report = DeltaReport.query.get_or_404(report_id)

    return render_template(
        "dashboard/view_report.html", report=report, show_sidebar=True
    )


@bp.route("/reports/scan/<int:scan_id>")
@login_required
def scan_history(scan_id):
    """
    View all delta reports for a specific scan (timeline view)
    """
    scan = Scan.query.get_or_404(scan_id)

    # Check if scan belongs to user (add your auth logic)
    # if scan.user_id != current_user.id:
    #     abort(403)

    # Get all reports for this scan (including partial)
    reports = (
        DeltaReport.query.filter_by(scan_id=scan_id)
        .order_by(DeltaReport.created_at.desc())
        .all()
    )

    return render_template(
        "dashboard/scan_history.html", scan=scan, reports=reports, show_sidebar=True
    )


@bp.route("/delta/report/<int:report_id>/export")
@login_required
def export_delta_report(report_id):
    """
    Export delta report as CSV
    """
    report = DeltaReport.query.get_or_404(report_id)

    # Check if report belongs to user's scan (add your auth logic)
    # if report.scan.user_id != current_user.id:
    #     abort(403)

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header information
    writer.writerow(["Delta Report Export"])
    writer.writerow(["Report ID", report.id])
    writer.writerow(["Scan Target", report.scan.target if report.scan else "N/A"])
    writer.writerow(["Generated At", report.created_at.strftime("%Y-%m-%d %H:%M:%S")])
    writer.writerow(["Status", report.status])
    writer.writerow([])

    # Write summary statistics
    writer.writerow(["Summary Statistics"])
    writer.writerow(["Metric", "Count"])
    writer.writerow(["New Hosts", report.new_hosts_count])
    writer.writerow(["Removed Hosts", report.removed_hosts_count])
    writer.writerow(["New Ports", report.new_ports_count])
    writer.writerow(["Closed Ports", report.closed_ports_count])
    writer.writerow(["Changed Services", report.changed_services_count])
    writer.writerow([])

    # Write comparison info
    if (
        report.delta_data
        and "baseline" in report.delta_data
        and "current" in report.delta_data
    ):
        writer.writerow(["Comparison Details"])
        writer.writerow(
            [
                "Baseline Result ID",
                report.delta_data["baseline"].get("result_id", "N/A"),
            ]
        )
        writer.writerow(
            [
                "Baseline Completed",
                report.delta_data["baseline"].get("completed_at", "N/A"),
            ]
        )
        writer.writerow(
            ["Current Result ID", report.delta_data["current"].get("result_id", "N/A")]
        )
        writer.writerow(
            [
                "Current Completed",
                report.delta_data["current"].get("completed_at", "N/A"),
            ]
        )
        writer.writerow([])

    # Write detailed changes if available
    if report.delta_data and "delta" in report.delta_data:
        delta = report.delta_data["delta"]

        # New hosts
        if delta.get("new_up_hosts"):
            writer.writerow(["New Hosts"])
            writer.writerow(["IP Address"])
            for host in delta["new_up_hosts"]:
                writer.writerow([host])
            writer.writerow([])

        # Removed hosts
        if delta.get("new_down_hosts"):
            writer.writerow(["Removed Hosts"])
            writer.writerow(["IP Address"])
            for host in delta["new_down_hosts"]:
                writer.writerow([host])
            writer.writerow([])

        # Added ports
        if delta.get("added_ports"):
            writer.writerow(["New Open Ports"])
            writer.writerow(["Host", "Port", "Protocol", "Service", "State"])
            for port in delta["added_ports"]:
                writer.writerow(
                    [
                        port.get("host", "N/A"),
                        port.get("port", "N/A"),
                        port.get("protocol", "N/A"),
                        port.get("service", "N/A"),
                        port.get("state", "N/A"),
                    ]
                )
            writer.writerow([])

        # Removed ports
        if delta.get("removed_ports"):
            writer.writerow(["Closed Ports"])
            writer.writerow(["Host", "Port", "Protocol", "Service"])
            for port in delta["removed_ports"]:
                writer.writerow(
                    [
                        port.get("host", "N/A"),
                        port.get("port", "N/A"),
                        port.get("protocol", "N/A"),
                        port.get("service", "N/A"),
                    ]
                )
            writer.writerow([])

        # Changed ports
        if delta.get("changed_ports"):
            writer.writerow(["Changed Services"])
            writer.writerow(["Host", "Port", "Protocol", "Before", "After"])
            for change in delta["changed_ports"]:
                before = change.get("before", {})
                after = change.get("after", {})
                writer.writerow(
                    [
                        change.get("host", "N/A"),
                        change.get("port", "N/A"),
                        change.get("protocol", "N/A"),
                        f"{before.get('service', 'N/A')} ({before.get('banner', 'N/A')})",
                        f"{after.get('service', 'N/A')} ({after.get('banner', 'N/A')})",
                    ]
                )
            writer.writerow([])

    # Prepare file for download
    output.seek(0)
    filename = (
        f"delta_report_{report.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )

    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename,
    )


@bp.route("/delta/report/<int:report_id>/export/json")
@login_required
def export_delta_report_json(report_id):
    """
    Export delta report as JSON
    """
    report = DeltaReport.query.get_or_404(report_id)

    # Check if report belongs to user's scan (add your auth logic)
    # if report.scan.user_id != current_user.id:
    #     abort(403)

    export_data = {
        "report_id": report.id,
        "scan_id": report.scan_id,
        "scan_target": report.scan.target if report.scan else None,
        "generated_at": report.created_at.isoformat(),
        "status": report.status,
        "summary": {
            "new_hosts_count": report.new_hosts_count,
            "removed_hosts_count": report.removed_hosts_count,
            "new_ports_count": report.new_ports_count,
            "closed_ports_count": report.closed_ports_count,
            "changed_services_count": report.changed_services_count,
        },
        "delta_data": report.delta_data,
    }

    filename = (
        f"delta_report_{report.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )

    return send_file(
        io.BytesIO(json.dumps(export_data, indent=2).encode("utf-8")),
        mimetype="application/json",
        as_attachment=True,
        download_name=filename,
    )


@bp.route("/delta/compare")
@login_required
def compare_reports():
    """
    Compare two specific scan results (for manual comparison)
    """
    baseline_id = request.args.get("baseline", type=int)
    current_id = request.args.get("current", type=int)

    if not baseline_id or not current_id:
        flash("Please select both baseline and current results to compare.", "warning")
        return redirect(url_for("dashboard.reports"))

    baseline = ScanResult.query.get_or_404(baseline_id)
    current = ScanResult.query.get_or_404(current_id)

    # Check if results belong to same scan
    if baseline.scan_id != current.scan_id:
        flash("Results must be from the same scan to compare.", "danger")
        return redirect(url_for("dashboard.reports"))

    # Find or create delta report for this comparison
    delta_report = DeltaReport.query.filter_by(
        baseline_result_id=baseline_id, current_result_id=current_id
    ).first()

    if not delta_report:
        flash(
            "No delta report found for this comparison. Run a scan to generate one.",
            "info",
        )
        return redirect(url_for("dashboard.reports"))

    return redirect(url_for("dashboard.view_delta_report", report_id=delta_report.id))


@bp.route("/logs")
@login_required
def logs():
    """Display log files"""
    logs_dir = Path(__file__).parent.parent.parent / "logs"

    # Fixed log files
    log_names = ["app.log", "error.log", "scheduler.log"]
    log_files = []

    for log_name in log_names:
        log_file = logs_dir / log_name
        if log_file.exists() and log_file.is_file():
            stats = log_file.stat()
            # Get last 50 lines for preview
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    last_lines = lines[-50:] if len(lines) > 50 else lines
                    preview = "".join(last_lines)
                    total_lines = len(lines)
            except Exception:
                preview = "Error reading file"
                total_lines = 0

            log_files.append(
                {
                    "name": log_name,
                    "size": stats.st_size,
                    "modified": datetime.fromtimestamp(stats.st_mtime),
                    "preview": preview,
                    "total_lines": total_lines,
                }
            )
        else:
            # File doesn't exist yet
            log_files.append(
                {
                    "name": log_name,
                    "size": 0,
                    "modified": None,
                    "preview": "Log file not created yet",
                    "total_lines": 0,
                }
            )

    return render_template(
        "dashboard/logs.html", log_files=log_files, show_sidebar=True
    )


@bp.route("/logs/<filename>/download")
@login_required
def download_log(filename):
    """Download log file"""
    # Only allow the three specific log files
    allowed_files = ["app.log", "error.log", "schedule.log"]
    if filename not in allowed_files:
        abort(403)

    logs_dir = Path(__file__).parent.parent.parent / "logs"
    log_file = logs_dir / filename

    if not log_file.exists() or not log_file.is_file():
        abort(404)

    return send_file(log_file, as_attachment=True, download_name=filename)


@bp.route("/alerts")
def alerts():
    alerts = Alert.query.order_by(Alert.created_at.desc()).all()
    return render_template("dashboard/alerts.html", alerts=alerts, show_sidebar=True)


@bp.route("/alerts/<int:alert_id>/status", methods=["POST"])
def update_alert_status(alert_id):
    data = request.get_json()
    alert = Alert.query.get_or_404(alert_id)
    if data.get("status") == "actioned":
        alert.mark_actioned()
    elif data.get("status") == "ignored":
        alert.mark_ignored()
    db.session.commit()
    return jsonify({"message": "Status updated"}), 200
