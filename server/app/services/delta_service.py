from datetime import datetime, timedelta
from app import db
from app.models.scan_result import ScanResult
from app.models.delta_report import DeltaReport
from app.models.scan import Scan
from typing import Optional, Dict, List, Tuple
from sqlalchemy import and_


class DeltaReportService:
    """Service for managing delta reports"""

    def generate_delta_report(self, current_result_id: int) -> Optional[DeltaReport]:
        """
        Generate a delta report comparing the current scan result with the previous one.

        Args:
            current_result_id: ID of the current scan result to compare

        Returns:
            DeltaReport: The generated delta report, or None if generation failed
        """
        try:
            # Get the current scan result
            print(f"Generating delta report for scan result {current_result_id}...")
            current_result = ScanResult.query.get(current_result_id)
            if not current_result:
                print(f"Error: Current result {current_result_id} not found")
                return None

            # Find the previous scan result for the same scan_id
            baseline_result = self._get_previous_result(current_result)

            # If no baseline exists, we can't generate a delta report
            if not baseline_result:
                print(
                    f"No previous result found for scan_id {current_result.scan_id}, skipping delta report"
                )
                return None

            # Generate the delta data
            delta_data = self._calculate_delta(baseline_result, current_result)

            # Create the delta report
            delta_report = DeltaReport(
                scan_id=current_result.scan_id,
                baseline_result_id=baseline_result.id,
                current_result_id=current_result.id,
                report_type="delta",
                status="generated",
                new_ports_count=delta_data["summary"]["new_ports_count"],
                closed_ports_count=delta_data["summary"]["closed_ports_count"],
                changed_services_count=delta_data["summary"]["changed_services_count"],
                new_hosts_count=delta_data["summary"]["new_hosts_count"],
                removed_hosts_count=delta_data["summary"]["removed_hosts_count"],
                delta_data=delta_data,
            )

            db.session.add(delta_report)
            db.session.commit()

            print(f"✓ Delta report generated: {delta_report.id}")
            return delta_report

        except Exception as e:
            db.session.rollback()
            print(f"Error generating delta report: {e}")
            return None

    @staticmethod
    def _get_previous_result(current_result: ScanResult) -> Optional[ScanResult]:
        """
        Get the most recent scan result before the current one for the same scan.

        Args:
            current_result: The current scan result

        Returns:
            ScanResult: The previous scan result, or None if not found
        """
        return (
            ScanResult.query.filter(
                ScanResult.scan_id == current_result.scan_id,
                ScanResult.id < current_result.id,
                ScanResult.status == "completed",
            )
            .order_by(ScanResult.id.desc())
            .first()
        )

    def _calculate_delta(self, baseline: ScanResult, current: ScanResult) -> Dict:
        """
        Calculate the differences between baseline and current scan results.

        Args:
            baseline: The baseline (previous) scan result
            current: The current scan result

        Returns:
            Dict: Delta data structure containing all changes
        """
        baseline_parsed = baseline.parsed_results or {}
        current_parsed = current.parsed_results or {}

        # Get sets of hosts
        baseline_hosts = set(baseline_parsed.keys())
        current_hosts = set(current_parsed.keys())

        # Calculate host changes
        new_hosts = list(current_hosts - baseline_hosts)
        removed_hosts = list(baseline_hosts - current_hosts)
        common_hosts = baseline_hosts & current_hosts

        # Calculate port and service changes
        added_ports = []
        removed_ports = []
        changed_ports = []

        for host in common_hosts:
            baseline_host = baseline_parsed[host]
            current_host = current_parsed[host]

            baseline_ports = set(baseline_host.get("open_ports", []))
            current_ports = set(current_host.get("open_ports", []))

            baseline_port_details = baseline_host.get("port_details", {})
            current_port_details = current_host.get("port_details", {})

            # New ports on this host
            for port in current_ports - baseline_ports:
                port_str = str(port)
                details = current_port_details.get(port_str, {})
                added_ports.append(
                    {
                        "host": host,
                        "port": port,
                        "protocol": details.get("protocol", "tcp"),
                        "service": details.get("name", "unknown"),
                        "product": details.get("product", ""),
                        "version": details.get("version", ""),
                    }
                )

            # Removed ports on this host
            for port in baseline_ports - current_ports:
                port_str = str(port)
                details = baseline_port_details.get(port_str, {})
                removed_ports.append(
                    {
                        "host": host,
                        "port": port,
                        "protocol": details.get("protocol", "tcp"),
                        "service": details.get("name", "unknown"),
                        "product": details.get("product", ""),
                        "version": details.get("version", ""),
                    }
                )

            # Changed services on existing ports
            for port in baseline_ports & current_ports:
                port_str = str(port)
                baseline_details = baseline_port_details.get(port_str, {})
                current_details = current_port_details.get(port_str, {})

                # Check if service details changed
                if self._has_service_changed(baseline_details, current_details):
                    changed_ports.append(
                        {
                            "host": host,
                            "port": port,
                            "protocol": current_details.get("protocol", "tcp"),
                            "before": {
                                "service": baseline_details.get("name", "unknown"),
                                "product": baseline_details.get("product", ""),
                                "version": baseline_details.get("version", ""),
                                "extrainfo": baseline_details.get("extrainfo", ""),
                            },
                            "after": {
                                "service": current_details.get("name", "unknown"),
                                "product": current_details.get("product", ""),
                                "version": current_details.get("version", ""),
                                "extrainfo": current_details.get("extrainfo", ""),
                            },
                        }
                    )

        # Handle new hosts (all their ports are "new")
        for host in new_hosts:
            host_data = current_parsed[host]
            port_details = host_data.get("port_details", {})
            for port in host_data.get("open_ports", []):
                port_str = str(port)
                details = port_details.get(port_str, {})
                added_ports.append(
                    {
                        "host": host,
                        "port": port,
                        "protocol": details.get("protocol", "tcp"),
                        "service": details.get("name", "unknown"),
                        "product": details.get("product", ""),
                        "version": details.get("version", ""),
                    }
                )

        # Handle removed hosts (all their ports are "removed")
        for host in removed_hosts:
            host_data = baseline_parsed[host]
            port_details = host_data.get("port_details", {})
            for port in host_data.get("open_ports", []):
                port_str = str(port)
                details = port_details.get(port_str, {})
                removed_ports.append(
                    {
                        "host": host,
                        "port": port,
                        "protocol": details.get("protocol", "tcp"),
                        "service": details.get("name", "unknown"),
                        "product": details.get("product", ""),
                        "version": details.get("version", ""),
                    }
                )

        # Build delta data structure
        delta_data = {
            "scanner": {
                "name": "nmap",
                "comparison_time": datetime.utcnow().isoformat(),
            },
            "baseline": {
                "result_id": baseline.id,
                "completed_at": (
                    baseline.completed_at.isoformat() if baseline.completed_at else None
                ),
                "total_hosts": len(baseline_hosts),
                "total_open_ports": baseline.total_open_ports,
            },
            "current": {
                "result_id": current.id,
                "completed_at": (
                    current.completed_at.isoformat() if current.completed_at else None
                ),
                "total_hosts": len(current_hosts),
                "total_open_ports": current.total_open_ports,
            },
            "delta": {
                "new_up_hosts": new_hosts,
                "new_down_hosts": removed_hosts,
                "added_ports": added_ports,
                "removed_ports": removed_ports,
                "changed_ports": changed_ports,
            },
            "summary": {
                "new_hosts_count": len(new_hosts),
                "removed_hosts_count": len(removed_hosts),
                "new_ports_count": len(added_ports),
                "closed_ports_count": len(removed_ports),
                "changed_services_count": len(changed_ports),
            },
        }

        return delta_data

    @staticmethod
    def _has_service_changed(baseline_details: Dict, current_details: Dict) -> bool:
        """
        Check if service details have changed between baseline and current.

        Args:
            baseline_details: Service details from baseline scan
            current_details: Service details from current scan

        Returns:
            bool: True if service details changed
        """
        # Compare relevant fields
        fields_to_compare = ["name", "product", "version", "extrainfo"]

        for field in fields_to_compare:
            baseline_value = baseline_details.get(field, "")
            current_value = current_details.get(field, "")

            # Consider change if values are different and both are non-empty
            # or if one became empty/populated
            if baseline_value != current_value:
                return True

        return False

    @staticmethod
    def get_change_summary(scan_id: int, days: int = 30) -> Dict:
        """
        Get a summary of changes for a specific scan over a given number of days.

        Args:
            scan_id: The ID of the scan to summarize.
            days: The number of days to include in the summary.

        Returns:
            A dictionary containing the change summary.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Get all delta reports for this scan within the timeframe
        reports = DeltaReport.query.filter(
            and_(DeltaReport.scan_id == scan_id, DeltaReport.created_at >= cutoff_date)
        ).all()

        if not reports:
            return {
                "scan_id": scan_id,
                "days": days,
                "total_reports": 0,
                "reports_with_changes": 0,
                "summary": {
                    "total_new_ports": 0,
                    "total_closed_ports": 0,
                    "total_changed_services": 0,
                    "total_new_hosts": 0,
                    "total_removed_hosts": 0,
                },
                "trend": {"most_active_hosts": [], "most_changed_ports": []},
            }

        # Aggregate statistics
        total_new_ports = sum(r.new_ports_count for r in reports)
        total_closed_ports = sum(r.closed_ports_count for r in reports)
        total_changed_services = sum(r.changed_services_count for r in reports)
        total_new_hosts = sum(r.new_hosts_count for r in reports)
        total_removed_hosts = sum(r.removed_hosts_count for r in reports)

        reports_with_changes = sum(1 for r in reports if r.has_changes())

        # Track most active hosts and ports
        host_activity = {}
        port_changes = {}

        for report in reports:
            if report.delta_data and report.delta_data.get("delta"):
                delta = report.delta_data["delta"]

                # Track host activity
                for port_info in delta.get("added_ports", []) + delta.get(
                    "removed_ports", []
                ):
                    host = port_info.get("host")
                    if host:
                        host_activity[host] = host_activity.get(host, 0) + 1

                # Track port changes
                for port_info in (
                    delta.get("added_ports", [])
                    + delta.get("removed_ports", [])
                    + delta.get("changed_ports", [])
                ):
                    port = port_info.get("port")
                    if port:
                        port_changes[port] = port_changes.get(port, 0) + 1

        # Get top 5 most active hosts and ports
        most_active_hosts = sorted(
            host_activity.items(), key=lambda x: x[1], reverse=True
        )[:5]
        most_changed_ports = sorted(
            port_changes.items(), key=lambda x: x[1], reverse=True
        )[:5]

        return {
            "scan_id": scan_id,
            "days": days,
            "period_start": cutoff_date.isoformat(),
            "period_end": datetime.utcnow().isoformat(),
            "total_reports": len(reports),
            "reports_with_changes": reports_with_changes,
            "summary": {
                "total_new_ports": total_new_ports,
                "total_closed_ports": total_closed_ports,
                "total_changed_services": total_changed_services,
                "total_new_hosts": total_new_hosts,
                "total_removed_hosts": total_removed_hosts,
            },
            "trend": {
                "most_active_hosts": [
                    {"host": host, "change_count": count}
                    for host, count in most_active_hosts
                ],
                "most_changed_ports": [
                    {"port": port, "change_count": count}
                    for port, count in most_changed_ports
                ],
            },
        }

    @staticmethod
    def get_reports_by_user(
        user_id: int,
        page: int = 1,
        per_page: int = 10,
        only_changes: bool = False,
    ) -> Dict:
        """
        Retrieve paginated delta reports for all scans owned by a specific user.

        Args:
            user_id: The ID of the user whose reports to retrieve.
            page: The page number for pagination.
            per_page: The number of reports per page.
            only_changes: If True, only return reports with changes.

        Returns:
            Dictionary with paginated results and metadata
        """
        # Get all scan IDs for this user
        user_scan_ids = db.session.query(Scan.id).filter(Scan.user_id == user_id).all()
        scan_ids = [scan_id[0] for scan_id in user_scan_ids]

        if not scan_ids:
            return {
                "reports": [],
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total_items": 0,
                    "total_pages": 0,
                },
            }

        # Build query for delta reports
        query = DeltaReport.query.filter(DeltaReport.scan_id.in_(scan_ids))

        # Filter for only reports with changes if requested
        if only_changes:
            query = query.filter(
                db.or_(
                    DeltaReport.new_ports_count > 0,
                    DeltaReport.closed_ports_count > 0,
                    DeltaReport.changed_services_count > 0,
                    DeltaReport.new_hosts_count > 0,
                    DeltaReport.removed_hosts_count > 0,
                )
            )

        # Order by most recent first
        query = query.order_by(DeltaReport.created_at.desc())

        # Get total count before pagination
        total_items = query.count()

        # Apply pagination
        paginated_query = query.paginate(page=page, per_page=per_page, error_out=False)

        # Convert reports to dictionaries
        reports = [report.to_dict() for report in paginated_query.items]

        return {
            "reports": reports,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_items": total_items,
                "total_pages": paginated_query.pages,
                "has_next": paginated_query.has_next,
                "has_prev": paginated_query.has_prev,
            },
        }
