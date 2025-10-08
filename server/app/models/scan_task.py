from datetime import datetime
from app import db
import json
import uuid


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

    def complete(self, scan_result_id=None):
        """
        Mark task as completed and trigger delta report generation if all group tasks are done.

        Args:
            scan_result_id: The ID of the scan result created from this task
        """
        self.status = "completed"
        self.completed_at = datetime.utcnow()
        if scan_result_id:
            self.scan_result_id = scan_result_id
        db.session.commit()
        return

        # TODO implement generate_delta_report
        # Check if all tasks in the group are completed
        if self.is_task_group_completed():
            print(f"✓ All tasks in group {self.task_group_id} completed!")
            self.generate_delta_report()
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

    def get_task_group_tasks(self):
        """
        Get all tasks in this task group.

        Returns:
            list: List of ScanTask objects in the same group
        """
        return (
            ScanTask.query.filter_by(task_group_id=self.task_group_id)
            .order_by(ScanTask.created_at)
            .all()
        )

    def get_task_group_results(self):
        """
        Get all scan results from tasks in this group.

        Returns:
            list: List of ScanResult objects from this task group
        """
        from app.models.scan_result import ScanResult

        group_tasks = self.get_task_group_tasks()

        # Get all scan results that have a completed status
        results = []
        for task in group_tasks:
            if task.scan_result_id:
                result = ScanResult.query.get(task.scan_result_id)
                if result and result.status == "completed":
                    results.append(result)

        return results

    def get_previous_task_group_id(self):
        """
        Find the task_group_id of the previous completed task group for this scan.

        Returns:
            str: Previous task_group_id or None if this is the first
        """
        # Find all task groups for this scan that completed before this one
        previous_groups = (
            db.session.query(
                ScanTask.task_group_id,
                db.func.max(ScanTask.completed_at).label("max_completed"),
            )
            .filter(
                ScanTask.scan_id == self.scan_id,
                ScanTask.task_group_id != self.task_group_id,
                ScanTask.status == "completed",
                ScanTask.completed_at < self.completed_at,
            )
            .group_by(ScanTask.task_group_id)
            .order_by(db.desc("max_completed"))
            .first()
        )

        if previous_groups:
            return previous_groups.task_group_id

        return None

    @staticmethod
    def aggregate_scan_results(scan_results):
        """
        Aggregate multiple scan results into a single results_data structure.
        Combines hosts and ports from all results.

        Args:
            scan_results: List of ScanResult objects

        Returns:
            dict: Aggregated results_data in the format expected by compare_with()
        """
        aggregated = {"hosts": {}}

        for result in scan_results:
            if not result.results_data:
                continue

            result_hosts = result.results_data.get("hosts", {})

            for host_ip, host_data in result_hosts.items():
                if host_ip not in aggregated["hosts"]:
                    # First time seeing this host
                    aggregated["hosts"][host_ip] = {"ports": []}

                # Merge ports (avoid duplicates)
                existing_ports = {
                    p["port"]: p for p in aggregated["hosts"][host_ip]["ports"]
                }

                for port_info in host_data.get("ports", []):
                    port_num = port_info.get("port")
                    if port_num:
                        # Keep the most recent/complete information
                        if port_num not in existing_ports or len(
                            str(port_info.get("service", ""))
                        ) > len(str(existing_ports[port_num].get("service", ""))):
                            existing_ports[port_num] = port_info

                # Convert back to list
                aggregated["hosts"][host_ip]["ports"] = list(existing_ports.values())

        return aggregated

    @staticmethod
    def create_task_group(
        scan_id, client_ranges, ports="1-1000", scan_type="tcp", priority=5
    ):
        """
        Create a group of related scan tasks for multiple clients.
        All tasks in the group share the same task_group_id.

        Args:
            scan_id: The scan ID these tasks belong to
            client_ranges: List of dicts with 'client_id' and 'targets'
                          Example: [
                              {'client_id': 'client1', 'targets': ['192.168.1.0/25']},
                              {'client_id': 'client2', 'targets': ['192.168.1.128/25']}
                          ]
            ports: Port specification
            scan_type: Type of scan
            priority: Priority level

        Returns:
            tuple: (task_group_id, list of created ScanTask objects)
        """
        # Generate a unique task_group_id for this execution
        task_group_id = str(uuid.uuid4())

        tasks = []

        for client_range in client_ranges:
            task = ScanTask(
                task_id=str(uuid.uuid4()),
                task_group_id=task_group_id,
                client_id=client_range.get("client_id"),
                scan_id=scan_id,
                targets=json.dumps(client_range.get("targets", [])),
                ports=ports,
                scan_type=scan_type,
                priority=priority,
                status="pending",
            )
            tasks.append(task)
            db.session.add(task)

        db.session.commit()

        print(f"✓ Created task group {task_group_id} with {len(tasks)} tasks")

        return task_group_id, tasks

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
