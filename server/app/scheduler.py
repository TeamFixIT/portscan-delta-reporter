"""
Background scheduler for database operations
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import logging

# Set up logging for scheduler
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = None


def check_client_heartbeats():
    """
    Check for clients that haven't sent heartbeats recently and mark them offline
    This should run frequently (every 1-2 minutes)
    """
    from app import db
    from app.models.client import Client
    from datetime import datetime, timedelta

    try:
        # Define heartbeat timeout (e.g., 3 minutes)
        heartbeat_timeout = timedelta(minutes=3)
        cutoff_time = datetime.utcnow() - heartbeat_timeout

        # Find clients that are marked as online but haven't sent heartbeat recently
        stale_clients = Client.query.filter(
            Client.status == "online", Client.last_seen < cutoff_time
        ).all()

        offline_count = 0
        for client in stale_clients:
            logger.info(
                f"Marking client {client.client_id} ({client.hostname}) as offline - last seen: {client.last_seen}"
            )
            client.mark_offline()
            offline_count += 1

        if offline_count > 0:
            db.session.commit()
            logger.info(
                f"Marked {offline_count} clients as offline due to missed heartbeats"
            )

        # Log current status summary
        total_clients = Client.query.count()
        online_clients = Client.query.filter_by(status="online").count()
        offline_clients = Client.query.filter_by(status="offline").count()

        logger.info(
            f"Client Status Summary - Total: {total_clients}, Online: {online_clients}, Offline: {offline_clients}"
        )

    except Exception as e:
        logger.error(f"Error checking client heartbeats: {str(e)}")
        db.session.rollback()


def start_scheduler(app):
    global scheduler

    if scheduler is not None:
        return  # Scheduler already started

    scheduler = BackgroundScheduler(daemon=True)

    # CRITICAL: Check for missed heartbeats every minute
    scheduler.add_job(
        func=lambda: run_with_app_context(app, check_client_heartbeats),
        trigger=IntervalTrigger(minutes=1),
        id="check_heartbeats",
        name="Check Client Heartbeats",
        replace_existing=True,
    )

    try:
        scheduler.start()
        logger.info("Scheduler started successfully - heartbeat monitoring active")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {str(e)}")


def run_with_app_context(app, func):
    """
    Execute a function within Flask application context
    This ensures database connections and app context are available
    """
    with app.app_context():
        func()


def stop_scheduler():
    """
    Stop the scheduler (useful for testing or shutdown)
    """
    global scheduler
    if scheduler:
        scheduler.shutdown()
        scheduler = None
        logger.info("Scheduler stopped")
