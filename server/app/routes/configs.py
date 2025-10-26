"""
Configs Routes – Admin UI
"""

from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    flash,
    redirect,
    url_for,
    current_app,
)
from flask_login import login_required, current_user
from functools import wraps
from app.config import update_config, get_config_value, validate_and_prepare_db_path
from app import db
import logging

logger = logging.getLogger(__name__)

bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not getattr(current_user, "is_admin", False):
            flash("Administrator privileges required.", "danger")
            return redirect(url_for("main.index"))
        return f(*args, **kwargs)

    return decorated


@bp.route("/config")
@admin_required
def index():
    """Render the full configs page – categories are passed from the service."""
    from app.config import get_all_env_config

    # Get all .env configuration values
    env_config = get_all_env_config()

    # Define all editable .env variables
    env_keys = [
        "SQLALCHEMY_DATABASE_URI",
        "FLASK_ENV",
        "HOST",
        "PORT",
        "SECRET_KEY",
        "SECURITY_PASSWORD_SALT",
        "ENTRA_CLIENT_ID",
        "ENTRA_CLIENT_SECRET",
        "ENTRA_TENANT_ID",
        "MAIL_SERVER",
        "MAIL_PORT",
        "MAIL_USE_TLS",
        "MAIL_USERNAME",
        "MAIL_PASSWORD",
    ]

    # Sensitive keys that should be masked
    sensitive_keys = {
        "SECRET_KEY",
        "SECURITY_PASSWORD_SALT",
        "ENTRA_CLIENT_SECRET",
        "MAIL_PASSWORD",
    }

    # Get all .env configuration values
    env_config = {}
    for key in env_keys:
        value = get_config_value(key)
        # Mask sensitive values
        if key in sensitive_keys and value:
            env_config[key] = "********"
        else:
            env_config[key] = value

    return render_template(
        "admin/configs.html",
        env_config=env_config,
        show_sidebar=True,
    )


@bp.route("/config", methods=["POST"])
@admin_required
def update_env_config():
    """Update .env file configuration"""
    new_values = request.json

    try:
        # Validate DB path if present
        if "SQLALCHEMY_DATABASE_URI" in new_values:
            new_values["SQLALCHEMY_DATABASE_URI"] = validate_and_prepare_db_path(
                new_values["SQLALCHEMY_DATABASE_URI"]
            )

        # Update .env
        update_config(new_values)

        logger.info(f"Configuration updated by user {current_user.id}")

        return jsonify(
            {
                "success": True,
                "message": "Configuration saved to .env. Application restart required for changes to take effect.",
            }
        )
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ----------------------------------------------------------------------
# Testing endpoints
# ----------------------------------------------------------------------


@bp.route("/test/email", methods=["POST"])
@admin_required
def api_test_email():
    """Test email configuration"""
    from flask_mail import Mail, Message

    recipient = request.json.get("email") or current_user.email
    if not recipient:
        return jsonify({"success": False, "error": "No recipient"}), 400

    try:
        mail = Mail(current_app)
        msg = Message(
            "Port Detector – Email Test",
            sender=current_app.config.get("MAIL_SENDER"),
            recipients=[recipient],
        )
        msg.body = "This is a test email. Your SMTP configs are working!"
        mail.send(msg)

        return jsonify({"success": True, "message": f"Test email sent to {recipient}"})
    except Exception as exc:
        logger.exception("Email test failed")
        return jsonify({"success": False, "error": str(exc)}), 500


@bp.route("/test/database", methods=["POST"])
@admin_required
def test_database():
    """Test database connectivity"""
    db_uri = request.json.get("database_uri")

    if not db_uri:
        return jsonify({"success": False, "error": "No database URI provided"}), 400

    try:
        from sqlalchemy import create_engine, text

        # Validate and prepare path
        db_uri = validate_and_prepare_db_path(db_uri)
        if not db_uri:
            return (
                jsonify({"success": False, "error": "SQLite database doesn't exist"}),
                400,
            )

        # Test connection
        engine = create_engine(db_uri)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        return jsonify({"success": True, "message": "Database connection successful"})
    except Exception as e:
        logger.error(f"Database test failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
