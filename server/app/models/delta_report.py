from datetime import datetime
from app import db

class DeltaReport(db.Model):
    """Generated delta reports comparing scans"""
    __tablename__ = 'delta_reports'

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.String(64), unique=True, nullable=False)
    baseline_scan_id = db.Column(db.String(64), nullable=False)
    current_scan_id = db.Column(db.String(64), nullable=False)
    target_mac = db.Column(db.String(17), nullable=False)  # MAC address for tracking
    report_type = db.Column(db.String(20), default='delta')  # delta, full, summary
    status = db.Column(db.String(20), default='generated')
    file_path = db.Column(db.String(500))  # Path to generated report file
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Summary statistics
    new_ports_count = db.Column(db.Integer, default=0)
    closed_ports_count = db.Column(db.Integer, default=0)
    changed_services_count = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'<DeltaReport {self.report_id} - {self.status}>'

    def to_dict(self):
        return {
            'id': self.id,
            'report_id': self.report_id,
            'baseline_scan_id': self.baseline_scan_id,
            'current_scan_id': self.current_scan_id,
            'target_mac': self.target_mac,
            'report_type': self.report_type,
            'status': self.status,
            'file_path': self.file_path,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'new_ports_count': self.new_ports_count,
            'closed_ports_count': self.closed_ports_count,
            'changed_services_count': self.changed_services_count
        }
