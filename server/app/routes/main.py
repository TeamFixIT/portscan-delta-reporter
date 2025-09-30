"""
Main routes for the Port Scanner Delta Reporter
"""

from flask import Blueprint, render_template
from app.forms import LoginForm


main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Home page"""
    form = LoginForm()
    return render_template('index.html', form=form)

@main_bp.route('/about')
def about():
    """About page"""
    return render_template('about.html')