import os
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from flask import current_app
from app import create_app, db
from app.models.scan import Scan
from app.models.scan_result import ScanResult
from src.scanner import NetworkScanner


class ScanScheduler:
    """
    Background scheduler for managing periodic network scans
    """
    
    def __init__(self, app=None, max_workers=3):
        """
        Initialize the scan scheduler
        
        Args:
            app: Flask application instance
            max_workers (int): Maximum number of concurrent scan workers
        """
        self.app = app
        self.max_workers = max_workers
        self.scheduler = None
        self.scanner = NetworkScanner()
        self.logger = self._setup_logging()
        self.active_scans: Dict[int, threading.Thread] = {}
        self.scan_lock = threading.Lock()
        
        if app is not None:
            self.init_app(app)
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for scheduler"""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def init_app(self, app):
        """Initialize scheduler with Flask app"""
        self.app = app
        
        # Configure job store
        jobstores = {
            'default': SQLAlchemyJobStore(
                url=app.config.get('JOBS_DATABASE_URL', app.config['SQLALCHEMY_DATABASE_URI'])
            )
        }
        
        # Configure executors
        executors = {
            'default': ThreadPoolExecutor(max_workers=self.max_workers)
        }
        
        # Job defaults
        job_defaults = {
            'coalesce': False,
            'max_instances': 1,
            'misfire_grace_time': 30
        }
        
        # Create scheduler
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=app.config.get('SCHEDULER_TIMEZONE', 'UTC')
        )
        
        # Add event listeners
        self.scheduler.add_listener(self._job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
        
        # Store reference in app
        app.extensions['scan_scheduler'] = self
    
    def start(self):
        """Start the scheduler"""
        if self.scheduler and not self.scheduler.running:
            self.scheduler.start()
            self.logger.info("Scan scheduler started")
            
            # Schedule existing active scans
            with self.app.app_context():
                self._schedule_existing_scans()
    
    def shutdown(self):
        """Shutdown the scheduler"""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            self.logger.info("Scan scheduler shutdown")
    
    def _job_listener(self, event):
        """Handle scheduler job events"""
        if event.exception:
            self.logger.error(f"Job {event.job_id} crashed: {event.exception}")
        else:
            self.logger.info(f"Job {event.job_id} executed successfully")
    
    def _schedule_existing_scans(self):
        """Schedule all active scans from database"""
        try:
            active_scans = Scan.query.filter_by(is_active=True, is_scheduled=True).all()
            
            for scan in active_scans:
                self.schedule_scan(scan)
                
            self.logger.info(f"Scheduled {len(active_scans)} existing scans")
            
        except Exception as e:
            self.logger.error(f"Failed to schedule existing scans: {e}")
    
    def schedule_scan(self, scan: Scan) -> bool:
        """
        Schedule a periodic scan
        
        Args:
            scan (Scan): Scan configuration to schedule
            
        Returns:
            bool: True if successfully scheduled
        """
        try:
            job_id = f"scan_{scan.id}"
            
            # Remove existing job if present
            try:
                self.scheduler.remove_job(job_id)
            except:
                pass
            
            # Calculate next run time
            if scan.last_run:
                next_run = scan.last_run + timedelta(minutes=scan.interval_minutes)
            else:
                next_run = datetime.utcnow() + timedelta(minutes=1)  # Start soon
            
            # Add job
            self.scheduler.add_job(
                func=self._execute_scan,
                trigger='interval',
                minutes=scan.interval_minutes,
                start_date=next_run,
                id=job_id,
                args=[scan.id],
                replace_existing=True
            )
            
            # Update next run time in database
            scan.next_run = next_run
            db.session.commit()
            
            self.logger.info(f"Scheduled scan {scan.name} (ID: {scan.id}) to run every {scan.interval_minutes} minutes")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to schedule scan {scan.id}: {e}")
            return False
    
    def unschedule_scan(self, scan_id: int) -> bool:
        """
        Unschedule a scan
        
        Args:
            scan_id (int): ID of scan to unschedule
            
        Returns:
            bool: True if successfully unscheduled
        """
        try:
            job_id = f"scan_{scan_id}"
            self.scheduler.remove_job(job_id)
            
            # Clear next run time in database
            scan = Scan.query.get(scan_id)
            if scan:
                scan.next_run = None
                db.session.commit()
            
            self.logger.info(f"Unscheduled scan {scan_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to unschedule scan {scan_id}: {e}")
            return False
    
    def _execute_scan(self, scan_id: int):
        """
        Execute a scheduled scan
        
        Args:
            scan_id (int): ID of scan to execute
        """
        with self.app.app_context():
            try:
                # Get scan configuration
                scan = Scan.query.get(scan_id)
                if not scan or not scan.is_active:
                    self.logger.warning(f"Scan {scan_id} is not active or not found")
                    return
                
                # Check if scan is already running
                with self.scan_lock:
                    if scan_id in self.active_scans:
                        self.logger.warning(f"Scan {scan_id} is already running")
                        return
                
                # Create scan result record
                scan_result = ScanResult(
                    scan_id=scan_id,
                    status='pending'
                )
                db.session.add(scan_result)
                db.session.commit()
                
                # Start scan in separate thread
                scan_thread = threading.Thread(
                    target=self._run_scan_thread,
                    args=(scan, scan_result.id),
                    name=f"scan_thread_{scan_id}"
                )
                
                with self.scan_lock:
                    self.active_scans[scan_id] = scan_thread
                
                scan_thread.start()
                
            except Exception as e:
                self.logger.error(f"Failed to execute scan {scan_id}: {e}")
    
    def _run_scan_thread(self, scan: Scan, result_id: int):
        """
        Run scan in background thread
        
        Args:
            scan (Scan): Scan configuration
            result_id (int): Scan result ID
        """
        try:
            with self.app.app_context():
                # Get scan result record
                scan_result = ScanResult.query.get(result_id)
                if not scan_result:
                    self.logger.error(f"Scan result {result_id} not found")
                    return
                
                # Mark as running
                scan_result.mark_running()
                self.logger.info(f"Starting scan {scan.name} (ID: {scan.id})")
                
                try:
                    # Execute scan
                    results = self.scanner.scan_target(
                        target=scan.target,
                        ports=scan.ports,
                        scan_args=scan.scan_arguments
                    )
                    
                    # Save results to file
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"scheduled_scan_{scan.id}_{result_id}_{timestamp}.json"
                    results_file = self.scanner.save_results(results, filename)
                    
                    # Prepare results data for database
                    results_data = {
                        'scan_metadata': {
                            'total_hosts': len(results),
                            'scan_time': datetime.now().isoformat(),
                            'scanner_version': '2.0',
                            'results_file': results_file,
                            'scheduled_scan': True
                        },
                        'results': [
                            {
                                'host': r.host,
                                'hostname': r.hostname,
                                'state': r.state,
                                'ports': r.ports,
                                'timestamp': r.timestamp,
                                'scan_duration': r.scan_duration
                            } for r in results
                        ]
                    }
                    
                    # Mark as completed
                    scan_result.mark_completed(results_data)
                    scan.update_last_run()
                    
                    # Update next run time
                    scan.next_run = datetime.utcnow() + timedelta(minutes=scan.interval_minutes)
                    db.session.commit()
                    
                    self.logger.info(
                        f"Completed scan {scan.name} (ID: {scan.id}). "
                        f"Found {len(results)} hosts in {scan_result.duration_seconds:.1f}s"
                    )
                    
                except Exception as scan_error:
                    # Mark as failed
                    scan_result.mark_failed(str(scan_error))
                    self.logger.error(f"Scan {scan.id} failed: {scan_error}")
                    
        except Exception as e:
            self.logger.error(f"Scan thread error: {e}")
            
        finally:
            # Remove from active scans
            with self.scan_lock:
                if scan.id in self.active_scans:
                    del self.active_scans[scan.id]
    
    def get_active_scan_count(self) -> int:
        """Get number of currently running scans"""
        with self.scan_lock:
            return len(self.active_scans)
    
    def get_scheduled_jobs(self) -> List[Dict]:
        """Get list of scheduled jobs"""
        try:
            jobs = []
            for job in self.scheduler.get_jobs():
                jobs.append({
                    'id': job.id,
                    'name': job.name,
                    'func': str(job.func),
                    'trigger': str(job.trigger),
                    'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None
                })
            return jobs
        except Exception as e:
            self.logger.error(f"Failed to get scheduled jobs: {e}")
            return []
    
    def reschedule_all_scans(self):
        """Reschedule all active scans (useful after configuration changes)"""
        with self.app.app_context():
            try:
                # Remove all existing jobs
                self.scheduler.remove_all_jobs()
                
                # Reschedule active scans
                self._schedule_existing_scans()
                
                self.logger.info("Rescheduled all active scans")
                
            except Exception as e:
                self.logger.error(f"Failed to reschedule scans: {e}")
    
    def run_scan_now(self, scan_id: int) -> bool:
        """
        Run a scan immediately (outside of schedule)
        
        Args:
            scan_id (int): ID of scan to run
            
        Returns:
            bool: True if scan was started successfully
        """
        with self.app.app_context():
            try:
                scan = Scan.query.get(scan_id)
                if not scan or not scan.is_active:
                    return False
                
                # Check if already running
                with self.scan_lock:
                    if scan_id in self.active_scans:
                        return False
                
                # Create result record
                scan_result = ScanResult(
                    scan_id=scan_id,
                    status='pending'
                )
                db.session.add(scan_result)
                db.session.commit()
                
                # Start scan thread
                scan_thread = threading.Thread(
                    target=self._run_scan_thread,
                    args=(scan, scan_result.id),
                    name=f"manual_scan_thread_{scan_id}"
                )
                
                with self.scan_lock:
                    self.active_scans[scan_id] = scan_thread
                
                scan_thread.start()
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to start manual scan {scan_id}: {e}")
                return False
    
    def get_scan_status(self, scan_id: int) -> Optional[str]:
        """
        Get current status of a scan
        
        Args:
            scan_id (int): ID of scan to check
            
        Returns:
            str: 'running', 'scheduled', 'inactive', or None if not found
        """
        with self.scan_lock:
            if scan_id in self.active_scans:
                return 'running'
        
        try:
            job_id = f"scan_{scan_id}"
            if self.scheduler.get_job(job_id):
                return 'scheduled'
        except:
            pass
        
        with self.app.app_context():
            scan = Scan.query.get(scan_id)
            if scan:
                return 'inactive' if not scan.is_active else 'scheduled'
        
        return None


# Flask integration helpers
def init_scheduler(app):
    """Initialize scheduler with Flask app"""
    max_workers = app.config.get('MAX_CONCURRENT_SCANS', 3)
    scheduler = ScanScheduler(app, max_workers=max_workers)
    return scheduler


def get_scheduler():
    """Get scheduler instance from current app"""
    try:
        from flask import current_app
        return current_app.extensions['scan_scheduler']
    except (RuntimeError, KeyError):
        return None


# CLI command for standalone scheduler
def run_standalone_scheduler():
    """Run scheduler as standalone service"""
    import signal
    import sys
    
    app = create_app()
    scheduler = init_scheduler(app)
    
    def signal_handler(signum, frame):
        print("\nShutting down scheduler...")
        scheduler.shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    with app.app_context():
        scheduler.start()
        print("Scheduler started. Press Ctrl+C to stop.")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            scheduler.shutdown()


if __name__ == "__main__":
    run_standalone_scheduler()