"""
Scheduler service for managing scheduled scans
"""

import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.events import (
    EVENT_JOB_ERROR,
    EVENT_JOB_EXECUTED,
    EVENT_JOB_MISSED,
    EVENT_JOB_ADDED,
    EVENT_JOB_REMOVED,
)
from flask import current_app
from sqlalchemy import and_
import uuid
import json

logger = logging.getLogger(__name__)

# Store app reference at module level (not pickled, set at runtime)
_app_instance = None


def _check_client_heartbeats_job():
    """Standalone function to check client heartbeats (called by scheduler)"""
    global _app_instance

    if _app_instance is None:
        logger.error("App instance not set for heartbeat check")
        return

    with _app_instance.app_context():
        try:
            from app import db
            from app.models.client import Client

            heartbeat_timeout = timedelta(minutes=3)
            cutoff_time = datetime.utcnow() - heartbeat_timeout

            stale_clients = Client.query.filter(
                Client.status == "online", Client.last_seen < cutoff_time
            ).all()

            offline_count = 0
            for client in stale_clients:
                logger.info(
                    f"Marking client {client.client_id} ({client.hostname}) offline - last seen: {client.last_seen}"
                )
                client.mark_offline()
                offline_count += 1

            if offline_count > 0:
                db.session.commit()
                logger.info(
                    f"Marked {offline_count} clients offline due to missed heartbeats"
                )

            total_clients = Client.query.count()
            online_clients = Client.query.filter_by(status="online").count()
            offline_clients = Client.query.filter_by(status="offline").count()

            logger.info(
                f"Client Status Summary - Total: {total_clients}, Online: {online_clients}, Offline: {offline_clients}"
            )

        except Exception as e:
            logger.error(f"Error checking client heartbeats: {str(e)}")
            db.session.rollback()


