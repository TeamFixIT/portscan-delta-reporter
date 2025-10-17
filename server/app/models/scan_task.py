from datetime import datetime
from app import db
import json
import uuid
from app.models.scan_result import ScanResult


class ScanTask(db.Model):
    """Scan tasks to be distributed to clients"""

    __tablename__ = "scan_tasks"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(64), unique=True, nullable=False)  # Unique per task
    task_group_id = db.Column(
        db.String(64), nullable=False, index=True
    )  # Links related tasks together
    client_id = db.Column(
        db.String(64), db.ForeignKey("clients.client_id"), nullable=True
    )
    scan_id = db.Column(
        db.Integer, db.ForeignKey("scans.id"), nullable=False, index=True
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

    # Relationship to scan result
    scan_result_id = db.Column(
        db.Integer, db.ForeignKey("scan_results.id"), nullable=True
    )

    # Indexes for performance
    __table_args__ = (
        db.Index("idx_task_group_status", "task_group_id", "status"),
        db.Index("idx_scan_status", "scan_id", "status"),
    )

    def __repr__(self):
        return (
            f"<ScanTask {self.task_id} (Group: {self.task_group_id}) - {self.status}>"
        )

    def assign(self, client_id):
        """Assign task to a client"""
        self.client_id = client_id
        self.status = "assigned"
        self.assigned_at = datetime.utcnow()
        db.session.commit()

    def complete(self):
        """
        Mark task as completed and trigger delta report generation if all group tasks are done.

        Args:
            scan_result_id: The ID of the scan result created from this task
        """
        self.status = "completed"
        self.completed_at = datetime.utcnow()
        db.session.commit()

        # Check if all tasks in the group are completed
        if self.is_task_group_completed():
            print(f"✓ All tasks in group {self.task_group_id} completed!")
            print(self.scan_result_id)
            result = ScanResult.query.get(self.scan_result_id)
            if result:
                result.mark_complete()
            else:
                print(f"⚠️ ScanResult with id {self.scan_result_id} not found")
        else:
            print(
                f"⏳ Task {self.task_id} completed, waiting for other tasks in group {self.task_group_id}"
            )

    def mark_failed(self):
        """Mark task as failed"""
        self.status = "failed"
        self.completed_at = datetime.utcnow()
        db.session.commit()

    def is_task_group_completed(self):
        """
        Check if all tasks in this task group are completed.

        Returns:
            bool: True if all tasks in group are completed
        """
        # Get all tasks in this group
        group_tasks = ScanTask.query.filter_by(task_group_id=self.task_group_id).all()

        if not group_tasks:
            return False

        # Check if all are completed
        all_completed = all(task.status == "completed" for task in group_tasks)

        return all_completed

    def to_dict(self):
        """Convert scan task to dictionary"""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "task_group_id": self.task_group_id,
            "client_id": self.client_id,
            "scan_id": self.scan_id,
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
            "scan_result_id": self.scan_result_id,
        }
