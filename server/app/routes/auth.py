"""
Authentication routes
"""

import re
import msal
from app.models.user import User
from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    jsonify,
    session,
)
from app import db
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.urls import url_parse


bp = Blueprint("auth", __name__)


def _build_msal_app(cache=None, authority=None):
    """Build MSAL confidential client application"""
    from flask import current_app

    return msal.ConfidentialClientApplication(
        current_app.config["ENTRA_CLIENT_ID"],
        authority=authority or current_app.config["ENTRA_AUTHORITY"],
        client_credential=current_app.config["ENTRA_CLIENT_SECRET"],
        token_cache=cache,
    )


def _build_auth_url(authority=None, scopes=None, state=None):
    """Build authentication URL for Entra ID"""
    from flask import current_app

    msal_app = _build_msal_app(authority=authority)
    return msal_app.get_authorization_request_url(
        scopes or current_app.config["ENTRA_SCOPE"],
        state=state or str(session.get("state")),
        redirect_uri=url_for("auth.entra_callback", _external=True),
    )


def validate_email(email):
    """Validate email format"""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one number"
    return True, "Password is valid"


@bp.route("/login", methods=["GET", "POST"])
def login():
    """User login route - supports both local and Entra ID"""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form
        username = data.get("username", "").strip()
        password = data.get("password", "")
        remember = data.get("remember", False)

        # Input validation
        if not username or not password:
            error = "Username and password are required"
            if request.is_json:
                return jsonify({"success": False, "error": error}), 400
            flash(error, "error")
            return render_template("auth/login.html")

        # Authenticate user
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            if not user.is_active:
                error = "Account is deactivated. Please contact administrator."
                if request.is_json:
                    return jsonify({"success": False, "error": error}), 403
                flash(error, "error")
                return render_template("auth/login.html")

            login_user(user, remember=remember)
            user.update_last_login()

            # Handle redirect after login
            next_page = request.args.get("next")
            if not next_page or url_parse(next_page).netloc != "":
                next_page = url_for("dashboard.index")

            if request.is_json:
                return jsonify(
                    {
                        "success": True,
                        "message": "Login successful",
                        "redirect": next_page,
                    }
                )

            flash("Welcome back!", "success")
            return redirect(next_page)
        else:
            error = "Invalid username or password"
            if request.is_json:
                return jsonify({"success": False, "error": error}), 401
            flash(error, "error")

    return render_template("auth/login.html")


@bp.route("/entra/login")
def entra_login():
    """Initiate Entra ID login"""
    from flask import current_app
    import uuid

    # Generate and store state for CSRF protection
    state = str(uuid.uuid4())
    session["state"] = state
    session["next"] = request.args.get("next", url_for("dashboard.index"))

    # Build authorization URL
    auth_url = _build_auth_url(state=state)
    return redirect(auth_url)


@bp.route("/entra/callback")
def entra_callback():
    """Handle Entra ID callback"""
    from flask import current_app

    # Verify state for CSRF protection
    if request.args.get("state") != session.get("state"):
        flash("Invalid state parameter. Please try again.", "error")
        return redirect(url_for("auth.login"))

    # Check for errors from Entra ID
    if "error" in request.args:
        error = request.args.get("error")
        error_description = request.args.get("error_description", "Unknown error")
        flash(f"Authentication failed: {error_description}", "error")
        return redirect(url_for("auth.login"))

    # Exchange authorization code for token
    if "code" not in request.args:
        flash("No authorization code received.", "error")
        return redirect(url_for("auth.login"))

    try:
        msal_app = _build_msal_app()
        result = msal_app.acquire_token_by_authorization_code(
            request.args["code"],
            scopes=current_app.config["ENTRA_SCOPE"],
            redirect_uri=url_for("auth.entra_callback", _external=True),
        )

        if "error" in result:
            flash(
                f"Authentication failed: {result.get('error_description', 'Unknown error')}",
                "error",
            )
            return redirect(url_for("auth.login"))

        # Get user info from token
        user_info = result.get("id_token_claims")

        # Get or create user
        user = User.get_or_create_from_entra(user_info)

        if not user.is_active:
            flash("Account is deactivated. Please contact administrator.", "error")
            return redirect(url_for("auth.login"))

        # Log user in
        login_user(user)
        user.update_last_login()

        # Get next page from session
        next_page = session.pop("next", url_for("dashboard.index"))
        if url_parse(next_page).netloc != "":
            next_page = url_for("dashboard.index")

        flash(f"Welcome back, {user.get_full_name()}!", "success")
        return redirect(next_page)

    except Exception as e:
        current_app.logger.error(f"Entra ID authentication error: {str(e)}")
        flash("Authentication failed. Please try again.", "error")
        return redirect(url_for("auth.login"))


