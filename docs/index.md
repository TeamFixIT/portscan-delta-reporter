---
layout: default
title: Home
---

# Port Scanner Delta Reporter

A distributed network scanning system with push-based client architecture and centralized reporting.

## Features

- **Distributed Scanning**: Deploy multiple client agents across different network segments
- **Push-Based Architecture**: Clients receive scan tasks and push results back
- **Client Approval System**: Secure approval workflow for client registration
- **Real-time Monitoring**: Track scan progress and client health
- **Comprehensive Results**: Detailed port information, service detection, and OS fingerprinting

## Components

### Server
The central management server that:
- Manages scan requests and scheduling
- Approves and monitors client agents
- Aggregates and stores scan results
- Provides web UI and API

[Learn more →](server/)

### Client Agent
Distributed scanning agents that:
- Perform network scans using Nmap
- Report system health and status
- Execute scans on demand
- Support concurrent scanning

[Learn more →](client/)

## Requirements

### Server
- Python 3.8+
- Flask, SQLAlchemy, Celery
- Redis (for task queue)
- PostgreSQL (recommended) or SQLite

### Client
- Python 3.8+
- Nmap installed
- Root/Administrator privileges (for SYN scans)
- Network access to target ranges

## Installation

Quick installation for testing:

```bash
# Clone repository
git clone https://github.com/TeamFixIT/portscanner-delta-reporter.git
cd portscanner-delta-reporter

# Install server
cd server
pip install -r requirements.txt
python server.py

# Install client (on scanning machine)
cd ../client
pip install -r requirements.txt
python client_agent.py
```

For detailed installation instructions, see [Getting Started](getting-started.md).

## Support

- **Issues**: [GitHub Issues](https://github.com/TeamFixIT/portscanner-delta-reporter/issues)
- **Documentation**: [Full Documentation](https://teamfixit.github.io/portscan-delta-reporter/)

## License

[Your License Here]