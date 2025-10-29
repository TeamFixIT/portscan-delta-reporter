"""
User model for Flask-Security-Too
"""

from flask_security import UserMixin, RoleMixin

from app import db

roles_users = db.Table(
    "roles_users",
    db.Column("user_id", db.Integer(), db.ForeignKey("user.id")),
    db.Column("role_id", db.Integer(), db.ForeignKey("role.id")),
)


class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    username = db.Column(db.String(255), unique=True, nullable=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean(), default=True)
    fs_uniquifier = db.Column(db.String(255), unique=True, nullable=False)

    # Profile fields
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    azure_id = db.Column(db.String(255), unique=True, nullable=True)

    roles = db.relationship(
        "Role", secondary=roles_users, backref=db.backref("users", lazy="dynamic")
    )

    scans = db.relationship(
        "Scan", backref="user", lazy="dynamic", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User {self.username}>"

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
