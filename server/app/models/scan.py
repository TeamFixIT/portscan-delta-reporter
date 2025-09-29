from datetime import datetime
from app import db
import json


class Scan(db.Model):
    """Scan configuration and schedule model"""

    __tablename__ = 'scans'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=True)
    target = db.Column(db.String(255), nullable=False)  # IP or subnet
    ports = db.Column(db.String(255), nullable=False)   # Port specification
    scan_arguments = db.Column(db.String(255), default='-sV')
    interval_minutes = db.Column(db.Integer, default=60)  # Scan interval
    is_active = db.Column(db.Boolean, default=True)
    is_scheduled = db.Column(db.Boolean, default=False)
    last_run = db.Column(db.DateTime, nullable=True)
    next_run = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    results = db.relationship('ScanResult', backref='scan', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Scan {self.name} ({self.target})>'

    def get_latest_result(self):
        """Get the most recent scan result"""
        return self.results.order_by(ScanResult.created_at.desc()).first()

    def get_result_count(self):
        """Get total number of results for this scan"""
        return self.results.count()

    def get_success_rate(self):
        """Calculate scan success rate"""
        total = self.get_result_count()
        if total == 0:
            return 0
        successful = self.results.filter_by(status='completed').count()
        return (successful / total) * 100

    def update_last_run(self):
        """Update last run timestamp"""
        self.last_run = datetime.utcnow()
        db.session.commit()

    def to_dict(self):
        """Convert scan to dictionary"""
        latest_result = self.get_latest_result()
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'target': self.target,
            'ports': self.ports,
            'scan_arguments': self.scan_arguments,
            'interval_minutes': self.interval_minutes,
            'is_active': self.is_active,
            'is_scheduled': self.is_scheduled,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'next_run': self.next_run.isoformat() if self.next_run else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'result_count': self.get_result_count(),
            'success_rate': self.get_success_rate(),
            'latest_result': latest_result.to_dict() if latest_result else None
        }
