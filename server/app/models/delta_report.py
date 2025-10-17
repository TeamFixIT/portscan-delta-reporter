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
        return f"<DeltaReport {self.id} - {self.status}>"

    def has_changes(self):
        """Check if this delta report contains any changes"""
        return (
            self.new_ports_count > 0
            or self.closed_ports_count > 0
            or self.changed_services_count > 0
            or self.new_hosts_count > 0
            or self.removed_hosts_count > 0
        )

    def to_dict(self, include_delta_data=False):
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

        # ADD THIS:
        if include_delta_data:
            result["delta_data"] = self.delta_data

        return result
