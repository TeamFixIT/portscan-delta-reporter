"""
Dashboard routes for web interface
"""
from app import db
from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint("dashboard", __name__)


@bp.route("/")
@login_required
def index():
    count = 0
    """Dashboard home"""
    return render_template("dashboard/index.html", count=count)


@bp.route("/scans")
def scans():
    """View scan results"""
    return render_template("dashboard/scans.html")


@bp.route("/clients")
@login_required
def clients():
    """View connected clients"""
    return render_template("dashboard/clients.html")


@bp.route("/reports")
@login_required
def reports():
    """View generated reports"""
    return render_template("dashboard/reports.html")