@bp.route("/register", methods=["GET", "POST"])
def register():
    """User registration route"""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form

        username = data.get("username", "").strip()
        email = data.get("email", "").strip().lower()
        first_name = data.get("first_name", "").strip()
        last_name = data.get("last_name", "").strip()
        password = data.get("password", "")
        confirm_password = data.get("confirm_password", "")

        # Input validation
        errors = []

        if not username:
            errors.append("Username is required")
        elif len(username) < 3:
            errors.append("Username must be at least 3 characters long")
        elif not re.match(r"^[a-zA-Z0-9_]+$", username):
            errors.append("Username can only contain letters, numbers, and underscores")

        if not email:
            errors.append("Email is required")
        elif not validate_email(email):
            errors.append("Please enter a valid email address")

        if not password:
            errors.append("Password is required")
        else:
            is_valid, message = validate_password(password)
            if not is_valid:
                errors.append(message)

        if password != confirm_password:
            errors.append("Passwords do not match")

        if errors:
            if request.is_json:
                return jsonify({"success": False, "errors": errors}), 400
            for error in errors:
                flash(error, "error")
            return render_template("auth/register.html")

        # Check for existing users
        if User.query.filter_by(username=username).first():
            error = "Username already exists"
            if request.is_json:
                return jsonify({"success": False, "error": error}), 400
            flash(error, "error")
            return render_template("auth/register.html")

        if User.query.filter_by(email=email).first():
            error = "Email already registered"
            if request.is_json:
                return jsonify({"success": False, "error": error}), 400
            flash(error, "error")
            return render_template("auth/register.html")

        # Create new user
        try:
            user = User.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name if first_name else None,
                last_name=last_name if last_name else None,
            )

            # Auto-login the new user
            login_user(user)
            user.update_last_login()

            if request.is_json:
                return jsonify(
                    {
                        "success": True,
                        "message": "Registration successful",
                        "redirect": url_for("dashboard.index"),
                    }
                )

            flash("Registration successful! Welcome to Port Detector.", "success")
            return redirect(url_for("dashboard.index"))

        except Exception as e:
            error = f"Registration failed: {str(e)}"
            if request.is_json:
                return jsonify({"success": False, "error": error}), 500
            flash(error, "error")

    return render_template("auth/register.html")


@bp.route("/logout")
@login_required
def logout():
    """User logout route"""
    username = current_user.username
    is_sso = current_user.is_sso_user()
    logout_user()
    session.clear()

    flash(f"You have been logged out, {username}.", "info")

    # For SSO users, optionally redirect to Entra ID logout
    if is_sso and request.args.get("full_logout"):
        from flask import current_app

        entra_logout_url = f"{current_app.config['ENTRA_AUTHORITY']}/oauth2/v2.0/logout?post_logout_redirect_uri={url_for('auth.login', _external=True)}"
        return redirect(entra_logout_url)

    return redirect(url_for("auth.login"))


@bp.route("/profile")
@login_required
def profile():
    """User profile page"""
    return render_template("auth/profile.html", user=current_user, show_sidebar=True)


@bp.route("/profile/update", methods=["POST"])
@login_required
def update_profile():
    """Update user profile"""
    data = request.get_json() if request.is_json else request.form

    first_name = data.get("first_name", "").strip()
    last_name = data.get("last_name", "").strip()
    email = data.get("email", "").strip().lower()

    errors = []

    # SSO users cannot change email
    if current_user.is_sso_user() and email != current_user.email:
        errors.append("Email cannot be changed for SSO accounts")

    # Validate email for local users
    if not current_user.is_sso_user() and email and email != current_user.email:
        if not validate_email(email):
            errors.append("Please enter a valid email address")
        elif User.query.filter_by(email=email).first():
            errors.append("Email already in use by another account")

    if errors:
        if request.is_json:
            return jsonify({"success": False, "errors": errors}), 400
        for error in errors:
            flash(error, "error")
        return redirect(url_for("auth.profile"))

    # Update user information
    try:
        current_user.first_name = first_name if first_name else None
        current_user.last_name = last_name if last_name else None
        if not current_user.is_sso_user() and email and email != current_user.email:
            current_user.email = email

        db.session.commit()

        if request.is_json:
            return jsonify({"success": True, "message": "Profile updated successfully"})

        flash("Profile updated successfully!", "success")
        return redirect(url_for("auth.profile"))

    except Exception as e:
        db.session.rollback()
        error = f"Failed to update profile: {str(e)}"

        if request.is_json:
            return jsonify({"success": False, "error": error}), 500

        flash(error, "error")
        return redirect(url_for("auth.profile"))


@bp.route("/change-password", methods=["POST"])
@login_required
def change_password():
    """Change user password - only for local users"""
    if current_user.is_sso_user():
        error = "Password cannot be changed for SSO accounts"
        if request.is_json:
            return jsonify({"success": False, "error": error}), 403
        flash(error, "error")
        return redirect(url_for("auth.profile"))

    data = request.get_json() if request.is_json else request.form

    current_password = data.get("current_password", "")
    new_password = data.get("new_password", "")
    confirm_password = data.get("confirm_password", "")

    # Validation
    errors = []

    if not current_password:
        errors.append("Current password is required")
    elif not current_user.check_password(current_password):
        errors.append("Current password is incorrect")

    if not new_password:
        errors.append("New password is required")
    else:
        is_valid, message = validate_password(new_password)
        if not is_valid:
            errors.append(message)

    if new_password != confirm_password:
        errors.append("New passwords do not match")

    if current_password == new_password:
        errors.append("New password must be different from current password")

    if errors:
        if request.is_json:
            return jsonify({"success": False, "errors": errors}), 400
        for error in errors:
            flash(error, "error")
        return redirect(url_for("auth.profile"))

    # Update password
    try:
        current_user.set_password(new_password)
        db.session.commit()

        if request.is_json:
            return jsonify(
                {"success": True, "message": "Password changed successfully"}
            )

        flash("Password changed successfully!", "success")
        return redirect(url_for("auth.profile"))

    except Exception as e:
        db.session.rollback()
        error = f"Failed to change password: {str(e)}"

        if request.is_json:
            return jsonify({"success": False, "error": error}), 500

        flash(error, "error")
        return redirect(url_for("auth.profile"))
