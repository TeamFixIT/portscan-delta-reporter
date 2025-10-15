"""
Dashboard routes for web interface
"""

from app import db
from flask import Blueprint, render_template, jsonify, abort, request, redirect, url_for
from flask_login import login_required, current_user
from app.models.client import Client
from app.models.scan import Scan
from app.models.scan_task import ScanTask
from app.models.scan_result import ScanResult
from app.models.delta_report import DeltaReport
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
    return render_template("dashboard/scans.html", scans=scan_list)


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
    return render_template("dashboard/clients.html", clients=client_list)


@bp.route("/reports")
@login_required
def reports():
    """
    Render the delta reports page.
    """
    return render_template("dashboard/reports.html")
