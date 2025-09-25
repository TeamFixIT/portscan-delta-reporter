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


@bp.route("/scans")
def scans():
    """View scan results"""
    return render_template("dashboard/scans.html")


@bp.route("/clients")
@login_required
def clients():
    """View connected clients"""
    client_list = Client.query.order_by(Client.last_seen.desc()).all()
    return render_template("dashboard/clients.html", clients=client_list)


@bp.route("/reports")
@login_required
def reports():
    """View generated reports"""
    return render_template("dashboard/reports.html")
