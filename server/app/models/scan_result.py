from datetime import datetime
from app import db

class ScanResult(db.Model):
    """Scan result model to store scan outputs"""

    __tablename__ = 'scan_results'

    id = db.Column(db.Integer, primary_key=True)
    scan_id = db.Column(db.Integer, db.ForeignKey('scans.id'), nullable=False)
    status = db.Column(db.String(32), default='pending')  # pending, running, completed, failed
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    duration_seconds = db.Column(db.Float, nullable=True)

    # Scan results data
    hosts_found = db.Column(db.Integer, default=0)
    ports_found = db.Column(db.Integer, default=0)
    services_found = db.Column(db.Integer, default=0)

    # JSON fields for detailed results
    results_data = db.Column(db.JSON)  # Stores the complete scan results
    error_message = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ScanResult {self.id} - {self.status}>'

    def mark_completed(self, results_data):
        """Mark scan as completed with results"""
        self.status = 'completed'
        self.end_time = datetime.utcnow()
        self.duration_seconds = (self.end_time - self.start_time).total_seconds()
        self.results_data = results_data

        # Calculate summary statistics
        if results_data and isinstance(results_data, dict):
            results = results_data.get('results', [])
            self.hosts_found = len(results)
            self.ports_found = sum(len(r.get('ports', [])) for r in results)
            self.services_found = len(set(
                p.get('service', '') for r in results
                for p in r.get('ports', [])
                if p.get('state') == 'open' and p.get('service')
            ))

        db.session.commit()

    def mark_failed(self, error_message):
        """Mark scan as failed with error message"""
        self.status = 'failed'
        self.end_time = datetime.utcnow()
        self.duration_seconds = (self.end_time - self.start_time).total_seconds()
        self.error_message = error_message
        db.session.commit()

    def mark_running(self):
        """Mark scan as currently running"""
        self.status = 'running'
        db.session.commit()

    def get_summary(self):
        """Get scan result summary"""
        if not self.results_data:
            return {}

        results = self.results_data.get('results', [])
        active_hosts = [r for r in results if r.get('state') == 'up']
        open_ports = []
        services = {}

        for result in results:
            for port in result.get('ports', []):
                if port.get('state') == 'open':
                    open_ports.append(port)
                    service = port.get('service', 'unknown')
                    services[service] = services.get(service, 0) + 1

        return {
            'total_hosts': len(results),
            'active_hosts': len(active_hosts),
            'total_open_ports': len(open_ports),
            'unique_services': len(services),
            'top_services': dict(sorted(services.items(), key=lambda x: x[1], reverse=True)[:5])
        }

    def to_dict(self):
        """Convert scan result to dictionary"""
        return {
            'id': self.id,
            'scan_id': self.scan_id,
            'status': self.status,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration_seconds,
            'hosts_found': self.hosts_found,
            'ports_found': self.ports_found,
            'services_found': self.services_found,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat(),
            'summary': self.get_summary() if self.status == 'completed' else {}
        }
