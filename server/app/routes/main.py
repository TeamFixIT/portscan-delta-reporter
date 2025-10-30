"""
Main routes for the Port Scanner Delta Reporter
"""

from flask import Blueprint, render_template, current_app

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    """Home page"""
    enabled_providers = current_app.config.get("ENABLED_PROVIDERS", [])
    return render_template("index.html", enabled_providers=enabled_providers)
