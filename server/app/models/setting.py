"""
Settings Model

Stores application configuration in database for runtime management.
"""

from app import db
from datetime import datetime
from sqlalchemy import Index


class Setting(db.Model):
    """Application settings stored in database"""

    __tablename__ = "settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(128), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=True)
    category = db.Column(
        db.String(64), nullable=False, index=True
    )  # email, scanner, etc.
    description = db.Column(db.String(256))
    is_sensitive = db.Column(db.Boolean, default=False)  # For passwords, secrets
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"))

    def __repr__(self):
        return f"<Setting {self.key}>"

    @staticmethod
    def get_value(key, default=None):
        """Get setting value by key"""
        setting = Setting.query.filter_by(key=key).first()
        return setting.value if setting else default

    @staticmethod
    def set_value(
        key,
        value,
        category="general",
        description=None,
        is_sensitive=False,
        user_id=None,
    ):
        """Set or update a setting value"""
        setting = Setting.query.filter_by(key=key).first()

        if setting:
            setting.value = value
            setting.updated_at = datetime.utcnow()
            setting.updated_by = user_id
        else:
            setting = Setting(
                key=key,
                value=value,
                category=category,
                description=description,
                is_sensitive=is_sensitive,
                updated_by=user_id,
            )
            db.session.add(setting)

        db.session.commit()
        return setting

    @staticmethod
    def get_by_category(category):
        """Get all settings in a category"""
        return Setting.query.filter_by(category=category).all()

    @staticmethod
    def initialise_defaults():
        """initialise default settings if they don't exist"""
        defaults = [
            # Email Settings
            ("MAIL_SERVER", None, "email", "Email server hostname", False),
            ("MAIL_PORT", "587", "email", "Email server port", False),
            ("MAIL_USE_TLS", "true", "email", "Use TLS for email", False),
            ("MAIL_USERNAME", None, "email", "Email username", False),
            ("MAIL_PASSWORD", None, "email", "Email password", True),
            (
                "MAIL_SENDER",
                "Port Detector <noreply@portdetector.com>",
                "email",
                "Email sender address",
                False,
            ),
            # Entra ID Settings
            ("ENTRA_CLIENT_ID", None, "auth", "Azure Entra ID Client ID", False),
            ("ENTRA_CLIENT_SECRET", None, "auth", "Azure Entra ID Client Secret", True),
            ("ENTRA_TENANT_ID", None, "auth", "Azure Entra ID Tenant ID", False),
            # Security Settings
            (
                "SESSION_COOKIE_SECURE",
                "false",
                "security",
                "Require HTTPS for session cookies",
                False,
            ),
            (
                "PERMANENT_SESSION_LIFETIME",
                "24",
                "security",
                "Session lifetime in hours",
                False,
            ),
        ]

        for key, value, category, description, is_sensitive in defaults:
            existing = Setting.query.filter_by(key=key).first()
            if not existing:
                setting = Setting(
                    key=key,
                    value=value,
                    category=category,
                    description=description,
                    is_sensitive=is_sensitive,
                )
                db.session.add(setting)

        db.session.commit()
