"""
Authentication routes
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.forms import LoginForm


auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    form = LoginForm()
    if form.validate_on_submit():
        # Placeholder: replace with real authentication logic
        flash('Login functionality not fully implemented; received username: {}'.format(form.username.data), 'info')
        return redirect(url_for('main.index'))

    # If the form wasn't submitted or didn't validate, render the login template with the form
    return render_template('auth/login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        # TODO: Implement user registration
        flash('Registration functionality not yet implemented', 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html')
