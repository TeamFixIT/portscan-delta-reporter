from datetime import datetime
from app import db
import csv
import io
import uuid


class DeltaReport(db.Model):
    """Generated delta reports comparing scans"""

    __tablename__ = "delta_reports"

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(
        db.String(64), unique=True, nullable=False, default=lambda: str(uuid.uuid4())
    )

    # Foreign Keys
    scan_id = db.Column(db.Integer, db.ForeignKey("scans.id"), nullable=False)
    baseline_result_id = db.Column(
        db.Integer, db.ForeignKey("scan_results.id"), nullable=True
    )  # Nullable for aggregated
    current_result_id = db.Column(
        db.Integer, db.ForeignKey("scan_results.id"), nullable=True
    )  # Nullable for aggregated

    # Task group tracking for distributed scans
    baseline_task_group_id = db.Column(db.String(64), nullable=True, index=True)
    current_task_group_id = db.Column(db.String(64), nullable=True, index=True)

    # Report metadata
    report_type = db.Column(db.String(20), default="delta")  # delta, aggregated_delta
    status = db.Column(db.String(20), default="generated")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Summary statistics
    new_ports_count = db.Column(db.Integer, default=0)
    closed_ports_count = db.Column(db.Integer, default=0)
    changed_services_count = db.Column(db.Integer, default=0)
    new_hosts_count = db.Column(db.Integer, default=0)
    removed_hosts_count = db.Column(db.Integer, default=0)

    # Detailed delta data as JSON
    delta_data = db.Column(db.JSON)

    # Relationships
    baseline_result = db.relationship(
        "ScanResult", foreign_keys=[baseline_result_id], backref="deltas_as_baseline"
    )
    current_result = db.relationship(
        "ScanResult", foreign_keys=[current_result_id], backref="deltas_as_current"
    )
    scan = db.relationship("Scan", backref="delta_reports")

    # Indexes for performance
    __table_args__ = (
        db.Index("idx_delta_scan_id", "scan_id"),
        db.Index("idx_delta_created_at", "created_at"),
        db.Index("idx_delta_current_result", "current_result_id"),
        db.Index(
            "idx_delta_task_groups", "baseline_task_group_id", "current_task_group_id"
        ),
        db.Index(
            "idx_delta_has_changes",
            "new_ports_count",
            "closed_ports_count",
            "changed_services_count",
            "new_hosts_count",
            "removed_hosts_count",
        ),
    )

    def __repr__(self):
        return f"<DeltaReport {self.report_id} - {self.status}>"

    @staticmethod
    def generate_from_results(scan_id, baseline_result, current_result):
        """
        Generate a delta report by comparing two scan results.

        Args:
            scan_id: ID of the parent scan
            baseline_result: Previous ScanResult to compare from
            current_result: Current ScanResult to compare to

        Returns:
            DeltaReport: The generated report, or None if comparison failed
        """
        if not baseline_result or not current_result:
            return None

        if (
            baseline_result.status != "completed"
            or current_result.status != "completed"
        ):
            return None

        # Generate delta data
        delta_data = current_result.compare_with(baseline_result)

        if not delta_data:
            return None

        # Create the report
        report = DeltaReport(
            report_id=str(uuid.uuid4()),
            scan_id=scan_id,
            baseline_result_id=baseline_result.id,
            current_result_id=current_result.id,
            report_type="delta",
            delta_data=delta_data,
            new_ports_count=delta_data["summary"]["total_new_ports"],
            closed_ports_count=delta_data["summary"]["total_closed_ports"],
            changed_services_count=delta_data["summary"]["total_changed_services"],
            new_hosts_count=delta_data["summary"]["total_new_hosts"],
            removed_hosts_count=delta_data["summary"]["total_removed_hosts"],
            status="generated",
        )

        db.session.add(report)
        db.session.commit()

        return report

    @staticmethod
    def generate_from_aggregated_results(
        scan_id,
        baseline_result,
        current_result,
        baseline_task_group_id=None,
        current_task_group_id=None,
    ):
        """
        Generate a delta report from aggregated scan results (distributed scanning).
        This is used when multiple clients scan different ranges and results need to be combined.

        Args:
            scan_id: ID of the parent scan
            baseline_result: Aggregated baseline ScanResult (can be temporary object)
            current_result: Aggregated current ScanResult (can be temporary object)
            baseline_task_group_id: Task group ID for baseline
            current_task_group_id: Task group ID for current

        Returns:
            DeltaReport: The generated report, or None if comparison failed
        """
        if not baseline_result or not current_result:
            return None

        # Generate delta data
        delta_data = current_result.compare_with(baseline_result)

        if not delta_data:
            return None

        # Check if a report already exists for this task group pair
        existing = DeltaReport.query.filter_by(
            baseline_task_group_id=baseline_task_group_id,
            current_task_group_id=current_task_group_id,
        ).first()

        if existing:
            print(
                f"ℹ️ Delta report already exists for task groups {baseline_task_group_id} → {current_task_group_id}"
            )
            return existing

        # Create the report
        report = DeltaReport(
            report_id=str(uuid.uuid4()),
            scan_id=scan_id,
            baseline_result_id=None,  # Aggregated, no single result
            current_result_id=None,  # Aggregated, no single result
            baseline_task_group_id=baseline_task_group_id,
            current_task_group_id=current_task_group_id,
            report_type="aggregated_delta",
            delta_data=delta_data,
            new_ports_count=delta_data["summary"]["total_new_ports"],
            closed_ports_count=delta_data["summary"]["total_closed_ports"],
            changed_services_count=delta_data["summary"]["total_changed_services"],
            new_hosts_count=delta_data["summary"]["total_new_hosts"],
            removed_hosts_count=delta_data["summary"]["total_removed_hosts"],
            status="generated",
        )

        db.session.add(report)
        db.session.commit()

        return report

    def has_changes(self):
        """Check if this delta report contains any changes"""
        return (
            self.new_ports_count > 0
            or self.closed_ports_count > 0
            or self.changed_services_count > 0
            or self.new_hosts_count > 0
            or self.removed_hosts_count > 0
        )

    def get_task_groups_info(self):
        """
        Get information about the task groups involved in this report.

        Returns:
            dict: Information about baseline and current task groups
        """
        from app.models.scan_task import ScanTask

        info = {"baseline": None, "current": None}

        if self.baseline_task_group_id:
            baseline_tasks = ScanTask.query.filter_by(
                task_group_id=self.baseline_task_group_id
            ).all()
            info["baseline"] = {
                "task_group_id": self.baseline_task_group_id,
                "task_count": len(baseline_tasks),
                "clients": list(
                    set(t.client_id for t in baseline_tasks if t.client_id)
                ),
                "completed_at": max(
                    (t.completed_at for t in baseline_tasks if t.completed_at),
                    default=None,
                ),
            }

        if self.current_task_group_id:
            current_tasks = ScanTask.query.filter_by(
                task_group_id=self.current_task_group_id
            ).all()
            info["current"] = {
                "task_group_id": self.current_task_group_id,
                "task_count": len(current_tasks),
                "clients": list(set(t.client_id for t in current_tasks if t.client_id)),
                "completed_at": max(
                    (t.completed_at for t in current_tasks if t.completed_at),
                    default=None,
                ),
            }

        return info

    def to_csv(self):
        """
        Export delta report as CSV string.
        Returns a CSV with separate sections for different change types.
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(["Delta Report"])
        writer.writerow(["Report ID", self.report_id])
        writer.writerow(["Report Type", self.report_type])
        writer.writerow(["Scan ID", self.scan_id])
        writer.writerow(["Generated", self.created_at.isoformat()])

        # Add task group info if available
        if self.baseline_task_group_id or self.current_task_group_id:
            task_info = self.get_task_groups_info()
            writer.writerow([])
            writer.writerow(["=== TASK GROUP INFORMATION ==="])

            if task_info["baseline"]:
                writer.writerow(["Baseline Task Group", self.baseline_task_group_id])
                writer.writerow(["Baseline Tasks", task_info["baseline"]["task_count"]])
                writer.writerow(
                    ["Baseline Clients", ", ".join(task_info["baseline"]["clients"])]
                )

            if task_info["current"]:
                writer.writerow(["Current Task Group", self.current_task_group_id])
                writer.writerow(["Current Tasks", task_info["current"]["task_count"]])
                writer.writerow(
                    ["Current Clients", ", ".join(task_info["current"]["clients"])]
                )
        elif self.baseline_result and self.current_result:
            writer.writerow(
                ["Baseline Scan", self.baseline_result.start_time.isoformat()]
            )
            writer.writerow(
                ["Current Scan", self.current_result.start_time.isoformat()]
            )

        writer.writerow([])

        # Summary section
        writer.writerow(["=== SUMMARY ==="])
        writer.writerow(["New Hosts", self.new_hosts_count])
        writer.writerow(["Removed Hosts", self.removed_hosts_count])
        writer.writerow(["New Ports", self.new_ports_count])
        writer.writerow(["Closed Ports", self.closed_ports_count])
        writer.writerow(["Changed Services", self.changed_services_count])
        writer.writerow([])

        if not self.delta_data:
            writer.writerow(["No delta data available"])
            return output.getvalue()

        # New hosts section
        if self.delta_data.get("new_hosts"):
            writer.writerow(["=== NEW HOSTS ==="])
            writer.writerow(["Host IP"])
            for host in self.delta_data["new_hosts"]:
                writer.writerow([host])
            writer.writerow([])

        # Removed hosts section
        if self.delta_data.get("removed_hosts"):
            writer.writerow(["=== REMOVED HOSTS ==="])
            writer.writerow(["Host IP"])
            for host in self.delta_data["removed_hosts"]:
                writer.writerow([host])
            writer.writerow([])

        # Host changes section
        if self.delta_data.get("host_changes"):
            writer.writerow(["=== HOST CHANGES ==="])

            for host_ip, changes in self.delta_data["host_changes"].items():
                writer.writerow([f"Host: {host_ip}"])
                writer.writerow([])

                # New ports for this host
                if changes.get("new_ports"):
                    writer.writerow(["  New Ports:"])
                    writer.writerow(
                        ["  Port", "State", "Service", "Version", "Product"]
                    )
                    for port in changes["new_ports"]:
                        writer.writerow(
                            [
                                f"  {port.get('port', '')}",
                                port.get("state", ""),
                                port.get("service", ""),
                                port.get("version", ""),
                                port.get("product", ""),
                            ]
                        )
                    writer.writerow([])

                # Closed ports for this host
                if changes.get("closed_ports"):
                    writer.writerow(["  Closed Ports:"])
                    writer.writerow(
                        ["  Port", "State", "Service", "Version", "Product"]
                    )
                    for port in changes["closed_ports"]:
                        writer.writerow(
                            [
                                f"  {port.get('port', '')}",
                                port.get("state", ""),
                                port.get("service", ""),
                                port.get("version", ""),
                                port.get("product", ""),
                            ]
                        )
                    writer.writerow([])

                # Changed ports for this host
                if changes.get("changed_ports"):
                    writer.writerow(["  Changed Ports:"])
                    writer.writerow(["  Port", "Change Type", "Old Value", "New Value"])
                    for port_change in changes["changed_ports"]:
                        port_num = port_change.get("port", "")
                        for change_type, change_vals in port_change.get(
                            "changes", {}
                        ).items():
                            writer.writerow(
                                [
                                    f"  {port_num}",
                                    change_type.capitalize(),
                                    change_vals.get("old", ""),
                                    change_vals.get("new", ""),
                                ]
                            )
                    writer.writerow([])

                writer.writerow([])

        return output.getvalue()

    def to_dict(self, include_delta_data=False):
        """
        Convert delta report to dictionary.

        Args:
            include_delta_data: Whether to include full delta_data (can be large)
        """
        result = {
            "id": self.id,
            "report_id": self.report_id,
            "scan_id": self.scan_id,
            "baseline_result_id": self.baseline_result_id,
            "current_result_id": self.current_result_id,
            "baseline_task_group_id": self.baseline_task_group_id,
            "current_task_group_id": self.current_task_group_id,
            "report_type": self.report_type,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "new_ports_count": self.new_ports_count,
            "closed_ports_count": self.closed_ports_count,
            "changed_services_count": self.changed_services_count,
            "new_hosts_count": self.new_hosts_count,
            "removed_hosts_count": self.removed_hosts_count,
            "has_changes": self.has_changes(),
        }

        # Add scan times based on report type
        if self.report_type == "aggregated_delta" and (
            self.baseline_task_group_id or self.current_task_group_id
        ):
            task_info = self.get_task_groups_info()
            if task_info["baseline"] and task_info["baseline"]["completed_at"]:
                result["baseline_scan_time"] = task_info["baseline"][
                    "completed_at"
                ].isoformat()
            if task_info["current"] and task_info["current"]["completed_at"]:
                result["current_scan_time"] = task_info["current"][
                    "completed_at"
                ].isoformat()
        else:
            result["baseline_scan_time"] = (
                self.baseline_result.start_time.isoformat()
                if self.baseline_result
                else None
            )
            result["current_scan_time"] = (
                self.current_result.start_time.isoformat()
                if self.current_result
                else None
            )

        if include_delta_data:
            result["delta_data"] = self.delta_data
            result["task_groups_info"] = self.get_task_groups_info()

        return result
