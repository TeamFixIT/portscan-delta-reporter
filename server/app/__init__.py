"""
Flask Application Factory

This module creates and configures the Flask application for the
Port Scanner Delta Reporter server.
"""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_socketio import SocketIO
from config import Config

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
socketio = SocketIO()


def create_app(config_class=Config):
    """
    Application factory pattern for Flask app creation

    Args:
        config_class: Configuration class to use

    Returns:
        Flask: Configured Flask application
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app, cors_allowed_origins="*")

    # Configure Flask-Login
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"

    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User

        return User.query.get(int(user_id))

    # Register blueprints

    from app.routes.main import bp as main_bp
    from app.routes.auth import bp as auth_bp
    from app.routes.api import bp as api_bp
    from app.routes.dashboard import bp as dashboard_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")

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

    # Create database tables
    with app.app_context():
        db.create_all()

        # Start background scheduler
        from app.scheduler import start_scheduler

        if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
            start_scheduler(app)

    return app


# Import models to ensure they are registered with SQLAlchemy
from app.models import user, scan, scan_result
