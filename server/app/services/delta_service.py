"""
Delta Report Service Layer

This service provides business logic for delta report management,
including notifications, batch operations, and advanced filtering.
"""

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
    def generate_delta_report():
        """
        Generate a delta report for this task group by:
        1. Aggregating all scan results from this group
        2. Finding the previous task group for this scan
        3. Aggregating results from the previous group
        4. Comparing the two aggregated results

        Returns:
            DeltaReport: Generated report or None
        """
        from app.models.scan import Scan
        from app.models.delta_report import DeltaReport
        from app.models.scan_result import ScanResult

        # Get current group's results
        current_results = self.get_task_group_results()

        if not current_results:
            print("❌ No completed results in current group")
            return None

        print(f"✓ Found {len(current_results)} results in current group")

        # Find previous task group for this scan
        previous_group_id = self.get_previous_task_group_id()

        if not previous_group_id:
            print("ℹ️ No previous task group found (this is the first scan)")
            return None

        print(f"✓ Found previous task group: {previous_group_id}")

        # Get previous group's results
        previous_tasks = ScanTask.query.filter_by(task_group_id=previous_group_id).all()

        previous_results = []
        for task in previous_tasks:
            if task.scan_result_id:
                result = ScanResult.query.get(task.scan_result_id)
                if result and result.status == "completed":
                    previous_results.append(result)

        if not previous_results:
            print("❌ No completed results in previous group")
            return None

        print(f"✓ Found {len(previous_results)} results in previous group")

        # Create aggregated scan results
        aggregated_current = self.aggregate_scan_results(current_results)
        aggregated_baseline = self.aggregate_scan_results(previous_results)

        # Create temporary ScanResult objects for comparison
        temp_current = ScanResult(
            scan_id=self.scan_id,
            client_id="aggregated",
            status="completed",
            started_at=min(r.started_at for r in current_results),
            end_time=max(r.end_time for r in current_results if r.end_time),
            results_data=aggregated_current,
        )

        temp_baseline = ScanResult(
            scan_id=self.scan_id,
            client_id="aggregated",
            status="completed",
            started_at=min(r.started_at for r in previous_results),
            end_time=max(r.end_time for r in previous_results if r.end_time),
            results_data=aggregated_baseline,
        )

        # Generate delta report using the aggregated data
        print("🔄 Comparing aggregated results...")
        delta_report = DeltaReport.generate_from_aggregated_results(
            scan_id=self.scan_id,
            baseline_result=temp_baseline,
            current_result=temp_current,
            baseline_task_group_id=previous_group_id,
            current_task_group_id=self.task_group_id,
        )

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
    def generate_report_for_scan_result(scan_result_id: int) -> Optional[DeltaReport]:
        """
        Generate a delta report for a completed scan result.

        Args:
            scan_result_id: ID of the completed scan result

        Returns:
            DeltaReport: Generated report or None if conditions not met
        """
        scan_result = ScanResult.query.get(scan_result_id)

        if not scan_result or scan_result.status != "completed":
            return None

        scan = scan_result.scan
        if not scan:
            return None

        return scan.generate_delta_report_for_result(scan_result)

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

    @staticmethod
    def get_critical_changes(
        user_id: int, severity_threshold: str = "medium"
    ) -> List[DeltaReport]:
        """
        Get delta reports with critical changes based on severity.

        Args:
            user_id: User ID
            severity_threshold: 'low', 'medium', 'high'

        Returns:
            List of critical delta reports
        """
        # Define severity criteria
        criteria = {
            "low": {"new_ports": 1, "closed_ports": 1, "new_hosts": 1},
            "medium": {"new_ports": 3, "closed_ports": 2, "new_hosts": 1},
            "high": {"new_ports": 5, "closed_ports": 3, "new_hosts": 2},
        }

        threshold = criteria.get(severity_threshold, criteria["medium"])

        query = (
            db.session.query(DeltaReport)
            .join(Scan)
            .filter(
                Scan.user_id == user_id,
                or_(
                    DeltaReport.new_ports_count >= threshold["new_ports"],
                    DeltaReport.closed_ports_count >= threshold["closed_ports"],
                    DeltaReport.new_hosts_count >= threshold["new_hosts"],
                ),
            )
            .order_by(DeltaReport.created_at.desc())
        )

        return query.all()

    @staticmethod
    def get_change_summary(scan_id: int, days: int = 30) -> Dict[str, Any]:
        """
        Get a summary of changes over the specified period.

        Args:
            scan_id: Scan ID
            days: Number of days to analyze

        Returns:
            dict: Summary statistics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        reports = DeltaReport.query.filter(
            DeltaReport.scan_id == scan_id, DeltaReport.created_at >= cutoff_date
        ).all()

        if not reports:
            return {
                "period_days": days,
                "total_reports": 0,
                "reports_with_changes": 0,
                "total_new_ports": 0,
                "total_closed_ports": 0,
                "total_changed_services": 0,
                "total_new_hosts": 0,
                "total_removed_hosts": 0,
                "average_changes_per_report": 0,
                "most_active_hosts": [],
            }

        # Calculate statistics
        reports_with_changes = [r for r in reports if r.has_changes()]
        total_changes = sum(
            r.new_ports_count
            + r.closed_ports_count
            + r.changed_services_count
            + r.new_hosts_count
            + r.removed_hosts_count
            for r in reports
        )

        # Find most active hosts (hosts with most changes)
        host_activity = {}
        for report in reports:
            if report.delta_data:
                for host_ip in report.delta_data.get("host_changes", {}).keys():
                    host_activity[host_ip] = host_activity.get(host_ip, 0) + 1

        most_active = sorted(host_activity.items(), key=lambda x: x[1], reverse=True)[
            :5
        ]

        return {
            "period_days": days,
            "total_reports": len(reports),
            "reports_with_changes": len(reports_with_changes),
            "total_new_ports": sum(r.new_ports_count for r in reports),
            "total_closed_ports": sum(r.closed_ports_count for r in reports),
            "total_changed_services": sum(r.changed_services_count for r in reports),
            "total_new_hosts": sum(r.new_hosts_count for r in reports),
            "total_removed_hosts": sum(r.removed_hosts_count for r in reports),
            "average_changes_per_report": (
                total_changes / len(reports) if reports else 0
            ),
            "most_active_hosts": [
                {"host": host, "change_count": count} for host, count in most_active
            ],
        }

    @staticmethod
    def regenerate_report(report_id: int) -> Optional[DeltaReport]:
        """
        Regenerate a delta report (useful if comparison logic changes).

        Args:
            report_id: ID of the report to regenerate

        Returns:
            DeltaReport: Regenerated report
        """
        old_report = DeltaReport.query.get(report_id)

        if not old_report:
            return None

        # Get the original scan results
        baseline_result = old_report.baseline_result
        current_result = old_report.current_result

        if not baseline_result or not current_result:
            return None

        # Delete old report
        scan_id = old_report.scan_id
        db.session.delete(old_report)
        db.session.commit()

        # Generate new report
        return DeltaReport.generate_from_results(
            scan_id=scan_id,
            baseline_result=baseline_result,
            current_result=current_result,
        )

    @staticmethod
    def batch_generate_missing_reports(scan_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Generate delta reports for any scan results that don't have one.

        Args:
            scan_id: Optional scan ID to limit to specific scan

        Returns:
            dict: Statistics about generation
        """
        # Get all completed scan results
        query = ScanResult.query.filter(ScanResult.status == "completed")

        if scan_id:
            query = query.filter(ScanResult.scan_id == scan_id)

        results = query.order_by(ScanResult.started_at).all()

        generated = 0
        skipped = 0
        errors = []

        # Group by scan
        from itertools import groupby

        results_by_scan = groupby(results, key=lambda x: x.scan_id)

        for scan_id, scan_results in results_by_scan:
            scan_results = list(scan_results)

            # Skip first result (no baseline)
            for i in range(1, len(scan_results)):
                current = scan_results[i]
                baseline = scan_results[i - 1]

                # Check if report already exists
                existing = DeltaReport.query.filter_by(
                    current_result_id=current.id
                ).first()

                if existing:
                    skipped += 1
                    continue

                try:
                    report = DeltaReport.generate_from_results(
                        scan_id=scan_id,
                        baseline_result=baseline,
                        current_result=current,
                    )

                    if report:
                        generated += 1
                    else:
                        skipped += 1
                except Exception as e:
                    errors.append({"scan_result_id": current.id, "error": str(e)})

        return {
            "generated": generated,
            "skipped": skipped,
            "errors": errors,
            "total_processed": generated + skipped + len(errors),
        }

    @staticmethod
    def compare_specific_results(
        result1_id: int, result2_id: int, save_as_report: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Compare two specific scan results (not necessarily consecutive).

        Args:
            result1_id: First (baseline) result ID
            result2_id: Second (current) result ID
            save_as_report: Whether to save as a delta report

        Returns:
            dict: Delta data or None if comparison fails
        """
        result1 = ScanResult.query.get(result1_id)
        result2 = ScanResult.query.get(result2_id)

        if not result1 or not result2:
            return None

        if result1.status != "completed" or result2.status != "completed":
            return None

        # Compare
        delta_data = result2.compare_with(result1)

        if not delta_data:
            return None

        # Optionally save as report
        if save_as_report and result1.scan_id == result2.scan_id:
            report = DeltaReport.generate_from_results(
                scan_id=result1.scan_id, baseline_result=result1, current_result=result2
            )
            return report.to_dict(include_delta_data=True)

        return delta_data

    @staticmethod
    def get_host_change_history(
        scan_id: int, host_ip: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get change history for a specific host across all delta reports.

        Args:
            scan_id: Scan ID
            host_ip: IP address of the host
            limit: Maximum number of reports to check

        Returns:
            List of changes for this host
        """
        reports = (
            DeltaReport.query.filter_by(scan_id=scan_id)
            .order_by(DeltaReport.created_at.desc())
            .limit(limit)
            .all()
        )

        history = []

        for report in reports:
            if not report.delta_data:
                continue

            # Check if host appears in new hosts
            if host_ip in report.delta_data.get("new_hosts", []):
                history.append(
                    {
                        "timestamp": report.created_at.isoformat(),
                        "report_id": report.report_id,
                        "event": "host_discovered",
                        "details": {},
                    }
                )

            # Check if host appears in removed hosts
            if host_ip in report.delta_data.get("removed_hosts", []):
                history.append(
                    {
                        "timestamp": report.created_at.isoformat(),
                        "report_id": report.report_id,
                        "event": "host_removed",
                        "details": {},
                    }
                )

            # Check for host changes
            host_changes = report.delta_data.get("host_changes", {}).get(host_ip)
            if host_changes:
                history.append(
                    {
                        "timestamp": report.created_at.isoformat(),
                        "report_id": report.report_id,
                        "event": "host_changed",
                        "details": {
                            "new_ports": len(host_changes.get("new_ports", [])),
                            "closed_ports": len(host_changes.get("closed_ports", [])),
                            "changed_ports": len(host_changes.get("changed_ports", [])),
                        },
                    }
                )

        return history

    @staticmethod
    def get_port_change_history(
        scan_id: int, host_ip: str, port: int, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get change history for a specific port on a host.

        Args:
            scan_id: Scan ID
            host_ip: IP address
            port: Port number
            limit: Maximum number of reports to check

        Returns:
            List of changes for this port
        """
        reports = (
            DeltaReport.query.filter_by(scan_id=scan_id)
            .order_by(DeltaReport.created_at.desc())
            .limit(limit)
            .all()
        )

        history = []

        for report in reports:
            if not report.delta_data:
                continue

            host_changes = report.delta_data.get("host_changes", {}).get(host_ip)
            if not host_changes:
                continue

            # Check new ports
            for port_info in host_changes.get("new_ports", []):
                if port_info.get("port") == port:
                    history.append(
                        {
                            "timestamp": report.created_at.isoformat(),
                            "report_id": report.report_id,
                            "event": "port_opened",
                            "port": port,
                            "service": port_info.get("service"),
                            "version": port_info.get("version"),
                        }
                    )

            # Check closed ports
            for port_info in host_changes.get("closed_ports", []):
                if port_info.get("port") == port:
                    history.append(
                        {
                            "timestamp": report.created_at.isoformat(),
                            "report_id": report.report_id,
                            "event": "port_closed",
                            "port": port,
                            "service": port_info.get("service"),
                        }
                    )

            # Check changed ports
            for port_change in host_changes.get("changed_ports", []):
                if port_change.get("port") == port:
                    history.append(
                        {
                            "timestamp": report.created_at.isoformat(),
                            "report_id": report.report_id,
                            "event": "port_changed",
                            "port": port,
                            "changes": port_change.get("changes"),
                        }
                    )

        return history

    @staticmethod
    def export_reports_bulk(report_ids: List[int], format: str = "csv") -> bytes:
        """
        Export multiple delta reports in bulk.

        Args:
            report_ids: List of report IDs to export
            format: Export format ('csv' or 'json')

        Returns:
            bytes: Zip file containing all reports
        """
        import zipfile
        from io import BytesIO
        import json

        zip_buffer = BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for report_id in report_ids:
                report = DeltaReport.query.get(report_id)

                if not report:
                    continue

                if format == "csv":
                    content = report.to_csv()
                    filename = f"delta_report_{report.report_id}.csv"
                else:  # json
                    content = json.dumps(
                        report.to_dict(include_delta_data=True), indent=2
                    )
                    filename = f"delta_report_{report.report_id}.json"

                zip_file.writestr(filename, content)

        return zip_buffer.getvalue()
