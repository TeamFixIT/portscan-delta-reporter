---
layout: default
title: Configuration
parent: Server
nav_order: 2
---

# Server Configuration Guide

Comprehensive guide to configuring the Port Scanner Delta Reporter server application.

## Table of Contents
- [Environment Variables](#environment-variables)
- [Database Configuration](#database-configuration)
- [Authentication](#authentication)
- [Scheduler Configuration](#scheduler-configuration)
- [Logging Configuration](#logging-configuration)
- [Security Settings](#security-settings)

## Environment Variables

All configuration is managed through the `.env` file in the server root directory.

### Core Settings

```bash
# Application Secret Key (REQUIRED)
# Generate: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=your-secret-key-here

# Flask Environment
FLASK_ENV=production  # Options: development, production, testing

# Server Host and Port
HOST=0.0.0.0
PORT=5000
```

### Session Configuration

```bash
# Session Type
SESSION_TYPE=filesystem  # Options: filesystem, redis, memcached

# Session Storage Location
SESSION_FILE_DIR=/tmp/flask_session

# Session Cookie Security
SESSION_COOKIE_SECURE=False  # Set to True when using HTTPS
PERMANENT_SESSION_LIFETIME=24  # Hours
```

## Database Configuration

### SQLite (Default)

```bash
# SQLite - file-based database
SQLALCHEMY_DATABASE_URI=sqlite:///data/app.db

# Disable modification tracking (improves performance)
SQLALCHEMY_TRACK_MODIFICATIONS=False
```

The database file will be created at `server/data/app.db`.

### PostgreSQL

```bash
# PostgreSQL connection string
SQLALCHEMY_DATABASE_URI=postgresql://username:password@localhost:5432/portscanner

# Example with custom options
SQLALCHEMY_DATABASE_URI=postgresql://user:pass@localhost/portscanner?client_encoding=utf8
```

### MySQL

```bash
# MySQL connection string
SQLALCHEMY_DATABASE_URI=mysql+pymysql://username:password@localhost:3306/portscanner

# With SSL
SQLALCHEMY_DATABASE_URI=mysql+pymysql://user:pass@localhost/portscanner?ssl=true
```

### Database Pool Settings

```bash
# Connection pool size
SQLALCHEMY_POOL_SIZE=10
SQLALCHEMY_MAX_OVERFLOW=20
SQLALCHEMY_POOL_TIMEOUT=30
SQLALCHEMY_POOL_RECYCLE=3600
```

## Authentication

### Local Authentication

Enabled by default. Users can register and log in with username/password.

### OAuth/SSO Configuration

#### Microsoft Entra ID (Azure AD)

1. **Register Application in Azure Portal**
   - Navigate to Azure Active Directory → App registrations
   - Create new registration
   - Add redirect URI: `http://your-domain:5000/auth/oauth_callback/microsoft`

2. **Configure Environment Variables**

```bash
# Enable Microsoft provider
OAUTH2_PROVIDERS=microsoft

# Microsoft credentials
MICROSOFT_CLIENT_ID=your-application-id
MICROSOFT_CLIENT_SECRET=your-client-secret
MICROSOFT_TENANT_ID=your-tenant-id
```

#### GitHub OAuth

1. **Register OAuth App on GitHub**
   - Settings → Developer settings → OAuth Apps → New OAuth App
   - Authorization callback URL: `http://your-domain:5000/auth/oauth_callback/github`

2. **Configure Environment Variables**

```bash
# Enable GitHub provider
OAUTH2_PROVIDERS=github

# GitHub credentials
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
```

#### Google OAuth

```bash
# Enable Google provider
OAUTH2_PROVIDERS=google

# Google credentials
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

#### Multiple Providers

Enable multiple OAuth providers:

```bash
OAUTH2_PROVIDERS=microsoft,github,google
```

### Password Requirements

Password validation is built-in with these requirements:
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number

These are enforced in the registration form and user profile updates.

## Scheduler Configuration

The application uses APScheduler for task scheduling.

### Basic Settings

```bash
# Maximum concurrent scheduled jobs
SCHEDULER_MAX_WORKERS=10

# Timezone for scheduler
SCHEDULER_TIMEZONE=UTC
```

### Managing Scheduled Jobs

```bash
# List all scheduled jobs
flask list-jobs

# Reload schedules from database
flask reload-schedules
```

## Logging Configuration

### Log Levels

```bash
# Log level
LOG_LEVEL=INFO  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

# Log directory
LOG_DIR=logs
```

### Log Files

The application creates three log files:

1. **app.log** - General application logs
2. **error.log** - Error-level logs only
3. **scheduler.log** - Scheduler-specific logs

### Log Rotation

Logs automatically rotate when they reach 10MB, keeping 5 backup files.

### Viewing Logs

- **Web Interface**: Navigate to **Settings** → **Logs**
- **Command Line**: `tail -f logs/app.log`

## Security Settings

### Secret Keys

```bash
# Application secret key (CRITICAL)
SECRET_KEY=your-secret-key

# Password salt for additional security
SECURITY_PASSWORD_SALT=your-password-salt
```

**Generate secure keys:**

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Session Security

```bash
# Secure cookies (HTTPS required)
SESSION_COOKIE_SECURE=True

# HTTPOnly cookies (prevent XSS)
SESSION_COOKIE_HTTPONLY=True

# SameSite cookie policy
SESSION_COOKIE_SAMESITE=Lax
```

### CORS Configuration

```bash
# Enable CORS for API
CORS_ENABLED=False

# Allowed origins (comma-separated)
CORS_ORIGINS=https://example.com,https://app.example.com
```

## Advanced Configuration

### Client Heartbeat Monitoring

```bash
# Heartbeat check interval (minutes)
CLIENT_HEARTBEAT_INTERVAL=3

# Heartbeat timeout (minutes)
CLIENT_HEARTBEAT_TIMEOUT=5
```

Clients that don't send heartbeats within the timeout are marked offline.

### Delta Report Generation

Delta reports are automatically generated when:
1. A scan completes
2. A previous scan result exists for comparison

No configuration needed - this is automatic.

### Rate Limiting

```bash
# Enable rate limiting
RATELIMIT_ENABLED=True

# Storage backend
RATELIMIT_STORAGE_URL=memory://  # Or redis://localhost:6379
```

### File Upload Limits

```bash
# Maximum file upload size (MB)
MAX_CONTENT_LENGTH=16
```

## Configuration Best Practices

### Production Checklist

- [ ] Change `SECRET_KEY` to a secure random value
- [ ] Set `FLASK_ENV=production`
- [ ] Enable `SESSION_COOKIE_SECURE=True` (with HTTPS)
- [ ] Configure proper database (not SQLite for high-load)
- [ ] Set up email notifications
- [ ] Configure log rotation and monitoring
- [ ] Enable backups for database
- [ ] Use environment-specific `.env` files
- [ ] Restrict OAuth redirect URIs
- [ ] Configure firewall rules

### Development Settings

```bash
FLASK_ENV=development
DEBUG=True
SQLALCHEMY_ECHO=True  # Log all SQL queries
LOG_LEVEL=DEBUG
SESSION_COOKIE_SECURE=False
```

### Testing Settings

```bash
FLASK_ENV=testing
TESTING=True
SQLALCHEMY_DATABASE_URI=sqlite:///:memory:
WTF_CSRF_ENABLED=False
```

## Environment-Specific Configuration

### Using Multiple .env Files

```bash
# Load specific environment
flask --env=production run

# Or set explicitly
export FLASK_ENV=production
flask run
```

### Configuration Precedence

1. Environment variables
2. `.env` file
3. Default values in `config.py`

## Troubleshooting Configuration

### Configuration Not Loading

```bash
# Check if .env exists
ls -la .env

# Verify environment variables
flask shell
>>> from flask import current_app
>>> print(current_app.config['SECRET_KEY'])
```

### Database Connection Issues

```bash
# Test database connection
flask shell
>>> from app import db
>>> db.engine.connect()
```

## Configuration API

Settings can also be managed through the admin web interface:

1. Log in as administrator
2. Navigate to **Settings** → **Configs**
3. Modify settings in the web UI
4. Changes are saved to `.env` file

**Note**: Application restart required for some changes to take effect.

## Next Steps

- [Usage Guide](usage.md) - Learn how to use the application
- [API Reference](api-reference.md) - API documentation