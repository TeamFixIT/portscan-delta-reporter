# run.py
import os
import click
from flask.cli import with_appcontext
from app import create_app, db
from app.models.user import User
from app.models.scan import Scan
from app.models.scan_result import ScanResult
from src.scheduler import init_scheduler
from config import get_config

# Create app instance
app = create_app(get_config())


@app.shell_context_processor
def make_shell_context():
    """Register shell context objects"""
    return {
        'db': db,
        'User': User,
        'Scan': Scan,
        'ScanResult': ScanResult
    }


@app.cli.command()
@with_appcontext
def init_db():
    """Initialize database with tables"""
    db.create_all()
    click.echo('Database initialized.')


@app.cli.command()
@with_appcontext
def create_admin():
    """Create admin user"""
    username = click.prompt('Admin username')
    email = click.prompt('Admin email')
    password = click.prompt('Admin password', hide_input=True)
    
    try:
        admin_user = User.create_user(
            username=username,
            email=email,
            password=password,
            first_name='Admin',
            last_name='User'
        )
        admin_user.is_admin = True
        db.session.commit()
        
        click.echo(f'Admin user {username} created successfully.')
        
    except ValueError as e:
        click.echo(f'Error creating admin user: {e}', err=True)


@app.cli.command()
@with_appcontext
def reset_db():
    """Reset database (WARNING: This will delete all data)"""
    if click.confirm('This will delete all data. Are you sure?'):
        db.drop_all()
        db.create_all()
        click.echo('Database reset successfully.')


@app.cli.command()
def run_scheduler():
    """Run the background scheduler as a separate service"""
    from src.scheduler import run_standalone_scheduler
    run_standalone_scheduler()


@app.before_request
def initialize_scheduler():
    """Initialize scheduler when app starts"""
    if not app.config.get('TESTING'):
        scheduler = init_scheduler(app)
        scheduler.start()

@app.teardown_appcontext
def shutdown_scheduler(exception):
    """Shutdown scheduler when app stops"""
    from src.scheduler import get_scheduler
    scheduler = get_scheduler()
    if scheduler:
        scheduler.shutdown()


if __name__ == '__main__':
    # Get configuration
    config_name = os.environ.get('FLASK_ENV', 'development')
    
    if config_name == 'development':
        # Development server with debug mode
        app.run(
            host='127.0.0.1',
            port=int(os.environ.get('PORT', 2000)),
            debug=True,
            threaded=True
        )
    else:
        # Production - should use gunicorn or similar WSGI server
        app.run(
            host='0.0.0.0',
            port=int(os.environ.get('PORT', 2000)),
            debug=False,
            threaded=True
        )


# requirements.txt content:
"""
Flask==2.3.3
Flask-SQLAlchemy==3.0.5
Flask-Login==0.6.3
Flask-Migrate==4.0.5
Flask-SocketIO==5.3.6
Werkzeug==2.3.7
python-nmap==0.7.1
psutil==5.9.5
netifaces==0.11.0
APScheduler==3.10.4
click==8.1.7
python-dotenv==1.0.0

# Optional dependencies for production
gunicorn==21.2.0
redis==4.6.0
celery==5.3.4

# Development dependencies
pytest==7.4.3
pytest-flask==1.3.0
pytest-cov==4.1.0
black==23.9.1
flake8==6.1.0
"""