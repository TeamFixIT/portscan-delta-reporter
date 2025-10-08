from datetime import datetime
from app import db
import json


class Scan(db.Model):
    """Scan configuration and schedule model"""

    __tablename__ = "scans"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=True)
    target = db.Column(db.String(255), nullable=False)  # IP or subnet
    ports = db.Column(db.String(255), nullable=False)  # Port specification
    scan_arguments = db.Column(db.String(255), default="-sV")
    interval_minutes = db.Column(db.Integer, default=60)  # Scan interval
    is_active = db.Column(db.Boolean, default=True)
    is_scheduled = db.Column(db.Boolean, default=False)
    last_run = db.Column(db.DateTime, nullable=True)
    next_run = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    tasks = db.relationship("ScanTask", backref="scan", lazy=True)
    results = db.relationship("ScanResult", backref="scan", lazy=True)

    def __repr__(self):
        return f"<Scan {self.name} ({self.target})>"

    def get_latest_result(self):
        """Get the most recent result for this scan"""
        if not self.results:
            return None
        # Filter out results with no started_at, just in case
        results_with_time = [r for r in self.results if getattr(r, "started_at", None)]
        if not results_with_time:
            return None
        # Sort by started_at descending and return the first
        return sorted(results_with_time, key=lambda r: r.started_at, reverse=True)[0]

    def get_completed_results(self, limit=None):
        """
        Get completed scan results ordered by started_at descending.

        Args:
            limit: Maximum number of results to return (None for all)

        Returns:
            list: List of completed ScanResult objects
        """
        completed = [
            r for r in self.results if r.status == "completed" and r.started_at
        ]
        completed_sorted = sorted(completed, key=lambda r: r.started_at, reverse=True)

        if limit:
            return completed_sorted[:limit]
        return completed_sorted

    def get_previous_result(self, before_result):
        """
        Get the scan result that occurred before the given result.

        Args:
            before_result: ScanResult to find the previous result for

        Returns:
            ScanResult: The previous completed result, or None
        """
        completed = self.get_completed_results()

        # Find the index of before_result
        try:
            idx = completed.index(before_result)
            if idx + 1 < len(completed):
                return completed[idx + 1]
        except ValueError:
            pass

        return None

    def generate_delta_report_for_result(self, current_result):
        """
        Generate a delta report for a specific scan result by comparing
        it with the previous completed result.

        Args:
            current_result: The current ScanResult to generate report for

        Returns:
            DeltaReport: The generated report, or None if no previous result
        """
        from app.models.delta_report import DeltaReport

        if current_result.status != "completed":
            return None

        # Get the previous completed result
        baseline_result = self.get_previous_result(current_result)

        if not baseline_result:
            # This is the first scan, no baseline to compare
            return None

        # Generate and return the delta report
        return DeltaReport.generate_from_results(
            scan_id=self.id,
            baseline_result=baseline_result,
            current_result=current_result,
        )

    def auto_generate_delta_report(self):
        """
        Automatically generate a delta report for the latest completed scan.
        This should be called after a scan completes.

        Returns:
            DeltaReport: The generated report, or None if conditions not met
        """
        latest_result = self.get_latest_result()

        if not latest_result or latest_result.status != "completed":
            return None

        # Check if we already have a delta report for this result
        from app.models.delta_report import DeltaReport

        existing = DeltaReport.query.filter_by(
            current_result_id=latest_result.id
        ).first()

        if existing:
            # Already generated
            return existing

        return self.generate_delta_report_for_result(latest_result)

    def get_delta_reports(self, page=1, per_page=10, only_with_changes=False):
        """
        Get paginated delta reports for this scan.

        Args:
            page: Page number (1-indexed)
            per_page: Number of reports per page
            only_with_changes: If True, only return reports with changes

        Returns:
            dict: Pagination info and reports list
        """
        from app.models.delta_report import DeltaReport

        query = DeltaReport.query.filter_by(scan_id=self.id).order_by(
            DeltaReport.created_at.desc()
        )

        if only_with_changes:
            # Filter for reports with any changes
            query = query.filter(
                db.or_(
                    DeltaReport.new_ports_count > 0,
                    DeltaReport.closed_ports_count > 0,
                    DeltaReport.changed_services_count > 0,
                    DeltaReport.new_hosts_count > 0,
                    DeltaReport.removed_hosts_count > 0,
                )
            )

        paginated = query.paginate(page=page, per_page=per_page, error_out=False)

        return {
            "reports": [report.to_dict() for report in paginated.items],
            "total": paginated.total,
            "pages": paginated.pages,
            "current_page": paginated.page,
            "per_page": per_page,
            "has_next": paginated.has_next,
            "has_prev": paginated.has_prev,
        }

    def get_result_count(self):
        """Get total number of results for this scan"""
        return len(self.results)

    def get_success_rate(self):
        """Calculate scan success rate"""
        total = self.get_result_count()
        if total == 0:
            return 0
        successful = sum(
            1 for r in self.results if getattr(r, "status", None) == "completed"
        )
        return (successful / total) * 100

    def update_last_run(self):
        """Update last run timestamp"""
        self.last_run = datetime.utcnow()
        db.session.commit()

    def to_dict(self, include_latest_delta=False):
        """
        Convert scan to dictionary.

        Args:
            include_latest_delta: Whether to include latest delta report info
        """
        result = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "target": self.target,
            "ports": self.ports,
            "scan_arguments": self.scan_arguments,
            "interval_minutes": self.interval_minutes,
            "is_active": self.is_active,
            "is_scheduled": self.is_scheduled,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "result_count": self.get_result_count(),
            "success_rate": self.get_success_rate(),
        }

        if include_latest_delta:
            from app.models.delta_report import DeltaReport

            latest_delta = (
                DeltaReport.query.filter_by(scan_id=self.id)
                .order_by(DeltaReport.created_at.desc())
                .first()
            )

            result["latest_delta_report"] = (
                latest_delta.to_dict() if latest_delta else None
            )

        return result