def _execute_scan(scan_id):
    """Standalone function to execute a scan (called by scheduler or manually)."""
    global _app_instance
    if _app_instance is None:
        logger.error("App instance not set for scan execution")
        return {"status": "error", "message": "App instance not set for scan execution"}

    import ipaddress
    import requests
    from datetime import datetime, timedelta
    import uuid
    import json

    with _app_instance.app_context():
        try:
            from app.models.scan import Scan
            from app.models.scan_task import ScanTask
            from app.models.scan_result import ScanResult
            from app.models.client import Client
            from app import db

            scan = Scan.query.get(scan_id)
            if not scan:
                raise ValueError(f"Scan {scan_id} not found")
            if not scan.is_active:
                logger.info(f"Scan {scan_id} is inactive, skipping execution")
                return {
                    "status": "success",
                    "message": f"Scan {scan_id} is inactive, skipped",
                }

            # Parse scan targets
            try:
                scan_network = ipaddress.ip_network(scan.target, strict=False)
                scan_targets = [str(ip) for ip in scan_network.hosts()]
            except Exception:
                scan_targets = [t.strip() for t in scan.target.split(",") if t.strip()]
            if not scan_targets:
                raise ValueError(f"No valid targets parsed for scan {scan_id}")

            # Find all online clients
            now = datetime.utcnow()
            clients = Client.query.filter(
                Client.status.in_(["online", "idle"]),
                Client.last_seen >= now - timedelta(minutes=5),
                Client.scan_range.isnot(None),
            ).all()
            if not clients:
                raise RuntimeError(f"No active clients available for scan {scan_id}")

            # Match clients to scan targets
            client_ip_map = {}
            for client in clients:
                try:
                    client_net = ipaddress.ip_network(client.scan_range, strict=False)
                    client_ips = set(str(ip) for ip in client_net.hosts())
                    overlap = set(scan_targets) & client_ips
                    if overlap:
                        client_ip_map[client] = overlap
                except Exception as e:
                    logger.warning(
                        f"Invalid scan_range for client {client.client_id}: {e}"
                    )

            if not client_ip_map:
                msg = f"No clients with matching scan_range for scan {scan_id}"
                logger.warning(msg)
                return {"status": "error", "message": msg}

            # Create result record
            scan_result = ScanResult(
                scan_id=scan_id,
                status="pending",
                started_at=datetime.utcnow(),
            )
            db.session.add(scan_result)
            db.session.flush()
            result_id = scan_result.id
            task_group_id = str(uuid.uuid4())
            assigned_targets = set()
            triggered_clients = 0

            for client, ips in client_ip_map.items():
                targets_for_client = list(ips - assigned_targets)
                if not targets_for_client:
                    continue
                assigned_targets.update(targets_for_client)
                task_id = str(uuid.uuid4())
                task = ScanTask(
                    task_id=task_id,
                    task_group_id=task_group_id,
                    client_id=client.client_id,
                    scan_id=scan_id,
                    targets=json.dumps(targets_for_client),
                    ports=scan.ports,
                    priority=2,
                    status="pending",
                    scan_result_id=scan_result.id,
                )
                db.session.add(task)
                try:
                    logger.info(
                        f"Triggering scan on client {client.ip_address} for {len(targets_for_client)} targets."
                    )
                    url = f"http://{client.ip_address}:{client.port}/scan"
                    payload = {
                        "scan_id": scan_id,
                        "task_id": task_id,
                        "result_id": result_id,
                        "targets": targets_for_client,
                        "ports": scan.ports,
                        "scan_arguments": scan.scan_arguments,
                    }
                    req = requests.post(url, json=payload, timeout=5)
                    req.raise_for_status()
                    logger.info(
                        f"Successfully triggered scan on client {client.client_id} for {len(targets_for_client)} targets."
                    )
                    triggered_clients += 1
                except requests.exceptions.RequestException as e:
                    logger.warning(
                        f"Failed to contact client at {client.ip_address}: {e}"
                    )
                    continue  # Continue to next client instead of failing the scan
                except Exception as e:
                    logger.warning(
                        f"Error triggering scan on client {client.client_id}: {e}"
                    )
                    continue

            if triggered_clients == 0:
                db.session.rollback()
                msg = "No clients successfully triggered for scan"
                logger.error(msg)
                return {"status": "error", "message": msg}

            # Check if all targets were assigned
            unassigned_targets = set(scan_targets) - assigned_targets
            if unassigned_targets:
                logger.warning(
                    f"Scan {scan_id} is partial: {len(unassigned_targets)} targets not assigned: {unassigned_targets}"
                )
                scan_result.type = "partial"
            else:
                scan_result.type = "full"

            # Finalize and commit
            scan.update_last_run()
            scan.next_run = datetime.utcnow() + timedelta(minutes=scan.interval_minutes)
            db.session.commit()
            msg = (
                f"Successfully delegated scan {scan_id} to {triggered_clients} clients. "
                f"{'Partial scan due to unassigned targets' if unassigned_targets else 'All targets assigned'}."
            )
            logger.info(msg)
            return {
                "status": "success",
                "message": msg,
                "result_id": result_id,
                "clients_triggered": triggered_clients,
                "unassigned_targets": (
                    list(unassigned_targets) if unassigned_targets else []
                ),
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error executing scan {scan_id}: {e}")
            return {
                "status": "error",
                "message": f"Error executing scan {scan_id}: {str(e)}",
            }


class SchedulerService:
    """Service for managing scheduled scan tasks"""

    def __init__(self, app=None):
        self.scheduler = None
        self.app = app
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize the scheduler with Flask app"""
        global _app_instance
        self.app = app
        _app_instance = app  # Store at module level for scheduled jobs

        # Configure job stores and executors
        jobstores = {
            "default": SQLAlchemyJobStore(
                url=app.config.get("SQLALCHEMY_DATABASE_URI", "sqlite:///scheduler.db")
            )
        }

        executors = {
            "default": ThreadPoolExecutor(
                max_workers=app.config.get("SCHEDULER_MAX_WORKERS", 10)
            )
        }

        job_defaults = {
            "coalesce": True,  # Combine multiple pending executions of same job
            "max_instances": 1,  # Only one instance of each job at a time
            "misfire_grace_time": 60,  # Job can be up to 60 seconds late
        }

        # Create scheduler
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone="UTC",
        )

        # Add event listeners
        self.scheduler.add_listener(self._job_executed_listener, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error_listener, EVENT_JOB_ERROR)
        self.scheduler.add_listener(self._job_missed_listener, EVENT_JOB_MISSED)
        self.scheduler.add_listener(self._job_added_listener, EVENT_JOB_ADDED)
        self.scheduler.add_listener(self._job_removed_listener, EVENT_JOB_REMOVED)

        # Register cleanup on app teardown
        app.teardown_appcontext(self._teardown)

    def start(self):
        """Start the scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")

            # Load existing scheduled scans
            self._load_scheduled_scans()

            self.schedule_client_heartbeats_check()

    def shutdown(self, wait=True):
        """Shutdown the scheduler"""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=wait)
            logger.info("Scheduler shutdown")

    def _teardown(self, exception=None):
        """Cleanup on app teardown"""
        pass  # Scheduler persists across requests

    def _load_scheduled_scans(self):
        """Load all active scheduled scans from database"""
        try:
            with self.app.app_context():
                from app.models.scan import Scan
                from app import db

                # Get all active scheduled scans
                scans = Scan.query.filter(
                    and_(Scan.is_scheduled == True, Scan.is_active == True)
                ).all()

                for scan in scans:
                    self.schedule_scan(scan)

                logger.info(f"Loaded {len(scans)} scheduled scans")

        except Exception as e:
            logger.error(f"Failed to load scheduled scans: {str(e)}")

    def schedule_client_heartbeats_check(self):
        """Schedule the client heartbeat check job"""
        try:
            # Don't pass app - the function will use current_app
            self.scheduler.add_job(
                func=_check_client_heartbeats_job,
                trigger="interval",
                minutes=3,
                id="check_heartbeats",
                replace_existing=True,
            )
            logger.info("Scheduled client heartbeat check job")
        except Exception as e:
            logger.error(f"Failed to schedule heartbeat check: {str(e)}")
            return None

    def schedule_scan(self, scan):
        """Schedule a scan for periodic execution"""
        try:
            job_id = f"scan_{scan.id}"

            # Remove existing job if present
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)

            # Calculate first run time
            if scan.next_run and scan.next_run > datetime.utcnow():
                first_run_time = scan.next_run
            else:
                first_run_time = datetime.utcnow() + timedelta(seconds=30)

            # Add job to scheduler
            job = self.scheduler.add_job(
                func=_execute_scan,
                trigger="interval",
                minutes=scan.interval_minutes,
                id=job_id,
                name=f"Scan: {scan.name}",
                args=[scan.id],
                next_run_time=first_run_time,
                replace_existing=True,
                max_instances=1,
            )

            logger.info(
                f"Scheduled scan {scan.id} ({scan.name}) to run every {scan.interval_minutes} minutes"
            )

            return job

        except Exception as e:
            logger.error(f"Failed to schedule scan {scan.id}: {str(e)}")
            return None

    def unschedule_scan(self, scan_id):
        """Remove a scan from the schedule"""
        try:
            job_id = f"scan_{scan_id}"

            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.info(f"Unscheduled scan {scan_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to unschedule scan {scan_id}: {str(e)}")
            return False

    def reschedule_scan(self, scan_id, interval_minutes):
        """Update the schedule for an existing scan"""
        try:
            job_id = f"scan_{scan_id}"
            job = self.scheduler.get_job(job_id)

            if job:
                # Reschedule with new interval
                self.scheduler.reschedule_job(
                    job_id, trigger="interval", minutes=interval_minutes
                )
                logger.info(
                    f"Rescheduled scan {scan_id} with interval {interval_minutes} minutes"
                )
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to reschedule scan {scan_id}: {str(e)}")
            return False

    def get_job_info(self, scan_id):
        """Get information about a scheduled job"""
        try:
            job_id = f"scan_{scan_id}"
            job = self.scheduler.get_job(job_id)

            if job:
                return {
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": (
                        job.next_run_time.isoformat() if job.next_run_time else None
                    ),
                    "trigger": str(job.trigger),
                    "pending": job.pending,
                }

            return None

        except Exception as e:
            logger.error(f"Failed to get job info for scan {scan_id}: {str(e)}")
            return None

    def get_all_jobs(self):
        """Get information about all scheduled jobs"""
        try:
            jobs = []
            for job in self.scheduler.get_jobs():
                jobs.append(
                    {
                        "id": job.id,
                        "name": job.name,
                        "next_run_time": (
                            job.next_run_time.isoformat() if job.next_run_time else None
                        ),
                        "trigger": str(job.trigger),
                    }
                )
            return jobs

        except Exception as e:
            logger.error(f"Failed to get all jobs: {str(e)}")
            return []

    def clear_all_jobs(self):
        """Remove all scheduled jobs from the scheduler"""
        try:
            if not self.scheduler:
                logger.warning("Scheduler not initialized")
                return False

            jobs = self.scheduler.get_jobs()
            for job in jobs:
                self.scheduler.remove_job(job.id)

            logger.info(f"Cleared {len(jobs)} scheduled jobs")
            return True

        except Exception as e:
            logger.error(f"Failed to clear all jobs: {str(e)}")
            return False

    def pause_scan(self, scan_id):
        """Pause a scheduled scan"""
        try:
            job_id = f"scan_{scan_id}"
            job = self.scheduler.get_job(job_id)

            if job:
                job.pause()
                logger.info(f"Paused scan {scan_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to pause scan {scan_id}: {str(e)}")
            return False

    def resume_scan(self, scan_id):
        """Resume a paused scan"""
        try:
            job_id = f"scan_{scan_id}"
            job = self.scheduler.get_job(job_id)

            if job:
                job.resume()
                logger.info(f"Resumed scan {scan_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to resume scan {scan_id}: {str(e)}")
            return False

    # Event Listeners

    def _job_executed_listener(self, event):
        """Handle successful job execution"""
        logger.debug(f"Job {event.job_id} executed successfully")

    def _job_error_listener(self, event):
        """Handle job execution errors"""
        logger.error(f"Job {event.job_id} crashed: {event.exception}")

        # Could implement retry logic or notifications here
        if event.job_id.startswith("scan_"):
            scan_id = event.job_id.replace("scan_", "")
            # Check if scan still exists and is scheduled in database
            try:
                with self.app.app_context():
                    from app.models.scan import Scan

                    scan = Scan.query.get(scan_id)
                    if not scan or not scan.is_scheduled:
                        logger.info(
                            f"Scan {scan_id} no longer exists or is not scheduled, removing from scheduler"
                        )
                        self.unschedule_scan(scan_id)
                    else:
                        logger.error(
                            f"Scan {scan_id} failed during scheduled execution."
                        )
            except Exception as db_error:
                logger.error(f"Failed to check scan {scan_id} in database: {db_error}")

    def _job_missed_listener(self, event):
        """Handle missed job executions"""
        logger.warning(f"Job {event.job_id} missed scheduled run time")

        # Could implement catch-up logic here

    def _job_added_listener(self, event):
        """Handle job addition"""
        logger.debug(f"Job {event.job_id} added to scheduler")

    def _job_removed_listener(self, event):
        """Handle job removal"""
        logger.debug(f"Job {event.job_id} removed from scheduler")


# Create a global instance
scheduler_service = SchedulerService()


def init_scheduler(app):
    """Initialize the scheduler with the Flask app"""
    scheduler_service.init_app(app)
    return scheduler_service
