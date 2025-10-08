"""
Main routes for the Port Scanner Delta Reporter
"""

from flask import Blueprint, render_template
from app.forms import LoginForm


bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    """Home page"""
    return render_template("index.html")


@bp.route("/about")
def about():
    """About page"""
    return render_template("about.html")


''' Example additional route
@bp.route("/hello")
def hello():
    """About page"""
    return render_template("index.html")
'''
