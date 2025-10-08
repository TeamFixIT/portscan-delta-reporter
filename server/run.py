#!/usr/bin/env python3
"""
Flask Application Entry Point

Run this file to start the Port Scanner Delta Reporter server.
"""

import os
import click
from flask.cli import with_appcontext
from app import create_app, db, socketio, scheduler
from app.models.user import User
from app.models.scan import Scan
from app.models.scan_result import ScanResult
from config import get_config

# Create app instance
app = create_app(get_config())


@app.shell_context_processor
def make_shell_context():
    """Register shell context objects"""
    return {"db": db, "User": User, "Scan": Scan, "ScanResult": ScanResult}


@app.cli.command()
@with_appcontext
def init_db():
    """Initialize database with tables"""
    db.create_all()
    click.echo("Database initialized.")


@app.cli.command()
@with_appcontext
def create_admin():
    """Create admin user"""
    username = click.prompt("Admin username")
    email = click.prompt("Admin email")
    password = click.prompt("Admin password", hide_input=True)

    try:
        admin_user = User.create_user(
            username=username,
            email=email,
            password=password,
            first_name="Admin",
            last_name="User",
        )
        admin_user.is_admin = True
        db.session.commit()

        click.echo(f"Admin user {username} created successfully.")

    except ValueError as e:
        click.echo(f"Error creating admin user: {e}", err=True)


from app.scheduler import (
    scheduler_service,
)  # or wherever SchedulerService is defined


@app.cli.command()
@with_appcontext
def reset_db():
    """Reset database and clear all APScheduler jobs."""
    if click.confirm("This will delete all data and all scheduled jobs. Continue?"):
        # Clear all scheduled jobs
        try:
            cleared = scheduler_service.clear_all_jobs()
            if cleared:
                click.echo("All scheduled jobs cleared successfully.")
            else:
                click.echo("No jobs cleared (scheduler not active).")
        except Exception as e:
            click.echo(f"Warning: Could not clear scheduled jobs: {e}")

        # Reset the database
        db.drop_all()
        db.create_all()

        click.echo("Database reset successfully.")


if __name__ == "__main__":
    # Get configuration
    config_name = os.environ.get("FLASK_ENV", "development")

    if config_name == "development":
        # Development server with debug mode
        app.run(
            host="127.0.0.1",
            port=int(os.environ.get("PORT", 2000)),
            debug=True,
            threaded=True,
        )
    else:
        # Production - should use gunicorn or similar WSGI server
        app.run(
            host="0.0.0.0",
            port=int(os.environ.get("PORT", 2000)),
            debug=False,
            threaded=True,
        )
