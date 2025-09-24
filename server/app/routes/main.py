"""
Main routes for the Port Scanner Delta Reporter
"""

from flask import Blueprint, render_template

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Home page"""
    return render_template("index.html")


@main_bp.route("/about")
def about():
    """About page"""
    return render_template("about.html")


@main_bp.route("/hello")
def hello():
    """About page"""
    return render_template("index.html")
