# Flask Production Setup Guide

Complete guide for deploying a Flask application using Gunicorn, Gevent, and Nginx on Ubuntu.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [System Dependencies](#system-dependencies)
3. [Application Setup](#application-setup)
4. [Gunicorn Configuration](#gunicorn-configuration)
5. [Systemd Service](#systemd-service)
6. [Nginx Configuration](#nginx-configuration)
7. [SSL/HTTPS Setup](#ssl-https-setup)
8. [Monitoring and Maintenance](#monitoring-and-maintenance)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- Ubuntu 20.04 LTS or newer
- Non-root user with sudo privileges
- Flask application
- Basic understanding of Linux command line

---

## System Dependencies

### 1. Update System Packages

```bash
sudo apt update
sudo apt upgrade -y
```

### 2. Install Required Packages

```bash
sudo apt install -y python3-pip python3-venv nginx
```

### 3. Configure Firewall

```bash
# Enable firewall if not already enabled
sudo ufw enable

# Allow SSH (important!)
sudo ufw allow OpenSSH

# Allow HTTP and HTTPS
sudo ufw allow 'Nginx Full'

# Check status
sudo ufw status
```

---

## Application Setup

### 1. Download and Extract Application

```bash
# Download latest release from GitHub
wget https://github.com/TeamFixIT/portscan-delta-reporter/releases/download/v1.0.0/server-release-1.zip

# Unzip the release
unzip server-release-1.zip

# Navigate to the app directory
cd <app> # TODO update this
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Application with Dependencies

This application uses a `pyproject.toml` file which includes all dependencies:

```bash
# Install the application and all dependencies
pip install .

# Or for development with dev dependencies
pip install .[dev]
```

The `pyproject.toml` includes all required dependencies:
- Flask and Flask extensions (Flask-SQLAlchemy, etc.)
- Gunicorn with gevent worker
- Database tools (Alembic, SQLAlchemy)
- Additional utilities (pandas, numpy, python-nmap, etc.)

### 4. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit with your configuration
nano .env
```

Add your specific configuration:

```ini
# .env
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///instance/app.db
FLASK_ENV=production
# Add other required environment variables
```

### 5. initialise Database (if applicable)

```bash
# Run database migrations
flask db upgrade

# Or if using setup script
./setup_server.sh
```

### 6. Verify Installation

```bash
# Test the application runs
python run.py
# Press Ctrl+C to stop

# Verify all dependencies installed
pip list | grep -E '(Flask|gunicorn|gevent)'
```

---

## Gunicorn Configuration

### 1. Create Gunicorn Config File

Create `gunicorn_config.py` in your application directory:

```bash
nano gunicorn_config.py
```

Add the following configuration:

```python
# Gunicorn configuration file
import multiprocessing

# Bind to localhost (nginx will proxy to this)
bind = "127.0.0.1:8000"

# Worker configuration
workers = 1  # Use 1 worker with gevent
worker_class = "gevent"
worker_connections = 1000

# Timeout and keepalive
timeout = 120
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Process naming
proc_name = "portscan-reporter"

# Daemon mode (systemd will handle this)
daemon = False
```

### 2. Test Gunicorn Manually

```bash
# Make sure you're in your venv
source venv/bin/activate

# Test run (Ctrl+C to stop)
gunicorn --config gunicorn_config.py --worker-class gevent -w 1 run:app
```

Replace `run:app` with your actual module:app reference.

---

## Systemd Service

### 1. Create Service File

```bash
sudo nano /etc/systemd/system/portscan-reporter.service
```

### 2. Add Service Configuration

Replace paths and user information with your actual values:

```ini
[Unit]
Description=Portscan Delta Reporter
After=network.target

[Service]
User=yourusername
Group=yourusername
WorkingDirectory=/path/to/your/app
Environment="PATH=/path/to/your/app/venv/bin"
ExecStart=/path/to/your/app/venv/bin/gunicorn --config gunicorn_config.py --worker-class gevent -w 1 run:app

# Restart policy
Restart=always
RestartSec=10

# Optional: Load environment variables from .env file
# EnvironmentFile=/path/to/your/app/.env

# Security (optional but recommended)
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

**Example for the portscan-delta-reporter:**

```ini
[Unit]
Description=Portscan Delta Reporter Flask Application
After=network.target

[Service]
User=it03
Group=it03
WorkingDirectory=/home/it03/portscan-delta-reporter/server
Environment="PATH=/home/it03/portscan-delta-reporter/server/venv/bin"
ExecStart=/home/it03/portscan-delta-reporter/server/venv/bin/gunicorn --config gunicorn_config.py --worker-class gevent -w 1 run:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 3. Enable and Start Service

```bash
# Reload systemd daemon
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable portscan-reporter

# Start the service
sudo systemctl start portscan-reporter

# Check status
sudo systemctl status portscan-reporter
```

### 4. Useful Systemd Commands

```bash
# Stop service
sudo systemctl stop portscan-reporter

# Restart service
sudo systemctl restart portscan-reporter

# View logs (last 50 lines)
sudo journalctl -u portscan-reporter -n 50

# Follow logs in real-time
sudo journalctl -u portscan-reporter -f

# View logs since last boot
sudo journalctl -u portscan-reporter -b
```

---

## Nginx Configuration

### 1. Create Nginx Configuration File

Check if `sites-available` directory exists:

```bash
ls -la /etc/nginx/
```

**Option A: Using sites-available (Debian/Ubuntu default)**

```bash
sudo nano /etc/nginx/sites-available/portscan-reporter
```

**Option B: Using conf.d**

```bash
sudo nano /etc/nginx/conf.d/portscan-reporter.conf
```

### 2. Add Nginx Configuration

```nginx
upstream flask_backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-server-ip-or-domain;  # Change this!

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Max upload size
    client_max_body_size 10M;

    # Root location - proxy to Flask
    location / {
        proxy_pass http://flask_backend;
        proxy_redirect off;
        
        # Standard proxy headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        
    }

    # Static files (if applicable)
    location /static/ {
        alias /path/to/your/app/app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Health check endpoint
    location /health {
        access_log off;
        proxy_pass http://flask_backend/health;
        proxy_set_header Host $host;
    }

    # Logging
    access_log /var/log/nginx/portscan-reporter-access.log;
    error_log /var/log/nginx/portscan-reporter-error.log;
}
```

### 3. Fix Static Files Permissions

**IMPORTANT:** Nginx needs read access to your static files.

```bash
# Give execute permission on parent directories
sudo chmod 755 /home/yourusername
sudo chmod 755 /home/yourusername/your-app
sudo chmod 755 /home/yourusername/your-app/server

# Give read/execute permission to static files
sudo chmod -R 755 /home/yourusername/your-app/server/app
sudo chmod -R 755 /home/yourusername/your-app/server/app/static
```

**Example:**

```bash
sudo chmod 755 /home/it03
sudo chmod 755 /home/it03/portscan-delta-reporter
sudo chmod 755 /home/it03/portscan-delta-reporter/server
sudo chmod -R 755 /home/it03/portscan-delta-reporter/server/app
```

### 4. Enable Site and Restart Nginx

**If using sites-available:**

```bash
# Create symbolic link
sudo ln -s /etc/nginx/sites-available/portscan-reporter /etc/nginx/sites-enabled/

# Remove default site (optional)
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx
```

**If using conf.d:**

```bash
# Test configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx
```

### 5. Verify Nginx is Running

```bash
sudo systemctl status nginx
```

---

## SSL/HTTPS Setup

### Option 1: Let's Encrypt (Recommended for Public Domains)

**Prerequisites:**
- Domain name pointing to your server
- Ports 80 and 443 open

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate (replace with your domain)
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Certbot will automatically:
# - Obtain SSL certificate
# - Update nginx configuration
# - Set up auto-renewal

# Test auto-renewal
sudo certbot renew --dry-run
```

### Option 2: Self-Signed Certificate (Development/Internal)

```bash
# Generate self-signed certificate
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/portscan-reporter.key \
    -out /etc/ssl/certs/portscan-reporter.crt

# Update nginx configuration
sudo nano /etc/nginx/sites-available/portscan-reporter
```

Add SSL configuration:

```nginx
# HTTPS server
server {
    listen 443 ssl http2;
    server_name your-server-ip;

    ssl_certificate /etc/ssl/certs/portscan-reporter.crt;
    ssl_certificate_key /etc/ssl/private/portscan-reporter.key;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # ... rest of your configuration (same as HTTP version)
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name your-server-ip;
    return 301 https://$server_name$request_uri;
}
```

Restart nginx:

```bash
sudo nginx -t
sudo systemctl restart nginx
```

---

## Monitoring and Maintenance

### Check Service Status

```bash
# Application status
sudo systemctl status portscan-reporter

# Nginx status
sudo systemctl status nginx

# Check listening ports
sudo netstat -tlnp | grep -E ':(80|443|8000)'
```

### View Logs

```bash
# Application logs (real-time)
sudo journalctl -u portscan-reporter -f

# Nginx access logs
sudo tail -f /var/log/nginx/portscan-reporter-access.log

# Nginx error logs
sudo tail -f /var/log/nginx/portscan-reporter-error.log

# Combined view
sudo tail -f /var/log/nginx/portscan-reporter-*.log
```

### Restart Services

```bash
# Restart application only
sudo systemctl restart portscan-reporter

# Restart nginx only
sudo systemctl restart nginx

# Restart both
sudo systemctl restart portscan-reporter nginx
```

### Update Application

```bash
# 1. Stop the service
sudo systemctl stop portscan-reporter

# 2. Update code (git pull, copy files, etc.)
cd /path/to/your/app
# git pull origin main

# 3. Update dependencies if needed
source venv/bin/activate
pip install -r requirements.txt

# 4. Restart service
sudo systemctl start portscan-reporter

# 5. Check status
sudo systemctl status portscan-reporter
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check detailed logs
sudo journalctl -u portscan-reporter -n 100 --no-pager

# Check if port 8000 is already in use
sudo netstat -tlnp | grep :8000

# Test gunicorn manually
cd /path/to/your/app
source venv/bin/activate
gunicorn --config gunicorn_config.py --worker-class gevent -w 1 run:app
```

### 502 Bad Gateway

This means nginx can't connect to your Flask app.

```bash
# Check if Flask app is running
sudo systemctl status portscan-reporter

# Check if it's listening on port 8000
curl http://localhost:8000/

# Check nginx error logs
sudo tail -f /var/log/nginx/portscan-reporter-error.log
```

### 403 Forbidden (Static Files)

Permission issue. Fix with:

```bash
# Fix directory permissions
sudo chmod 755 /home/yourusername
sudo chmod -R 755 /path/to/your/app

# Check nginx can read the file
sudo -u www-data cat /path/to/static/file.js
```

### High Memory/CPU Usage

```bash
# Check process resources
top -u yourusername

# View application logs for errors
sudo journalctl -u portscan-reporter -f
```

### Can't Connect from External Network

```bash
# Check firewall
sudo ufw status

# Make sure nginx is listening on the right interface
sudo netstat -tlnp | grep nginx

# Check if server_name in nginx config matches your IP/domain
sudo nginx -t
```

---

## Security Best Practices

### 1. Keep System Updated

```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Use Environment Variables for Secrets

Never hardcode secrets in your code. Use environment files:

```bash
# Create .env file
nano /path/to/your/app/.env
```

```ini
SECRET_KEY=your-secret-key-here
DATABASE_URL=your-database-url
```

Update systemd service:

```ini
[Service]
EnvironmentFile=/path/to/your/app/.env
```

### 3. Limit File Permissions

```bash
# Restrict .env file
chmod 600 /path/to/your/app/.env
```

### 4. Configure Fail2Ban (Optional)

Protect against brute force attacks:

```bash
sudo apt install fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 5. Regular Backups

```bash
# Backup application data, database, etc.
# Set up automated backups with cron
```

---

## Performance Tuning

### Gunicorn Workers

For CPU-bound tasks, increase workers:

```python
# gunicorn_config.py
workers = (2 * multiprocessing.cpu_count()) + 1
```

### Nginx Caching

Add caching for static files:

```nginx
location /static/ {
    alias /path/to/static/;
    expires 1y;
    add_header Cache-Control "public, immutable";
    access_log off;
}
```

### Optimize Connection Limits

```python
# gunicorn_config.py
worker_connections = 2000  # Increase if needed
```

---

## Quick Reference Commands

```bash
# Service Management
sudo systemctl start portscan-reporter
sudo systemctl stop portscan-reporter
sudo systemctl restart portscan-reporter
sudo systemctl status portscan-reporter

# Nginx Management
sudo systemctl restart nginx
sudo nginx -t
sudo systemctl reload nginx

# Logs
sudo journalctl -u portscan-reporter -f
sudo tail -f /var/log/nginx/*.log

# Testing
curl http://localhost:8000/
curl http://localhost/
```

---

## Checklist

- [ ] System packages updated
- [ ] Python virtual environment created
- [ ] Dependencies installed
- [ ] Gunicorn config created
- [ ] Systemd service created and enabled
- [ ] Nginx installed and configured
- [ ] Static file permissions fixed
- [ ] Services started and running
- [ ] Firewall configured
- [ ] SSL/HTTPS configured (if needed)
- [ ] Application accessible from browser
- [ ] Logs being generated properly

---

## Additional Resources

- [Gunicorn Documentation](https://docs.gunicorn.org/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)

---

*Last Updated: October 2025*