---
layout: default
title: Installation
parent: Server
nav_order: 1
---

# Server Installation Guide

This guide covers the installation and initial setup of the Port Scanner Delta Reporter server application.

## Prerequisites

- **Python**: 3.8 or higher
- **Operating System**: Linux, macOS, or Windows
- **Database**: SQLite (default) or PostgreSQL/MySQL
- **Memory**: Minimum 2GB RAM recommended
- **Storage**: 1GB+ for application and logs

## Installation Methods

### Method 1: Quick Install (Recommended)

```bash
# Clone the repository
git clone https://github.com/TeamFixIT/portscan-delta-reporter.git
cd portscan-delta-reporter/server

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run setup command
flask setup

# Create admin user
flask create-admin
```

### Method 2: Manual Installation

#### 1. Clone Repository

```bash
git clone https://github.com/TeamFixIT/portscan-delta-reporter.git
cd portscan-delta-reporter/server
```

#### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 4. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration
nano .env  # or use your preferred editor
```

#### 5. Initialize Database

```bash
# Initialize migrations
flask db init

# Create initial migration
flask db migrate -m "Initial migration"

# Apply migrations
flask db upgrade
```

#### 6. Create Admin User

```bash
flask create-admin
```

Follow the prompts to create your administrator account.

## Environment Configuration

### Required Settings

Edit your `.env` file with these essential configurations:

```bash
# Secret Keys (CRITICAL - Change in production!)
SECRET_KEY=your-secret-key-change-in-production

# Flask Environment
FLASK_ENV=production  # Use 'development' for dev mode

# Database Configuration
# SQLite (default)
SQLALCHEMY_DATABASE_URI=sqlite:///data/app.db

# Or PostgreSQL
# SQLALCHEMY_DATABASE_URI=postgresql://user:password@localhost/dbname

# Session Configuration
SESSION_TYPE=filesystem
SESSION_FILE_DIR=/tmp/flask_session
```

### Optional OAuth Configuration

If you want to enable SSO authentication:

```bash
# Enable OAuth providers
OAUTH2_PROVIDERS=microsoft,github

# Microsoft Entra ID
MICROSOFT_CLIENT_ID=your-client-id
MICROSOFT_CLIENT_SECRET=your-client-secret
MICROSOFT_TENANT_ID=your-tenant-id

# GitHub OAuth
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
```

### Email Configuration

For alert notifications:

```bash
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-email-password
MAIL_DEFAULT_SENDER=noreply@example.com
```

## Running the Server

### Development Mode

```bash
# Using Flask development server
flask run --host=0.0.0.0 --port=5000

# Or using the run script
python run.py
```

### Production Mode (Gunicorn)

```bash
# Install gunicorn if not already installed
pip install gunicorn

# Run with gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 'app:create_app()'

# Or with more options
gunicorn -w 4 \
  --bind 0.0.0.0:5000 \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log \
  --log-level info \
  'app:create_app()'
```

### Running as a Service (systemd)

Create a systemd service file at `/etc/systemd/system/portscanner.service`:

```ini
[Unit]
Description=Port Scanner Delta Reporter
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/portscan-delta-reporter/server
Environment="PATH=/path/to/portscan-delta-reporter/server/venv/bin"
ExecStart=/path/to/portscan-delta-reporter/server/venv/bin/gunicorn \
    -w 4 \
    --bind 0.0.0.0:5000 \
    'app:create_app()'
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable portscanner
sudo systemctl start portscanner
sudo systemctl status portscanner
```

## Post-Installation Steps

### 1. Verify Installation

Access the web interface:
```
http://localhost:5000
```

### 2. Configure First Scan

1. Log in with your admin credentials
2. Navigate to **Scans** → **New Scan**
3. Configure your first scan target

### 3. Set Up Client Agents

Follow the [Client Agent Installation Guide](../client/index.md) to set up scanning clients.

### 4. Configure Scheduled Scans

The scheduler starts automatically. To verify:

```bash
flask list-jobs
```

## Troubleshooting

### Port Already in Use

```bash
# Find process using port 5000
lsof -i :5000  # On Linux/macOS
netstat -ano | findstr :5000  # On Windows

# Kill the process or use a different port
flask run --port=8000
```

### Database Migration Issues

```bash
# Reset database (WARNING: destroys all data)
flask reset-db

# Or manually
rm data/app.db
flask setup
```

### Permission Errors

```bash
# Ensure correct permissions
chmod -R 755 /path/to/server
chown -R www-data:www-data /path/to/server  # Linux

# Create required directories
mkdir -p logs data
```

### Import Errors

```bash
# Reinstall dependencies
pip install --force-reinstall -r requirements.txt
```

## Upgrading

### From Previous Version

```bash
# Pull latest changes
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Update dependencies
pip install --upgrade -r requirements.txt

# Run migrations
flask db upgrade

# Restart service
sudo systemctl restart portscanner
```

## Next Steps

- [Configuration Guide](configuration.md) - Detailed configuration options
- [Usage Guide](usage.md) - Learn how to use the application
- [API Reference](api-reference.md) - API documentation for integration

## Support

For issues or questions:
- GitHub Issues: [TeamFixIT/portscan-delta-reporter](https://github.com/TeamFixIT/portscan-delta-reporter/issues)
- Documentation: [https://teamfixit.github.io/portscan-delta-reporter](https://teamfixit.github.io/portscan-delta-reporter)