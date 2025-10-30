from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class User(UserMixin, db.Model):
    """User model for authentication and authorization"""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(
        db.String(255), nullable=True
    )  # Now nullable for SSO users
    first_name = db.Column(db.String(64), nullable=True)
    last_name = db.Column(db.String(64), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    current_session_token = db.Column(db.String(64), nullable=True)
    auth_provider = db.Column(db.String(50))
    # Relationships
    scans = db.relationship(
        "Scan", backref="user", lazy="dynamic", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User {self.username}>"

    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check password against hash"""
        if not self.password_hash:
            return False  # SSO users don't have passwords
        return check_password_hash(self.password_hash, password)

    def is_sso_user(self):
        """Check if user authenticates via SSO"""
        return self.auth_provider != "local"

    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()
        db.session.commit()

    def get_full_name(self):
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

    def get_active_scans(self):
        """Get user's active scans"""
        return self.scans.filter_by(is_active=True).all()

    def get_scan_count(self):
        """Get total number of scans for user"""
        return self.scans.count()

    def to_dict(self):
        """Convert user to dictionary for API responses"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.get_full_name(),
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "auth_provider": self.auth_provider,
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "scan_count": self.get_scan_count(),
        }

    @staticmethod
    def create_user(
        username,
        email,
        password=None,
        first_name=None,
        last_name=None,
        auth_provider="local",
    ):
        """Create new user with validation"""
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            raise ValueError("Username already exists")
        if User.query.filter_by(email=email).first():
            raise ValueError("Email already exists")

        if auth_provider == "local" and not password:
            raise ValueError("Password required for local authentication")

        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            auth_provider=auth_provider,
        )

        if password:
            user.set_password(password)

        db.session.add(user)
        db.session.commit()
        return user
