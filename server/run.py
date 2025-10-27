#!/usr/bin/env python3
"""
Flask Application Entry Point
"""
import os
from app import create_app, socketio, db
from flask_migrate import upgrade
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = create_app()

# === MOVE STARTUP LOGIC HERE ===
with app.app_context():
    BASE_DIR = Path(__file__).resolve().parent
    migrations_dir = BASE_DIR / "migrations"

    try:
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()

        if not tables:
            logger.warning("No database tables found.")
        else:
            logger.info(f"Database ready with {len(tables)} tables")

            # Apply pending migrations
            if migrations_dir.exists():
                upgrade(directory=str(migrations_dir))
                logger.info("Migrations applied")

    except Exception as e:
        logger.error(f"Database check failed: {e}")

    # Start scheduler only in main process (not during reloader)
    if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN"):
        from app.scheduler import scheduler_service

        scheduler_service.start()
        logger.info("Scheduler started")


def main():
    # Check if first run
    db_path = BASE_DIR / "data" / "app.db"
    first_run = not db_path.exists() or not migrations_dir.exists()

    if first_run:
        print("\n" + "=" * 60)
        print("FIRST TIME SETUP REQUIRED")
        print("=" * 60)
        print("\nPlease run:\n")
        print("  flask setup")
        print("  flask create-admin")
        print("  portscanner-server")
        print("=" * 60 + "\n")
        return

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV") == "development"

    if debug:
        print(f"\nStarting on {host}:{port} | Debug: {debug}\n")
        socketio.run(app, host=host, port=port, debug=debug, use_reloader=False)
    else:
        print("Use gunicorn to run the server in production mode.")


if __name__ == "__main__":
    main()
