---
layout: default
title: Client Documentation
---

# Client Agent Documentation

The Port Scanner Client Agent is a distributed scanning component that performs network scans on behalf of the central server.

## Table of Contents

- [Installation](installation.md)
- [Configuration](configuration.md)
- [Usage](usage.md)
- [Troubleshooting](troubleshooting.md)

## Overview

The client agent:
- Runs as a service on scanning machines
- Receives scan tasks via HTTP push
- Executes Nmap scans with various options
- Reports results back to the server
- Requires approval before performing scans

## Key Features

- **Push-Based Architecture**: Server pushes scan tasks to client
- **Approval System**: Clients must be approved before scanning
- **Concurrent Scans**: Configurable parallel scan execution
- **System Monitoring**: Reports CPU, memory, and network metrics
- **Automatic Retries**: Resilient result delivery

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Create configuration
cp config.example.yml config.yml
# Edit config.yml with your settings

# Run client (requires root for SYN scans)
sudo python client_agent.py
```

## Architecture

```
┌─────────────────────────────────────┐
│         Client Agent                │
│                                     │
│  ┌──────────────────────────────┐  │
│  │   Flask HTTP Server          │  │
│  │   - /health                  │  │
│  │   - /scan (receive tasks)    │  │
│  │   - /approve                 │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │   Scan Executor              │  │
│  │   - ThreadPoolExecutor       │  │
│  │   - Nmap Integration         │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │   Heartbeat Service          │  │
│  │   - Registration             │  │
│  │   - Status Updates           │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
```

## Endpoints

### Health Check
```
GET /health
```
Returns client status and system information.

### Receive Scan Task
```
POST /scan
```
Receives scan task from server and executes it.

### Approve Client
```
POST /approve
```
Marks client as approved (called by server).

## Next Steps

- [Installation Guide](installation.md) - Detailed installation instructions
- [Configuration](configuration.md) - Configuration options
- [Usage Examples](usage.md) - Common usage patterns