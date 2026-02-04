from datetime import datetime, timezone, timedelta
from typing import Iterable, Optional, Set

from flask import current_app

from app import db
from app.logging_config import get_logger
from app.models.delta_report import DeltaReport
from app.models.scan import Scan
from app.models.scan_result import ScanResult

logger = get_logger(__name__)


class RetentionService:
    """Prune scan results and delta reports based on retention settings."""

    def cleanup(self) -> None:
        max_results = current_app.config.get("RETENTION_MAX_RESULTS")
        max_reports = current_app.config.get("RETENTION_MAX_REPORTS")
        retention_days = current_app.config.get("RETENTION_DAYS")

        if not any([max_results, max_reports, retention_days]):
            logger.info("Retention cleanup skipped (no retention config set)")
            return

        cutoff = None
        if retention_days:
            cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

        scans = Scan.query.all()
        total_reports_removed = 0
        total_results_removed = 0

        for scan in scans:
            kept_report_ids = self._retain_delta_reports(scan.id, max_reports, cutoff)
            total_reports_removed += self._delete_delta_reports(scan.id, kept_report_ids)

            if max_results:
                total_results_removed += self._delete_scan_results(
                    scan.id, max_results, kept_report_ids
                )

        db.session.commit()
        logger.info(
            "Retention cleanup complete: %s delta reports removed, %s scan results removed",
            total_reports_removed,
            total_results_removed,
        )

    def _retain_delta_reports(
        self,
        scan_id: int,
        max_reports: Optional[int],
        cutoff: Optional[datetime],
    ) -> Set[int]:
        """Return the set of delta report IDs that should be kept."""
        query = DeltaReport.query.filter(DeltaReport.scan_id == scan_id)
        if cutoff:
            query = query.filter(DeltaReport.created_at >= cutoff)

        if max_reports:
            query = query.order_by(DeltaReport.created_at.desc()).limit(max_reports)

        kept_ids = {report.id for report in query.all()}
        return kept_ids

    def _delete_delta_reports(self, scan_id: int, keep_ids: Set[int]) -> int:
        """Delete delta reports for a scan that are not in keep_ids."""
        if keep_ids:
            delete_query = DeltaReport.query.filter(
                DeltaReport.scan_id == scan_id, DeltaReport.id.notin_(keep_ids)
            )
        else:
            delete_query = DeltaReport.query.filter(DeltaReport.scan_id == scan_id)

        removed = delete_query.count()
        if removed:
            delete_query.delete(synchronize_session=False)
        return removed

    def _delete_scan_results(
        self, scan_id: int, max_results: int, kept_report_ids: Set[int]
    ) -> int:
        """Delete scan results while preserving recent results and report baselines."""
        keep_results = (
            ScanResult.query.filter(ScanResult.scan_id == scan_id)
            .order_by(ScanResult.created_at.desc())
            .limit(max_results)
            .all()
        )
        keep_ids = {result.id for result in keep_results}

        if kept_report_ids:
            referenced_ids = self._get_report_result_ids(kept_report_ids)
            keep_ids.update(referenced_ids)

        if not keep_ids:
            return 0

        delete_query = ScanResult.query.filter(
            ScanResult.scan_id == scan_id, ScanResult.id.notin_(keep_ids)
        )
        removed = delete_query.count()
        if removed:
            delete_query.delete(synchronize_session=False)
        return removed

    def _get_report_result_ids(self, report_ids: Iterable[int]) -> Set[int]:
        """Return scan result IDs referenced by the given delta reports."""
        if not report_ids:
            return set()
        rows = (
            db.session.query(
                DeltaReport.baseline_result_id, DeltaReport.current_result_id
            )
            .filter(DeltaReport.id.in_(report_ids))
            .all()
        )
        referenced = {row[0] for row in rows if row[0]} | {
            row[1] for row in rows if row[1]
        }
        return referenced
