import os
from dotenv import load_dotenv, set_key
from pathlib import Path
from datetime import timedelta

# Load environment variables
load_dotenv()

# Path to .env file (assuming it's at project root)
BASE_DIR = Path(__file__).parent.parent
ENV_FILE = BASE_DIR / ".env"


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    user_db = os.getenv("SQLALCHEMY_DATABASE_URI")
    if user_db:
        db_uri = user_db
    else:
        # Default: SQLite in ./data/app.db (relative to BASE_DIR)
        db_dir = BASE_DIR / "data"
        db_dir.mkdir(exist_ok=True)
        db_path = db_dir / "app.db"
        db_uri = f"sqlite:///{db_path}"
        print(db_uri)

    if db_uri.startswith("sqlite:///") and ":memory:" not in db_uri:
        db_path = db_uri.replace("sqlite:///", "", 1)
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    set_key(ENV_FILE, "SQLALCHEMY_DATABASE_URI", db_uri)
    SQLALCHEMY_DATABASE_URI = db_uri
    SQLALCHEMY_TRACK_MODIFICATIONS = (
        os.getenv("SQLALCHEMY_TRACK_MODIFICATIONS", "False").lower() == "true"
    )
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }
    # Session configuration
    SESSION_TYPE = "filesystem"
    SESSION_FILE_DIR = BASE_DIR / "flask_session"
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = (
        os.environ.get("SESSION_COOKIE_SECURE", "False").lower() == "true"
    )
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # Flask-Security-Too settings
    SECURITY_PASSWORD_SALT = (
        os.environ.get("SECURITY_PASSWORD_SALT")
        or "super-secret-salt-change-in-production"
    )
    SECURITY_PASSWORD_HASH = "argon2"  # Modern, secure password hashing

    # Registration settings
    SECURITY_REGISTERABLE = True
    SECURITY_SEND_REGISTER_EMAIL = False  # Set to True if you configure email
    SECURITY_CONFIRMABLE = False  # Set to True to require email confirmation
    SECURITY_USERNAME_ENABLED = True
    SECURITY_USERNAME_REQUIRED = True

    # Login/logout settings
    SECURITY_URL_PREFIX = "/auth"
    SECURITY_POST_LOGIN_VIEW = "/dashboard"

    # Session and tracking
    SECURITY_TRACKABLE = True  # Track login IP and timestamps
    SECURITY_LOGIN_WITHOUT_CONFIRMATION = True

    # Two-factor authentication (optional)
    SECURITY_TWO_FACTOR = (
        os.environ.get("SECURITY_TWO_FACTOR", "False").lower() == "true"
    )
    SECURITY_TWO_FACTOR_REQUIRED = False

    # Password requirements
    SECURITY_PASSWORD_LENGTH_MIN = 8
    SECURITY_PASSWORD_COMPLEXITY_CHECKER = "zxcvbn"

    # Token settings
    SECURITY_TOKEN_AUTHENTICATION_HEADER = "Authentication-Token"
    SECURITY_TOKEN_MAX_AGE = 86400  # 24 hours

    WTF_CSRF_CHECK_DEFAULT = False

    # CSRF protection
    SECURITY_CSRF_PROTECT_MECHANISMS = ["session", "basic"]
    SECURITY_CSRF_IGNORE_UNAUTH_ENDPOINTS = True

    # Flash message categories
    SECURITY_FLASH_MESSAGES = True

    # OAuth Settings - Azure AD / Microsoft Entra ID
    AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID")
    AZURE_CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET")
    AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID", "common")

    # OAuth Settings - Google
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

    # OAuth Settings - GitHub
    GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID")
    GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET")

    # Email configuration (optional, for Flask-Security email features)
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "True").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@example.com")

    # Security headers
    SECURITY_HSTS_ENABLED = (
        os.environ.get("SECURITY_HSTS_ENABLED", "False").lower() == "true"
    )
    SECURITY_CONTENT_SECURITY_POLICY = {
        "default-src": ["'self'"],
        "script-src": ["'self'", "'unsafe-inline'"],
        "style-src": ["'self'", "'unsafe-inline'"],
    }

    # Application settings
    APP_NAME = os.environ.get("APP_NAME", "Port Scanner Delta Reporter")

    # Logging
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_DIR = BASE_DIR / "logs"

    # Scheduler
    SCHEDULER_API_ENABLED = True

    # Rate limiting (optional)
    RATELIMIT_ENABLED = os.environ.get("RATELIMIT_ENABLED", "False").lower() == "true"
    RATELIMIT_STORAGE_URL = os.environ.get("RATELIMIT_STORAGE_URL", "memory://")


def get_config_value(key):
    """Get a config value from .env"""
    from dotenv import get_key

    return get_key(ENV_FILE, key)


def update_config(new_values):
    """Update .env file with new configuration values"""
    for key, value in new_values.items():
        set_key(ENV_FILE, key, str(value))
    return True


EDITABLE_ENV_VARS = [
    ("SQLALCHEMY_DATABASE_URI", False),
    ("FLASK_ENV", False),
    ("HOST", False),
    ("PORT", False),
    ("SECRET_KEY", True),  # True = sensitive
    ("SECURITY_PASSWORD_SALT", True),
    ("ENTRA_CLIENT_ID", False),
    ("ENTRA_CLIENT_SECRET", True),
    ("ENTRA_TENANT_ID", False),
    ("MAIL_SERVER", False),
    ("MAIL_PORT", False),
    ("MAIL_USE_TLS", False),
    ("MAIL_USERNAME", False),
    ("MAIL_PASSWORD", True),
]


def get_all_env_config():
    """Get all editable env variables with masking"""
    config = {}
    for key, is_sensitive in EDITABLE_ENV_VARS:
        value = get_config_value(key)
        if is_sensitive and value:
            config[key] = "********"
        else:
            config[key] = value
    return config


def validate_and_prepare_db_path(db_uri):
    """Ensure SQLite database file exists; return False if it doesn't."""
    if db_uri.startswith("sqlite:///"):
        db_path = db_uri.replace("sqlite:///", "")
        if not os.path.isabs(db_path):
            db_path = os.path.abspath(db_path)

        # Check if the database file exists
        if not os.path.exists(db_path):
            return False
        return f"sqlite:///{db_path}"

    # For non-SQLite databases, just return the URI as-is
    return db_uri
