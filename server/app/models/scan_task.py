from datetime import datetime
from app import db
import json


class ScanTask(db.Model):
    """Scan tasks to be distributed to clients"""

    __tablename__ = "scan_tasks"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(64), unique=True, nullable=False)
    client_id = db.Column(
        db.String(64), db.ForeignKey("clients.client_id"), nullable=True
    )
    scan_id = db.Column(
        db.Integer, db.ForeignKey("scans.id"), nullable=True
    )  # Foreign key to Scan
    targets = db.Column(db.Text, nullable=False)  # JSON array of targets
    ports = db.Column(db.String(255), default="1-1000")
    scan_type = db.Column(db.String(20), default="tcp")
    priority = db.Column(db.Integer, default=5)  # 1=highest, 10=lowest
    status = db.Column(
        db.String(20), default="pending"
    )  # pending, assigned, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    assigned_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)

    def __repr__(self):
        return f"<ScanTask {self.task_id} - {self.status}>"

    def assign(self, client_id):
        self.client_id = client_id
        self.status = "assigned"
        self.assigned_at = datetime.utcnow()
        db.session.commit()

    def complete(self):
        self.status = "completed"
        self.completed_at = datetime.utcnow()
        db.session.commit()

    def fail(self):
        self.status = "failed"
        self.completed_at = datetime.utcnow()
        db.session.commit()

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "client_id": self.client_id,
            "targets": json.loads(self.targets) if self.targets else [],
            "ports": self.ports,
            "scan_type": self.scan_type,
            "priority": self.priority,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
        }
