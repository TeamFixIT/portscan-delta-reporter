from datetime import datetime
from app import db


class Client(db.Model):
    """Scanning client devices"""

    __tablename__ = "clients"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(64), unique=True, nullable=False)  # MAC address
    hostname = db.Column(db.String(255), nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)  # IPv4 or IPv6
    port = db.Column(
        db.Integer, nullable=False, default=8080
    )  # Port the client listens on
    scan_range = db.Column(db.String(255), nullable=False)  # e.g., '192.168.1.0/24'
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="offline")  # online, offline, scanning

    is_approved = db.Column(db.Boolean, default=False, nullable=False)
    approved_at = db.Column(db.DateTime, nullable=True)
    approved_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_hidden = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<Client {self.client_id} - {self.status} - {'Approved' if self.is_approved else 'Pending'}>"

    def approve(self, approved_by_user_id=None):
        """Approve the client"""
        try:
            import requests

            url = f"http://{self.ip_address}:{self.port}/approve"
            req = requests.post(url, timeout=5)
            req.raise_for_status()
            self.status = "online"
        except Exception as e:
            print(f"Failed to notify client of approval: {e}")

        self.is_hidden = False
        self.is_approved = True
        self.approved_at = datetime.utcnow()
        if approved_by_user_id:
            self.approved_by = approved_by_user_id
        db.session.commit()

    def revoke_approval(self):
        """Revoke client approval"""
        self.is_approved = False
        self.approved_at = None
        self.approved_by = None
        self.status = "offline"
        db.session.commit()

    def mark_online(self, ip_address=None, hostname=None):
        """Mark client as online (only if approved)"""
        if not self.is_approved:
            return False

        self.status = "online"
        self.is_hidden = False
        self.last_seen = datetime.utcnow()
        if ip_address:
            self.ip_address = ip_address
        if hostname:
            self.hostname = hostname
        db.session.commit()
        return True

    def mark_offline(self):
        self.status = "offline"
        db.session.commit()

    def mark_scanning(self):
        """Mark client as scanning (only if approved)"""
        if not self.is_approved:
            return False
        self.status = "scanning"
        db.session.commit()
        return True

    def to_dict(self):
        return {
            "id": self.id,
            "client_id": self.client_id,
            "hostname": self.hostname,
            "ip_address": self.ip_address,
            "scan_range": self.scan_range,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "status": self.status,
            "is_approved": self.is_approved,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
