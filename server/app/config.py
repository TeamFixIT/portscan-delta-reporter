import os
from dotenv import load_dotenv, set_key
from pathlib import Path

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
    SESSION_TYPE = os.getenv("SESSION_TYPE", "filesystem")
    SESSION_FILE_DIR = os.getenv("SESSION_FILE_DIR", "/tmp/flask_session")

    # Email, and Entra ID configs
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
    # ... other configs


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
