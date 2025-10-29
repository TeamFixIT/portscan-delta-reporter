"""
Flask Application Factory

This module creates and configures the Flask application for the
Port Scanner Delta Reporter server.
"""

import os
import click
from pathlib import Path
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_session import Session
from dotenv import load_dotenv


load_dotenv()

# initialise extensions
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
socketio = SocketIO()
sess = Session()

# Import scheduler
from app.logging_config import setup_logging, get_logger
from app.scheduler import scheduler_service
from .config import Config

logger = get_logger(__name__)


def create_app():
    """
    Application factory pattern for Flask app creation

    Returns:
        Flask: Configured Flask application
    """
    BASE_DIR = Path(__file__).resolve().parent.parent

    app = Flask(__name__)

    app.config.from_prefixed_env()

    app.config.from_object(Config)

    # Ensure session directory exists
    Path(app.config["SESSION_FILE_DIR"]).mkdir(parents=True, exist_ok=True)

    # Ensure instance directory exists
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    # initialise extensions with app
    db.init_app(app)
    login_manager.init_app(app)

    # initialise migrations directory if it doesn't exist
    migrations_dir = BASE_DIR / "migrations"
    migrate.init_app(app, db, directory=str(migrations_dir))

    socketio.init_app(app, cors_allowed_origins="*", async_mode="gevent")
    sess.init_app(app)

    # Configure Flask-Login
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"

    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User

        return User.query.get(int(user_id))

    # Import models to ensure they are registered with SQLAlchemy
    from app.models import (
        user,
        client,
        scan,
        scan_result,
        scan_task,
        delta_report,
    )

    # initialise scheduler and websocket
    scheduler_service.init_app(app)

    # Create database tables
    with app.app_context():
        if os.environ.get("WERKZEUG_RUN_MAIN") == "true":

            try:
                setup_logging(
                    app=app,
                    log_level=os.getenv("LOG_LEVEL", "INFO"),
                    log_dir=os.getenv("LOG_DIR", BASE_DIR / "logs"),
                )
                scheduler_service.start()
                logger.info("Scheduler service started successfully")
            except Exception as e:
                logger.error(f"Failed to start scheduler: {str(e)}")

    # Register blueprints
    from app.routes.main import bp as main_bp
    from app.routes.auth import bp as auth_bp
    from app.routes.delta import bp as delta_bp
    from app.routes.api import bp as api_bp
    from app.routes.scan import bp as scan_bp
    from app.routes.dashboard import bp as dashboard_bp
    from app.routes.configs import bp as configs_bp
    from app.routes.sse import sse_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(scan_bp, url_prefix="/api")
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")
    app.register_blueprint(delta_bp, url_prefix="/api")
    app.register_blueprint(configs_bp, url_prefix="/admin")
    app.register_blueprint(sse_bp, url_prefix="/api")

    # Register error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        from flask import render_template

        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        from flask import render_template

        db.session.rollback()
        return render_template("errors/500.html"), 500

    # Register scheduler shutdown on app teardown
    @app.teardown_appcontext
    def shutdown_scheduler(exception=None):
        pass  # Scheduler persists across requests

    @app.cli.command()
    def list_jobs():
        """List all scheduled jobs"""
        jobs = scheduler_service.get_all_jobs()
        for job in jobs:
            print(f"Job: {job['name']} - Next run: {job['next_run_time']}")

    @app.cli.command()
    def reload_schedules():
        """Reload all scheduled scans from database"""
        from app.models.scan import Scan
        from sqlalchemy import and_

        scans = Scan.query.filter(
            and_(Scan.is_scheduled == True, Scan.is_active == True)
        ).all()

        for scan in scans:
            scheduler_service.schedule_scan(scan)

        print(f"Reloaded {len(scans)} scheduled scans")

    @app.cli.command()
    def init_db():
        """Initialise database with tables"""
        db.create_all()
        click.echo("Database tables created.")

    @app.cli.command()
    def reset_db():
        """Reset database and clear all APScheduler jobs."""
        if click.confirm("This will delete all data and all scheduled jobs. Continue?"):
            # Clear all scheduled jobs
            # Reset the database
            db.drop_all()
            db.create_all()

            click.echo("Database reset successfully.")

    @app.cli.command()
    @click.option("--message", "-m", default=None, help="Migration message")
    def new_migration(message):
        """Create a new migration after model changes"""
        from flask_migrate import migrate as create_migration

        migrations_dir = BASE_DIR / "migrations"

        if not migrations_dir.exists():
            click.echo(
                "Error: Migrations not initialised. Run 'flask setup' first.", err=True
            )
            return

        if not message:
            message = click.prompt("Enter migration message")

        click.echo(f"Creating migration: {message}")
        try:
            create_migration(message=message, directory=str(migrations_dir))
            click.echo("Migration created successfully.")
            click.echo("\nTo apply the migration, run: flask db upgrade")
        except Exception as e:
            click.echo(f"✗ Error creating migration: {e}", err=True)

    @app.cli.command()
    def create_admin():
        """Create admin user"""
        from app.models.user import User

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

    @app.cli.command()
    def setup():
        """Complete setup: initialise migrations, create tables, and setup defaults"""
        from flask_migrate import (
            init as migrate_init,
            migrate as create_migration,
            upgrade,
        )

        migrations_dir = BASE_DIR / "migrations"

        # Step 1: initialise Flask-Migrate if needed
        if not migrations_dir.exists():
            click.echo("Step 1/4: Initializing Flask-Migrate...")
            migrate_init(directory=str(migrations_dir))
            click.echo("Migrations directory created.")
        else:
            click.echo("Migrations directory already exists.")

        # Step 2: Check if we need to create initial migration
        versions_dir = migrations_dir / "versions"
        has_migrations = versions_dir.exists() and any(versions_dir.glob("*.py"))

        if not has_migrations:
            click.echo("\nStep 2/4: Creating initial migration...")
            try:
                create_migration(
                    message="Initial migration", directory=str(migrations_dir)
                )
                click.echo("Initial migration created.")
            except Exception as e:
                click.echo(f"✗ Error creating migration: {e}", err=True)
                click.echo("\nTrying to create tables directly...")
                db.create_all()
                click.echo("Database tables created directly.")
        else:
            click.echo("\nMigrations already exist.")

        # Step 3: Run migrations
        click.echo("\nStep 3/4: Applying migrations...")
        try:
            upgrade(directory=str(migrations_dir))
            click.echo("Database migrations applied.")
        except Exception as e:
            click.echo(f"Warning: Migration upgrade failed: {e}", err=True)
            click.echo("Checking if tables need to be created...")
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            if not tables:
                click.echo("Creating tables directly...")
                db.create_all()
                click.echo("Database tables created.")

        click.echo("\n" + "=" * 60)
        click.echo("Setup complete!")
        click.echo("=" * 60)
        click.echo("\nNext steps:")
        click.echo("  1. Create an admin user: flask create-admin")
        click.echo("  2. Run the server: portscanner-server")
        click.echo("\nOr run both: flask create-admin && portscanner-server")
        click.echo("=" * 60)

    return app
