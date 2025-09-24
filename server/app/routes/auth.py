"""
Authentication routes
"""
import re
from app.models.user import User
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from app import db
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.urls import url_parse


bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login route"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        username = data.get('username', '').strip()
        password = data.get('password', '')
        remember = data.get('remember', False)

        # Input validation
        if not username or not password:
            error = 'Username and password are required'
            if request.is_json:
                return jsonify({'success': False, 'error': error}), 400
            flash(error, 'error')
            return render_template('auth/login.html')

        # Authenticate user
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            if not user.is_active:
                error = 'Account is deactivated. Please contact administrator.'
                if request.is_json:
                    return jsonify({'success': False, 'error': error}), 403
                flash(error, 'error')
                return render_template('auth/login.html')

            login_user(user, remember=remember)
            user.update_last_login()

            # Handle redirect after login
            next_page = request.args.get('next')
            if not next_page or url_parse(next_page).netloc != '':
                next_page = url_for('dashboard.index')

            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': 'Login successful',
                    'redirect': next_page
                })

            flash('Welcome back!', 'success')
            return redirect(next_page)
        else:
            error = 'Invalid username or password'
            if request.is_json:
                return jsonify({'success': False, 'error': error}), 401
            flash(error, 'error')

    return render_template('auth/login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration route"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form

        username = data.get('username', '').strip()
        email = data.get('email', '').strip().lower()
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')

        # Input validation
        errors = []

        if not username:
            errors.append('Username is required')
        elif len(username) < 3:
            errors.append('Username must be at least 3 characters long')
        elif not re.match(r'^[a-zA-Z0-9_]+$', username):
            errors.append('Username can only contain letters, numbers, and underscores')

        if not email:
            errors.append('Email is required')
        elif not validate_email(email):
            errors.append('Please enter a valid email address')

        if not password:
            errors.append('Password is required')
        else:
            is_valid, message = validate_password(password)
            if not is_valid:
                errors.append(message)

        if password != confirm_password:
            errors.append('Passwords do not match')

        if errors:
            if request.is_json:
                return jsonify({'success': False, 'errors': errors}), 400
            for error in errors:
                flash(error, 'error')
            return render_template('auth/register.html')

        # Check for existing users
        if User.query.filter_by(username=username).first():
            error = 'Username already exists'
            if request.is_json:
                return jsonify({'success': False, 'error': error}), 400
            flash(error, 'error')
            return render_template('auth/register.html')

        if User.query.filter_by(email=email).first():
            error = 'Email already registered'
            if request.is_json:
                return jsonify({'success': False, 'error': error}), 400
            flash(error, 'error')
            return render_template('auth/register.html')

        # Create new user
        try:
            user = User.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name if first_name else None,
                last_name=last_name if last_name else None
            )

            # Auto-login the new user
            login_user(user)
            user.update_last_login()

            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': 'Registration successful',
                    'redirect': url_for('dashboard.index')
                })

            flash('Registration successful! Welcome to Port Detector.', 'success')
            return redirect(url_for('dashboard.index'))

        except Exception as e:
            error = f'Registration failed: {str(e)}'
            if request.is_json:
                return jsonify({'success': False, 'error': error}), 500
            flash(error, 'error')

    return render_template('auth/register.html')



@bp.route('/logout')
@login_required
def logout():
    """User logout route"""
    username = current_user.username
    logout_user()
    flash(f'You have been logged out, {username}.', 'info')
    return redirect(url_for('auth.login'))

@bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    return render_template('auth/profile.html', user=current_user)

@bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    """Update user profile"""
    data = request.get_json() if request.is_json else request.form

    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    email = data.get('email', '').strip().lower()

    errors = []

    # Validate email
    if email and email != current_user.email:
        if not validate_email(email):
            errors.append('Please enter a valid email address')
        elif User.query.filter_by(email=email).first():
            errors.append('Email already in use by another account')

    if errors:
        if request.is_json:
            return jsonify({'success': False, 'errors': errors}), 400
        for error in errors:
            flash(error, 'error')
        return redirect(url_for('auth.profile'))

    # Update user information
    try:
        current_user.first_name = first_name if first_name else None
        current_user.last_name = last_name if last_name else None
        if email and email != current_user.email:
            current_user.email = email

        db.session.commit()

        if request.is_json:
            return jsonify({'success': True, 'message': 'Profile updated successfully'})

        flash('Profile updated successfully!', 'success')
        return redirect(url_for('auth.profile'))

    except Exception as e:
        db.session.rollback()
        error = f'Failed to update profile: {str(e)}'

        if request.is_json:
            return jsonify({'success': False, 'error': error}), 500

        flash(error, 'error')
        return redirect(url_for('auth.profile'))


@bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password"""
    data = request.get_json() if request.is_json else request.form

    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    confirm_password = data.get('confirm_password', '')

    # Validation
    errors = []

    if not current_password:
        errors.append('Current password is required')
    elif not current_user.check_password(current_password):
        errors.append('Current password is incorrect')

    if not new_password:
        errors.append('New password is required')
    else:
        is_valid, message = validate_password(new_password)
        if not is_valid:
            errors.append(message)

    if new_password != confirm_password:
        errors.append('New passwords do not match')

    if current_password == new_password:
        errors.append('New password must be different from current password')

    if errors:
        if request.is_json:
            return jsonify({'success': False, 'errors': errors}), 400
        for error in errors:
            flash(error, 'error')
        return redirect(url_for('auth.profile'))

    # Update password
    try:
        current_user.set_password(new_password)
        db.session.commit()

        if request.is_json:
            return jsonify({'success': True, 'message': 'Password changed successfully'})

        flash('Password changed successfully!', 'success')
        return redirect(url_for('auth.profile'))

    except Exception as e:
        db.session.rollback()
        error = f'Failed to change password: {str(e)}'

        if request.is_json:
            return jsonify({'success': False, 'error': error}), 500

        flash(error, 'error')
        return redirect(url_for('auth.profile'))
