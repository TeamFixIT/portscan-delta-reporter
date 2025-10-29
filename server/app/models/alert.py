# models/alert.py
from datetime import datetime
from app import db


class Alert(db.Model):
    __tablename__ = "alerts"

    id = db.Column(db.Integer, primary_key=True)
    device_ip = db.Column(db.String(64), nullable=False)
    port = db.Column(db.Integer, nullable=False)
    service = db.Column(db.String(128))
    criticality = db.Column(
        db.String(32), default="medium"
    )  # low, medium, high, critical
    message = db.Column(db.Text, nullable=False)

    status = db.Column(
        db.String(32), default="warned"
    )  # warned, actioned, ignored, resolved
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    resolved_at = db.Column(db.DateTime, nullable=True)

    scan_result_id = db.Column(db.String(36), db.ForeignKey("scan_results.id"))

    def mark_actioned(self):
        self.status = "actioned"
        self.last_updated = datetime.utcnow()

    def mark_ignored(self):
        self.status = "ignored"
        self.last_updated = datetime.utcnow()

    def mark_resolved(self):
        self.status = "resolved"
        self.resolved_at = datetime.utcnow()
        self.last_updated = datetime.utcnow()
