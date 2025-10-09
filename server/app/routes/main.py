"""
Main routes for the Port Scanner Delta Reporter
"""

from flask import Blueprint, render_template


bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    """Home page"""
    return render_template("index.html")
