"""
Dashboard routes for web interface
"""

from app import db
from flask import Blueprint, render_template
from flask_login import login_required
from app.models.client import Client

bp = Blueprint("dashboard", __name__)


@bp.route("/")
@login_required
def index():
    """Dashboard home"""
    # Query active clients (status == 'online')
    active_count = Client.query.filter_by(status="online").count()
    return render_template("dashboard/index.html", count=active_count)


from app.models.scan import Scan
from app.models.scan_task import ScanTask
from app.models.scan_result import ScanResult


@bp.route("/scans")
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
            .order_by(ScanResult.start_time.desc())
            .all()
        )
    return render_template("dashboard/scans.html", scans=scan_list)


@bp.route("/clients")
@login_required
def clients():
    """View connected clients"""
    client_list = Client.query.order_by(Client.last_seen.desc()).all()
    return render_template("dashboard/clients.html", clients=client_list)


@bp.route("/scans/create", methods=["GET"])
@login_required
def create_scan():
    """Render the create scan page"""
    return render_template("dashboard/create_scan.html")


@bp.route("/reports")
@login_required
def reports():
    """View generated reports"""
    return render_template("dashboard/reports.html")
