"""
Authentication routes
"""

import re
import secrets
from app.models.user import User
from datetime import datetime
from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    jsonify,
    session,
    current_app,
)
from app import db
from app import oauth
from flask import current_app as app
from flask_login import login_user, logout_user, login_required, current_user
from app.services.sse_service import sse_manager
from urllib.parse import urlparse
import uuid

from app.logging_config import get_logger

logger = get_logger(__name__)

bp = Blueprint("auth", __name__)


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
    """User login route - supports local authentication"""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form
        username = data.get("username", "").strip()
        password = data.get("password", "")
        remember = data.get("remember", False)
        # Input validation
        if not username or not password:
            flash("Invalid credentials")
            return redirect(url_for("auth.login"))
        # Authenticate user
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if not user.is_active:
                error = "Account is deactivated. Please contact administrator."
                flash(error, "error")
                return redirect(url_for("auth.login"))
            if user.current_session_token:
                sse_manager.redirect_user(user.id, "auth.login")
            new_token = secrets.token_hex(32)
            user.current_session_token = new_token
            user.last_login = datetime.utcnow()
            db.session.commit()
            login_user(user, remember=remember)
            session["session_token"] = new_token
            # Handle redirect after login
            next_page = request.args.get("next")
            if not next_page:
                next_page = url_for("dashboard.index")
            flash(f"Welcome back {user.first_name or user.username}.", "success")
            return redirect(next_page)
        else:
            error = "Invalid username or password"
            if request.is_json:
                return jsonify({"success": False, "error": error}), 401
            flash(error, "error")
    enabled_providers = current_app.config.get("ENABLED_PROVIDERS", [])
    return render_template("auth/login.html", enabled_providers=enabled_providers)


@bp.route("/login/<provider>")
def oauth_login(provider):
    if provider not in current_app.config["OAUTH2_PROVIDERS"]:
        flash(f"Unsupported provider: {provider}")
        return redirect(url_for("auth.login"))
    # Generate state for CSRF protection
    state = str(uuid.uuid4())
    session["oauth_state"] = state
    session["oauth_provider"] = provider
    # Redirect to provider
    redirect_uri = url_for("auth.oauth_callback", provider=provider, _external=True)
    # Use the dynamic provider client registered in `oauth`
    client = oauth.create_client(provider)
    return client.authorize_redirect(redirect_uri, state=state)


@bp.route("/oauth_callback/<provider>")
def oauth_callback(provider):
    if provider not in app.config["OAUTH2_PROVIDERS"]:
        flash(f"Unsupported provider: {provider}")
        return redirect(url_for("auth.login"))
    # Verify state
    if session.get("oauth_provider") != provider or session.get(
        "oauth_state"
    ) != request.args.get("state"):
        flash("OAuth state mismatch. Retry login.")
        return redirect(url_for("auth.login"))
    client = oauth.create_client(provider)
    if provider == "github":
        token = client.authorize_access_token()
        # Fetch user info separately for GitHub
        resp = client.get("https://api.github.com/user", token=token)
        user_info = resp.json()
    else:
        token = client.authorize_access_token()
        if not token:
            flash("OAuth token fetch failed.")
            return redirect(url_for("auth.login"))
        user_info = token.get("userinfo")

    email = (
        user_info.get("email")
        or user_info.get("preferred_username")
        or user_info.get("emailAddress")
    )
    if not email:
        flash(f"{provider.capitalize()} doesn't want to share your email.", "error")
        return redirect(url_for("auth.login"))
    user = User.query.filter_by(email=email).first()
    new_user = False
    if not user:
        new_user = True
        username = (
            user_info.get("name")
            or user_info.get("preferred_username")
            or email.split("@")[0]
        )
        # Adjust for general OAuth
        user = User.create_user(
            username=username,
            email=email,
            first_name=user_info.get("given_name"),
            last_name=user_info.get("family_name"),
            auth_provider=provider,  # Set to provider name
        )
    logger.info(f"OAuth login for user: {user.username} via {provider}")
    if user and user.current_session_token:
        sse_manager.redirect_user(user.id, "auth.login")
    # Generate session token for single-session logic
    new_token = secrets.token_hex(32)
    user.current_session_token = new_token
    db.session.commit()
    # Log in with Flask-Login
    login_user(user, remember=False)
    session["session_token"] = new_token

    session.pop("oauth_state", None)
    session.pop("oauth_provider", None)
    flash(
        f"Logged in via {provider.capitalize()} successfully! Welcome {'' if new_user else 'back '} {user.first_name or user.username}.",
        "success",
    )
    return (
        render_template("dashboard/onboarding.html", show_sidebar=True)
        if new_user
        else redirect(url_for("dashboard.index"))
    )


@bp.route("/register", methods=["GET", "POST"])
def register():
    """User registration route for local users"""
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
                auth_provider="local",
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
            flash(
                "Registration successful ! Welcome to Port Scanner Delta Reporter.",
                "success",
            )
            return render_template("dashboard/onboarding.html", show_sidebar=True)
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
    current_user.current_session_token = None
    logout_user()
    session.clear()
    flash(f"You have been logged out, {username}.", "info")
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
    if current_user.auth_provider != "local" and email != current_user.email:
        errors.append("Email cannot be changed for SSO accounts")
    # Validate email for local users
    if current_user.auth_provider == "local" and email and email != current_user.email:
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
        if (
            current_user.auth_provider == "local"
            and email
            and email != current_user.email
        ):
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
    if current_user.auth_provider != "local":
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
