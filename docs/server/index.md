---
layout: default
title: Server
nav_order: 3
has_children: true
---

# Server Documentation

The Port Scanner Delta Reporter server is the central coordination hub for distributed network scanning. It manages scan configurations, delegates tasks to client agents, aggregates results, and generates delta reports showing network changes over time.

## Quick Start

```bash
# Clone and navigate to server directory
cd server

# Install and setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
flask setup

# Create admin user
flask create-admin

# Run server
flask run --host=0.0.0.0 --port=5000
```

Access the web interface at `http://localhost:5000`

## Overview

The server application provides:

- **Web Dashboard** - Intuitive interface for scan management and monitoring
- **REST API** - Programmatic access for automation and integration
- **Task Scheduler** - Automatic execution of recurring scans
- **Delta Reporting** - Change detection between consecutive scans
- **Alert System** - Notifications for critical security events
- **Multi-Client Coordination** - Distributed scanning across multiple agents
- **User Management** - Role-based access control with OAuth/SSO support

## Architecture

```
┌─────────────────────────────────────────────────┐
│           Web Interface / Dashboard             │
├─────────────────────────────────────────────────┤
│               Flask Application                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │   Auth   │  │  Scans   │  │    Delta     │   │
│  │  System  │  │  Manager │  │   Reports    │   │
│  └──────────┘  └──────────┘  └──────────────┘   │
├─────────────────────────────────────────────────┤
│              Task Scheduler                     │
│          (APScheduler Background)               │
├─────────────────────────────────────────────────┤
│          Database (SQLite/PostgreSQL)           │
└─────────────────────────────────────────────────┘
         ↕                    ↕
    [Client 1]           [Client 2]
```

## Key Features

### Scan Management
- Create and configure network scans
- Support for IP ranges, CIDR notation, and multiple targets
- Flexible port specifications and nmap arguments
- Manual or scheduled execution

### Delta Reporting
- Automatic change detection between scans
- Detailed comparison of network state
- Track new/removed hosts and ports
- Service version change monitoring
- Export to CSV/JSON formats

### Alert System
- Critical port monitoring (RDP, SSH, Telnet, etc.)
- Configurable severity levels
- Automatic alert resolution
- Real-time notifications via SSE

### Client Coordination
- Automatic task distribution to agents
- Client approval workflow
- Health monitoring via heartbeats
- Load balancing based on scan ranges

### Security
- User authentication (local and OAuth/SSO)
- Role-based access control
- Session management
- Password policies

### Monitoring
- Real-time dashboard
- System health metrics
- Comprehensive logging
- Performance statistics

## Documentation

### [Installation](installation.md)
Complete installation guide covering:
- System requirements
- Installation methods
- Environment setup
- Running as a service
- Docker deployment

### [Configuration](configuration.md)
Detailed configuration options:
- Environment variables
- Database setup
- Authentication (OAuth/SSO)
- Email notifications
- Scheduler settings
- Security hardening

### [API Reference](api-reference.md)
Complete REST API documentation:
- Authentication endpoints
- Scan management
- Delta reports
- Client coordination
- SSE streaming
- Error handling

### [Usage Guide](usage.md)
Step-by-step usage instructions:
- Dashboard walkthrough
- Creating and managing scans
- Client approval
- Viewing delta reports
- Alert management
- Advanced features

## System Requirements

### Minimum
- **Python**: 3.8+
- **RAM**: 2GB
- **Storage**: 1GB
- **OS**: Linux, macOS, or Windows

### Recommended
- **Python**: 3.10+
- **RAM**: 4GB+
- **Storage**: 5GB+
- **Database**: PostgreSQL (for production)
- **OS**: Linux (Ubuntu 20.04+ or RHEL 8+)

## Technology Stack

- **Framework**: Flask 3.x
- **Database**: SQLAlchemy (SQLite/PostgreSQL/MySQL)
- **Scheduler**: APScheduler
- **Authentication**: Flask-Login + OAuth (Authlib)
- **Frontend**: Bootstrap 5, Vanilla JavaScript
- **Real-time**: Server-Sent Events (SSE)

## Common Tasks

### Creating Your First Scan

```bash
# Via web interface
1. Navigate to Scans → New Scan
2. Configure target: 192.168.1.0/24
3. Set ports: 1-65535
4. Enable scheduling
5. Click Create

# Or via API
curl -X POST http://localhost:5000/api/scans \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Network Scan",
    "target": "192.168.1.0/24",
    "ports": "1-65535",
    "interval_minutes": 10080,
    "is_scheduled": true
  }'
```

### Viewing Delta Reports

```bash
# Web interface
1. Navigate to Reports
2. Select a network
3. Click "View Latest Report"
4. Export as CSV/JSON if needed

# API
curl http://localhost:5000/api/scan/1/reports
```

### Managing Clients

```bash
# Approve new client
curl -X POST http://localhost:5000/api/clients/<client_id>/approve

# View client status
curl http://localhost:5000/api/clients/<client_id>
```

## Default Ports

- **Web Interface**: 5000
- **API**: 5000
- **Client Communication**: Configurable per client (default: 8080)

## Security Considerations

1. **Change default credentials** immediately after installation
2. **Generate secure SECRET_KEY** for production
3. **Enable HTTPS** with valid SSL certificate
4. **Configure firewall** rules appropriately
5. **Regular backups** of database
6. **Keep dependencies updated**
7. **Review logs** regularly for suspicious activity

## Troubleshooting

### Server Won't Start
```bash
# Check if port is in use
lsof -i :5000

# Check logs
tail -f logs/app.log

# Verify database connection
flask shell
>>> from app import db
>>> db.engine.connect()
```

### Scans Not Running
```bash
# Verify scheduler is running
flask list-jobs

# Check client status
# Navigate to Clients page in web interface

# Review scheduler logs
tail -f logs/scheduler.log
```

### Performance Issues
- Switch from SQLite to PostgreSQL
- Increase worker processes
- Optimize scan arguments
- Reduce concurrent scans

## Getting Help

- **Documentation**: [https://teamfixit.github.io/portscan-delta-reporter](https://teamfixit.github.io/portscan-delta-reporter)
- **GitHub Issues**: [Report bugs or request features](https://github.com/TeamFixIT/portscan-delta-reporter/issues)
- **Client Agent Docs**: [Client documentation](../client/index.md)

## Contributing

Contributions are welcome! Please refer to the main project [contributing guidelines](../CONTRIBUTING.md).

## License

This project is part of the Port Scanner Delta Reporter suite. See the main [LICENSE](../LICENSE) file for details.

---

**Next Steps:**
- Follow the [Installation Guide](installation.md) to set up your server
- Configure your [environment settings](configuration.md)
- Set up [client agents](../client/index.md) to begin scanning