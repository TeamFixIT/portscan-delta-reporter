# Port Scanner Delta Reporter - Setup Guide

## Quick Start (Automated)

```bash
# 1. Run the automated setup script
pip install -e .

flask setup

flask create-admin

portscanner-server
```

## Manual Installation

### 1. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Package

```bash
# Install in development mode
pip install -e .

# Or for production
pip install .
```

### 3. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and set at minimum:
# - SECRET_KEY (generate with: python -c "import secrets; print(secrets.token_hex(32))")
# - SQLALCHEMY_DATABASE_URI (optional, defaults to SQLite)
```

### 4. Initialize Database

```bash
# Run complete setup (this does everything in one command)
flask setup
```

This command will:
1. Initialize Flask-Migrate
2. Create initial migration
3. Apply migrations to database
4. Initialize default settings

### 5. Create Admin User

```bash
flask create-admin
```

### 6. Start Server

```bash
portscanner-server
```

Or for development with auto-reload:
```bash
FLASK_ENV=development portscanner-server
```

## Available Flask Commands

### Database Management

```bash
# Complete setup (first time only)
flask setup

# Create a new migration after model changes
flask new-migration -m "Description of changes"

# Apply pending migrations
flask db upgrade

# Rollback last migration
flask db downgrade

# Initialize database tables (alternative to migrations)
flask init-db

# Reset database (WARNING: deletes all data)
flask reset-db
```

### User Management

```bash
# Create admin user
flask create-admin
```

### Settings Management

```bash
# Initialize/reset default settings
flask init-settings
```

### Scheduler Management

```bash
# Start scheduler manually
flask init-scheduler

# List all scheduled jobs
flask list-jobs

# Reload scheduled scans from database
flask reload-schedules
```

## Production Deployment

### Using Gunicorn (Recommended)

```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"
```

### Using systemd (Linux)

Create `/etc/systemd/system/portscanner.service`:

```ini
[Unit]
Description=Port Scanner Delta Reporter
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/portscanner-server
Environment="PATH=/path/to/portscanner-server/venv/bin"
ExecStart=/path/to/portscanner-server/venv/bin/portscanner-server

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable portscanner
sudo systemctl start portscanner
```

## Database Migrations Workflow

When you modify database models:

```bash
# 1. Make changes to your models in app/models/

# 2. Create a migration
flask new-migration -m "Added new field to User model"

# 3. Review the migration file in migrations/versions/

# 4. Apply the migration
flask db upgrade

# 5. If something goes wrong, rollback
flask db downgrade
```

## Troubleshooting

### "No module named 'run'" error
```bash
pip uninstall portscanner-server -y
pip install -e .
```

### "no such table" errors
```bash
flask setup
```

### Migrations directory not found
```bash
flask setup
```

### Reset everything and start fresh
```bash
# WARNING: This deletes all data
rm -rf migrations/ data/
flask setup
flask create-admin
```

### Scheduler not starting
```bash
# Reload scheduled scans
flask reload-schedules

# Or restart scheduler
flask init-scheduler
```

## Environment Variables

```bash
# Required
SECRET_KEY=your-secret-key-here

# Optional
SQLALCHEMY_DATABASE_URI=sqlite:///path/to/db.db  # Default: ./data/app.db
HOST=0.0.0.0                                      # Default: 127.0.0.1
PORT=5000                                         # Default: 5000
FLASK_ENV=development                             # development or production
```

## Directory Structure

```
portscanner-server/
├── app/                    # Main application package
│   ├── __init__.py        # Application factory
│   ├── __main__.py        # Entry point
│   ├── models/            # Database models
│   ├── routes/            # Route blueprints
│   ├── services/          # Business logic
│   ├── static/            # Static files
│   └── templates/         # Jinja2 templates
├── migrations/            # Flask-Migrate migrations
├── data/                  # SQLite database (if using SQLite)
├── venv/                  # Virtual environment
├── .env                   # Environment variables
├── pyproject.toml        # Package configuration
├── setup_app.sh          # Automated setup script
└── start.sh              # Start script
```