"""
Settings Routes

Admin interface for managing application settings.
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from functools import wraps
from app.services.settings_service import settings_service
from app.models.setting import Setting
from app import db
import logging

logger = logging.getLogger(__name__)

bp = Blueprint("settings", __name__)


def admin_required(f):
    """Decorator to require admin privileges"""

    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash("You need administrator privileges to access this page.", "danger")
            return redirect(url_for("main.index"))
        return f(*args, **kwargs)

    return decorated_function


@bp.route("/")
@admin_required
def index():
    """Display settings page"""
    categories = settings_service.get_all_categories()
    return render_template("admin/settings.html", categories=categories)


@bp.route("/api/settings", methods=["GET"])
@admin_required
def get_settings():
    """Get all settings grouped by category"""
    try:
        categories = settings_service.get_all_categories()
        return jsonify({"success": True, "categories": categories})
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/settings/category/<category>", methods=["GET"])
@admin_required
def get_category_settings(category):
    """Get settings for a specific category"""
    try:
        settings = settings_service.get_category(category)
        return jsonify({"success": True, "settings": settings})
    except Exception as e:
        logger.error(f"Error getting category settings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/settings/<key>", methods=["PUT"])
@admin_required
def update_setting(key):
    """Update a setting value"""
    try:
        data = request.get_json()
        value = data.get("value")

        if value is None:
            return jsonify({"success": False, "error": "Value is required"}), 400

        # Get existing setting to preserve metadata
        setting = Setting.query.filter_by(key=key).first()

        if not setting:
            return jsonify({"success": False, "error": "Setting not found"}), 404

        # Update the setting
        success = settings_service.set(
            key=key,
            value=value,
            category=setting.category,
            description=setting.description,
            is_sensitive=setting.is_sensitive,
            user_id=current_user.id,
        )

        if success:
            logger.info(f"Setting {key} updated by user {current_user.username}")
            return jsonify({"success": True, "message": "Setting updated successfully"})
        else:
            return jsonify({"success": False, "error": "Failed to update setting"}), 500

    except Exception as e:
        logger.error(f"Error updating setting: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/settings/test/email", methods=["POST"])
@admin_required
def test_email():
    """Test email configuration"""
    try:
        from flask_mail import Mail, Message
        from flask import current_app

        # Create a temporary mail instance with current settings
        mail = Mail(current_app)

        test_recipient = request.json.get("email", current_user.email)

        msg = Message(
            "Port Detector - Email Configuration Test",
            sender=current_app.config.get("MAIL_SENDER"),
            recipients=[test_recipient],
        )
        msg.body = "This is a test email from Port Detector. Your email configuration is working correctly!"

        mail.send(msg)

        return jsonify(
            {"success": True, "message": f"Test email sent to {test_recipient}"}
        )

    except Exception as e:
        logger.error(f"Email test failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/settings/initialise", methods=["POST"])
@admin_required
def initialise_settings():
    """initialise default settings"""
    try:
        settings_service.initialise_defaults()
        return jsonify({"success": True, "message": "Default settings initialised"})
    except Exception as e:
        logger.error(f"Error initializing settings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/settings/reload", methods=["POST"])
@admin_required
def reload_settings():
    """Reload settings into app config"""
    try:
        from flask import current_app
        from config import Config

        Config.load_database_settings(current_app)

        return jsonify({"success": True, "message": "Settings reloaded successfully"})
    except Exception as e:
        logger.error(f"Error reloading settings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
