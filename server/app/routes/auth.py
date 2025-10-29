"""
Authentication routes with Flask-Security-Too and OAuth support
"""

import uuid
import json
from datetime import datetime, timedelta
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
from flask_security import (
    login_required,
    current_user,
    login_user,
    logout_user,
    hash_password,
)
from urllib.parse import urlparse as url_parse
from app import db
from app import azure

bp = Blueprint("auth", __name__)


@bp.route("/profile")
@login_required
def profile():
    """User profile page"""
    oauth_connections = {
        conn.provider_name: conn for conn in current_user.oauth_connections.all()
    }

    return render_template(
        "auth/profile.html",
        user=current_user,
        oauth_connections=oauth_connections,
        show_sidebar=True,
    )


@bp.route("/login/azure")
def azure_login():
    redirect_uri = url_for("azure_authorize", _external=True)
    return azure.authorize_redirect(redirect_uri)


@bp.route("/authorize/azure")
def azure_authorize():
    try:
        token = azure.authorize_access_token()
        user_info = token.get("userinfo")

        if not user_info:
            user_info = azure.get("https://graph.microsoft.com/v1.0/me").json()

        # Find or create user
        azure_id = user_info.get("sub") or user_info.get("id")
        email = user_info.get("email") or user_info.get("userPrincipalName")

        user = User.query.filter_by(azure_id=azure_id).first()

        if not user:
            user = User.query.filter_by(email=email).first()
            if user:
                user.azure_id = azure_id
            else:
                user = user_datastore.create_user(
                    email=email,
                    azure_id=azure_id,
                    first_name=user_info.get("given_name", ""),
                    last_name=user_info.get("family_name", ""),
                    username=user_info.get("preferred_username", email),
                    password=hash_password(secrets.token_hex(32)),
                    active=True,
                    fs_uniquifier=secrets.token_hex(16),
                )
            db.session.commit()

        # Log in the user
        from flask_security import login_user

        login_user(user)

        flash("Successfully logged in with Microsoft Azure!", "success")
        return redirect(url_for("profile"))

    except Exception as e:
        flash(f"Login failed: {str(e)}", "error")
        return redirect(url_for("index"))


@bp.route("/logout")
@login_required
def logout():
    from flask_security import logout_user

    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))
