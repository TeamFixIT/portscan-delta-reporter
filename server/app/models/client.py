from datetime import datetime
from app import db


class Client(db.Model):
    """Scanning client devices (Raspberry Pi 4s)"""

    __tablename__ = "clients"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(64), unique=True, nullable=False)  # MAC address
    hostname = db.Column(db.String(255))
    ip_address = db.Column(db.String(45))  # IPv4 or IPv6
    scan_range = db.Column(
        db.String(255), nullable=True
    )  # e.g., '192.168.1.0/24' or port range
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="offline")  # online, offline, scanning
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    scan_results = db.relationship("ScanResult", backref="client", lazy=True)

    def __repr__(self):
        return f"<Client {self.client_id} - {self.status}>"

    def mark_online(self, ip_address=None, hostname=None):
        self.status = "online"
        self.last_seen = datetime.utcnow()
        if ip_address:
            self.ip_address = ip_address
        if hostname:
            self.hostname = hostname
        db.session.commit()

    def mark_offline(self):
        self.status = "offline"
        db.session.commit()

    def mark_scanning(self):
        self.status = "scanning"
        db.session.commit()

    def to_dict(self):
        return {
            "id": self.id,
            "client_id": self.client_id,
            "hostname": self.hostname,
            "ip_address": self.ip_address,
            "scan_range": self.scan_range,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "scan_results": [sr.id for sr in self.scan_results],
        }
