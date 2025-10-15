import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


class Config:
    """Base configuration class"""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{os.path.join(basedir, 'app.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = (
        os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    )
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    UPLOAD_FOLDER = os.path.join(basedir, "uploads")
    SCANNER_OUTPUT_DIR = os.path.join(basedir, "scan_results")

    # Redis, Email, and Entra ID configs
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    MAIL_SERVER = os.getenv("MAIL_SERVER")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() in ("true", "on", "1")
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_SENDER = os.getenv("MAIL_SENDER", "Port Detector <noreply@portdetector.com>")

    ENTRA_CLIENT_ID = os.getenv("ENTRA_CLIENT_ID")
    ENTRA_CLIENT_SECRET = os.getenv("ENTRA_CLIENT_SECRET")
    ENTRA_TENANT_ID = os.getenv("ENTRA_TENANT_ID")
    ENTRA_REDIRECT_PATH = "/auth/entra/callback"
    ENTRA_AUTHORITY = f"https://login.microsoftonline.com/{ENTRA_TENANT_ID}"
    ENTRA_SCOPE = ["User.Read"]

    # Session configuration for MSAL
    SESSION_TYPE = "filesystem"
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True

    @staticmethod
    def init_app(app):
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        os.makedirs(app.config["SCANNER_OUTPUT_DIR"], exist_ok=True)


class DevelopmentConfig(Config):
    DEBUG = True
    SCANNER_LOG_LEVEL = "DEBUG"
    SESSION_COOKIE_SECURE = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    SECURITY_HEADERS = {
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'",
    }

    @classmethod
    def init_app(cls, app):
        super().init_app(app)
        import logging
        from logging import StreamHandler

        handler = StreamHandler()
        handler.setLevel(logging.INFO)
        app.logger.addHandler(handler)


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config():
    return config.get(os.getenv("FLASK_ENV", "development"), DevelopmentConfig)
