"""
Delta Report Service Layer

This service provides business logic for delta report management,
including notifications, batch operations, and advanced filtering.
"""

# TODO For Andrew - create this generate_delta_report function to create delta reports when a scan result is completed utilizing the model in delta_report.py
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import or_, and_
from app import db
from app.models.scan import Scan
from app.models.scan_result import ScanResult
from app.models.delta_report import DeltaReport
from app.models.user import User


class DeltaReportService:
    """Service for managing delta reports"""

    @staticmethod
    def generate_delta_report(current_result_id: int) -> Optional[DeltaReport]:
        """
        Generate a delta report for this result:
        Returns:
            DeltaReport: Generated report or None
        """
        from app.models.scan import Scan
        from app.models.delta_report import DeltaReport
        from app.models.scan_result import ScanResult

        # TODO implement generate_delta_report, need to get current_result first find previous results to compare against

        scan_result = ScanResult.query.get(current_result_id)

        if not scan_result or scan_result.status != "completed":
            return None

        existing = DeltaReport.query.filter_by(
            current_result_id=current_result_id
        ).first()

        if existing:
            # Already generated
            return existing

        # Generate delta report using the aggregated data
        print("🔄 Comparing aggregated results...")
        delta_report = DeltaReport.generate_from_results()

        if delta_report:
            print(f"✅ Delta report generated: {delta_report.report_id}")
            print(
                f"   Changes: {delta_report.new_ports_count} new ports, "
                f"{delta_report.closed_ports_count} closed ports, "
                f"{delta_report.new_hosts_count} new hosts"
            )
        else:
            print("⚠️ Delta report generation failed")

        return delta_report

    @staticmethod
    def get_reports_by_user(
        user_id: int,
        page: int = 1,
        per_page: int = 10,
        only_changes: bool = False,
        scan_id: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get delta reports for a user with advanced filtering.

        Args:
            user_id: User ID to filter by
            page: Page number
            per_page: Items per page
            only_changes: Only show reports with changes
            scan_id: Filter by specific scan
            date_from: Start date filter
            date_to: End date filter

        Returns:
            dict: Paginated results with reports
        """
        # Build query
        query = db.session.query(DeltaReport).join(Scan).filter(Scan.user_id == user_id)

        # Apply filters
        if scan_id:
            query = query.filter(DeltaReport.scan_id == scan_id)

        if only_changes:
            query = query.filter(
                or_(
                    DeltaReport.new_ports_count > 0,
                    DeltaReport.closed_ports_count > 0,
                    DeltaReport.changed_services_count > 0,
                    DeltaReport.new_hosts_count > 0,
                    DeltaReport.removed_hosts_count > 0,
                )
            )

        if date_from:
            query = query.filter(DeltaReport.created_at >= date_from)

        if date_to:
            query = query.filter(DeltaReport.created_at <= date_to)

        # Order by most recent
        query = query.order_by(DeltaReport.created_at.desc())

        # Paginate
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)

        return {
            "reports": [r.to_dict() for r in paginated.items],
            "total": paginated.total,
            "pages": paginated.pages,
            "current_page": paginated.page,
            "per_page": per_page,
            "has_next": paginated.has_next,
            "has_prev": paginated.has_prev,
        }
