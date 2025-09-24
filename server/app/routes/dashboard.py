"""
Dashboard routes for web interface
"""

from flask import Blueprint, render_template
from flask_login import login_required

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    """Dashboard home"""
    return render_template("dashboard/index.html")


@dashboard_bp.route("/scans")
def scans():
    """View scan results"""
    return render_template("dashboard/scans.html")


@dashboard_bp.route("/clients")
@login_required
def clients():
    """View connected clients"""
    return render_template("dashboard/clients.html")


@dashboard_bp.route("/reports")
@login_required
def reports():
    """View generated reports"""
    return render_template("dashboard/reports.html")
