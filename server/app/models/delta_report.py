from datetime import datetime
from app import db
import csv
import io
import uuid


class DeltaReport(db.Model):
    """Generated delta reports comparing scans"""

    __tablename__ = "delta_reports"

    id = db.Column(db.Integer, primary_key=True)

    # Foreign Keys
    scan_id = db.Column(db.Integer, db.ForeignKey("scans.id"), nullable=False)
    baseline_result_id = db.Column(db.Integer, db.ForeignKey("scan_results.id"))
    current_result_id = db.Column(db.Integer, db.ForeignKey("scan_results.id"))

    # Report metadata
    report_type = db.Column(db.String(20), default="delta")  # delta, aggregated_delta
    status = db.Column(
        db.String(20), default="generated"
    )  # TODO Might be redundant depending how quickly reports generate
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Summary statistics
    new_ports_count = db.Column(db.Integer, default=0)
    closed_ports_count = db.Column(db.Integer, default=0)
    changed_services_count = db.Column(db.Integer, default=0)
    new_hosts_count = db.Column(db.Integer, default=0)
    removed_hosts_count = db.Column(db.Integer, default=0)

    # Detailed delta data as JSON
    delta_data = db.Column(db.JSON)

    """ TODO Create db.json structure for delta_data
    Example structure:
    {
        {
        "scanner": {
            "name": "nmap",
            "args": "-A -T4"
        },
        "delta": {
            "new_up_hosts": [192.168.1.1],
            "new_down_hosts": [192.168.1.2],
            "added_ports": [
            {
                "port": 8080,
                "protocol": "tcp",
                "service": "http-proxy"
            }
            ],
            "removed_ports": [
            {
                "port": 22,
                "protocol": "tcp",
                "service": "ssh"
            }
            ],
            "changed_ports": [
            {
                "port": 443,
                "protocol": "tcp",
                "before": { "state": "open", "service": "https", "banner": "nginx 1.18" },
                "after":  { "state": "open", "service": "https", "banner": "nginx 1.20" }
            }
            ]
        },
        }
        """

    # Relationships
    baseline_result = db.relationship(
        "ScanResult", foreign_keys=[baseline_result_id], backref="deltas_as_baseline"
    )
    current_result = db.relationship(
        "ScanResult", foreign_keys=[current_result_id], backref="deltas_as_current"
    )
    scan = db.relationship("Scan", backref="delta_reports")

    def __repr__(self):
        return f"<DeltaReport {self.report_id} - {self.status}>"

    def has_changes(self):
        """Check if this delta report contains any changes"""
        return (
            self.new_ports_count > 0
            or self.closed_ports_count > 0
            or self.changed_services_count > 0
            or self.new_hosts_count > 0
            or self.removed_hosts_count > 0
        )

    # TODO fix up the to_csv to export a csv of the delta report.
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

    # This is for API output.
    def to_dict(self, include_delta_data=False):
        """
        Convert delta report to dictionary.

        Args:
            include_delta_data: Whether to include full delta_data (can be large)
        """
        result = {
            "id": self.id,
            "scan_id": self.scan_id,
            "baseline_result_id": self.baseline_result_id,
            "current_result_id": self.current_result_id,
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
        return result
