---
layout: default
title: Usage Guide
parent: Server
nav_order: 4
---

# Server Usage Guide

Learn how to use the Port Scanner Delta Reporter server application.

## Table of Contents
- [Getting Started](#getting-started)
- [User Management](#user-management)
- [Scan Management](#scan-management)
- [Client Management](#client-management)
- [Delta Reports](#delta-reports)
- [Alerts](#alerts)
- [Advanced Features](#advanced-features)

## Getting Started

### First Login

1. Navigate to your server URL:
   ```
   http://localhost:5000
   ```

2. Sign in with your admin credentials (created during installation)

3. You'll see the dashboard with four main sections:
   - **Active Clients** - Connected scanning agents
   - **Recent Scans** - Scans performed in the last 24 hours
   - **Delta Reports** - Change reports between scans
   - **Alerts** - Critical security notifications

### Dashboard Overview

The dashboard provides a real-time overview of your network monitoring:

```
┌─────────────────────────────────────────────────┐
│  Port Scanner Delta Reporter - Dashboard       │
├─────────────────────────────────────────────────┤
│  Active Clients: 5    Recent Scans: 12         │
│  Delta Reports: 8     Alerts: 2                 │
└─────────────────────────────────────────────────┘
```

## User Management

### Profile Management

1. Click your username in the sidebar → **Profile**
2. Update your information:
   - First Name
   - Last Name
   - Email address

**Note:** OAuth users cannot change their email address.

### Change Password

**Local Users Only:**

1. Navigate to **Profile** → **Password** tab
2. Enter current password
3. Enter new password (must meet requirements)
4. Confirm new password
5. Click **Change Password**

### Creating Additional Users

**Administrators Only:**

Users can self-register, or administrators can invite them:

1. Share the registration URL: `http://your-server:5000/auth/register`
2. New users complete registration
3. Verify their account (if email verification is enabled)

## Scan Management

### Creating a New Scan

1. Navigate to **Scans** → **New Scan**
2. Fill in scan details:

```yaml
Name: Weekly Network Scan
Description: Comprehensive network scan
Target: 192.168.1.0/24
Ports: 1-65535
Scan Arguments: -T4 -sV --host-timeout 30s
Interval: 10080 minutes (weekly)
Active: ✓
Scheduled: ✓
```

3. Click **Create Scan**

### Target Formats

The server accepts multiple target formats:

```bash
# Single IP
192.168.1.100

# IP Range (CIDR notation)
192.168.1.0/24

# Multiple IPs (comma-separated)
192.168.1.10,192.168.1.20,192.168.1.30

# IP Range (dash notation)
192.168.1.1-192.168.1.50
```

### Port Specifications

```bash
# All ports
1-65535

# Common ports
22,80,443,3306,5432

# Port range
1-1000

# Mixed
22,80,443,1000-2000
```

### Scan Arguments

Common nmap arguments:

```bash
# Service version detection
-sV

# OS detection
-O

# Aggressive scan
-A

# Timing template (0-5, 5=fastest)
-T4

# Timeout per host
--host-timeout 30s

# Skip host discovery
-Pn

# UDP scan
-sU

# TCP SYN scan (default)
-sS
```

**Example combinations:**
```bash
# Fast service detection
-T4 -sV --host-timeout 30s --max-retries 1

# Comprehensive scan
-A -T4 -sV --script=default

# Quick discovery
-T5 -F --max-retries 1
```

### Viewing Scan Details

1. Navigate to **Scans**
2. Click on a scan name
3. View scan information:
   - Configuration
   - Execution history
   - Results
   - Associated tasks

### Editing a Scan

1. Navigate to **Scans**
2. Click the **Edit** button (pencil icon)
3. Modify scan parameters
4. Click **Save Changes**

**Note:** Changes to scheduled scans take effect on the next run.

### Executing a Scan Manually

1. Navigate to **Scans**
2. Click the **Execute** button (play icon)
3. Scan will be queued immediately
4. View progress in **Scan Details**

### Deleting a Scan

1. Navigate to **Scans**
2. Click the **Delete** button (trash icon)
3. Confirm deletion

**Note:** This deactivates the scan rather than deleting it permanently.

## Client Management

### Understanding Client Status

Clients can have three statuses:

- **🟢 Online** - Client is active and ready to scan
- **🟡 Scanning** - Client is currently performing a scan
- **🔴 Offline** - Client hasn't sent heartbeat recently

### Approving New Clients

When a new client connects:

1. Navigate to **Clients**
2. Find the pending client (marked "No" under Approved)
3. Click **Approve** button
4. Client will receive approval notification

### Client Information

Each client displays:
```
MAC Address:    aa:bb:cc:dd:ee:ff
Hostname:       scanner-01
IP Address:     192.168.1.100
Scan Range:     192.168.1.0/24
Status:         Online
Last Seen:      2 minutes ago
Approved:       Yes
```

### Managing Client Visibility

Hide clients you don't want to see:

1. Navigate to **Clients**
2. Click the **Hide** button (eye icon)
3. Toggle **Show Hidden** filter to view hidden clients

### Revoking Client Access

1. Navigate to **Clients**
2. Click the **Revoke** button
3. Confirm revocation
4. Client will be marked offline and cannot scan

## Delta Reports

### Understanding Delta Reports

Delta reports show changes between consecutive scans:

- **New Hosts** - Devices that appeared
- **Removed Hosts** - Devices that disappeared
- **New Ports** - Ports that opened
- **Closed Ports** - Ports that closed
- **Service Changes** - Services that changed versions or configurations

### Viewing Reports

#### Overview (All Networks)

1. Navigate to **Reports**
2. See network cards with:
   - Security score
   - Change indicators
   - Status badges

```
┌────────────────────────────┐
│ Office Network             │
│ 192.168.1.0/24             │
├────────────────────────────┤
│    Security Score: 85      │
│         Good               │
├────────────────────────────┤
│  +2 New Ports              │
│  -1 Closed Ports           │
│  1 Service Changes         │
└────────────────────────────┘
```

#### Detailed Report

1. Click **View Latest Report** on a network card
2. See detailed changes:

```yaml
New Hosts:
  - 192.168.1.150
  
New Open Ports:
  - Host: 192.168.1.100
    Port: 3389 (RDP)
    Service: Microsoft Terminal Services
    
Closed Ports:
  - Host: 192.168.1.50
    Port: 22 (SSH)
    
Service Changes:
  - Host: 192.168.1.10
    Port: 80
    Before: nginx 1.18
    After: nginx 1.20
```

### Filtering Reports

Use the filter controls to narrow down reports:

```yaml
Status Filter:
  - All Statuses
  - Critical Only (new critical ports)
  - Changes Only (any changes)
  - Stable Only (no changes)

Score Filter:
  - All Scores
  - Excellent (90+)
  - Good (70-89)
  - Monitor (50-69)
  - Critical (0-49)

Sort:
  - Most Recent
  - Oldest
  - Score (High to Low)
  - Score (Low to High)
  - Network Name

Search:
  - Filter by network name
```

### Exporting Reports

#### Single Report

1. Open a delta report
2. Click **Export** dropdown
3. Choose format:
   - **CSV** - Spreadsheet format
   - **JSON** - Machine-readable format

#### All Reports

1. Navigate to **Reports**
2. Click **Export All** on a network card
3. Download ZIP file containing all reports

### Scan History Timeline

View all changes over time:

1. Navigate to **Reports**
2. Click **History** on a network card
3. See timeline of all scans:

```
Timeline View:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
● 2025-01-15 09:00
  ↳ Critical: +1 RDP port opened
  
● 2025-01-08 09:00
  ↳ Changes: Service updates detected
  
● 2025-01-01 09:00
  ↳ Stable: No changes
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Alerts

### Understanding Alert Criticality

Alerts are categorized by severity:

- **🔴 Critical** - Immediate action required
- **🟠 High** - Important but not urgent
- **🟡 Medium** - Monitor but not urgent
- **🔵 Low** - Informational

### Critical Ports

The system monitors these ports automatically:

```yaml
Critical Ports:
  3389: RDP (Critical)
  22: SSH (High)
  23: Telnet (High)
  445: SMB (High)
  5900: VNC (High)
  
Medium Risk:
  21: FTP
  3306: MySQL
  5432: PostgreSQL
```

### Managing Alerts

#### Mark as Actioned

1. Navigate to **Alerts**
2. Click **Mark Actioned** on an alert
3. Alert status changes to "Actioned"

#### Ignore Alert

1. Navigate to **Alerts**
2. Click **Ignore** on an alert
3. Alert will be hidden from active view

#### Auto-Resolution

Alerts automatically resolve when:
- Port closes
- Service returns to expected state
- Device goes offline

## Advanced Features

### Scheduled Scans

Scans can run automatically:

1. Create scan with **Scheduled** enabled
2. Set interval in minutes:
   - Daily: 1440
   - Weekly: 10080
   - Monthly: 43200

3. View next run time in scan details
4. Toggle scheduling without deleting scan

### Scan Task Distribution

The server automatically distributes scan targets to clients:

```
Target: 192.168.0.0/16 (65,536 IPs)

Client Distribution:
  Client 1: 192.168.0.0/24   → 256 IPs
  Client 2: 192.168.1.0/24   → 256 IPs
  Client 3: 192.168.2.0/24   → 256 IPs
  ...
```

Clients only scan IPs within their configured range.

### Partial Scans

If not all targets can be assigned:
- Scan marked as "partial"
- Warning indicator shown
- Report notes incomplete coverage

### Server-Sent Events (SSE)

Real-time notifications in the UI:

- New scan completion
- Client status changes
- Alert notifications
- System messages

### Viewing Logs

**Administrators Only:**

1. Navigate to **Settings** → **Logs**
2. View three log types:
   - **app.log** - General application logs
   - **error.log** - Error messages only
   - **scheduler.log** - Scheduled task logs

3. Download logs for analysis

### Flask CLI Commands

Useful management commands:

```bash
# List all scheduled jobs
flask list-jobs

# Reload schedules from database
flask reload-schedules

# Create admin user
flask create-admin

# Initialize database
flask init-db

# Reset database (WARNING: destroys data)
flask reset-db

# Run complete setup
flask setup
```

## Best Practices

### Scan Configuration

1. **Start Small**
   - Begin with small subnets
   - Test with short intervals
   - Expand gradually

2. **Optimize Performance**
   - Use appropriate timing templates (-T3 or -T4)
   - Set reasonable timeouts
   - Limit port ranges when possible

3. **Schedule Wisely**
   - Run during off-peak hours
   - Avoid overlapping scans
   - Consider network impact

### Security

1. **Review Alerts Promptly**
   - Check critical alerts daily
   - Investigate new open ports
   - Monitor service changes

2. **Client Management**
   - Approve clients carefully
   - Revoke unused clients
   - Monitor client activity

3. **Report Analysis**
   - Review reports weekly
   - Track trends over time
   - Export reports for records

### Performance

1. **Database Maintenance**
   - Archive old reports periodically
   - Monitor database size
   - Run VACUUM on SQLite

2. **Log Management**
   - Rotate logs regularly
   - Archive old logs
   - Monitor disk space

## Troubleshooting

### Scan Not Running

1. Check scan is **Active** and **Scheduled**
2. Verify clients are **Online** and **Approved**
3. Check client scan ranges match targets
4. Review scheduler logs

### No Results Received

1. Verify client connectivity
2. Check firewall rules
3. Review client logs
4. Test client manually

### Delta Report Not Generated

Delta reports require:
- At least two completed scans
- Same scan target
- Successfully completed results

### Performance Issues

1. Reduce concurrent scans
2. Optimize scan arguments
3. Increase server resources
4. Use PostgreSQL instead of SQLite

## Getting Help

- **Documentation**: [https://teamfixit.github.io/portscan-delta-reporter](https://teamfixit.github.io/portscan-delta-reporter)
- **GitHub Issues**: [TeamFixIT/portscan-delta-reporter](https://github.com/TeamFixIT/portscan-delta-reporter/issues)
- **Client Guide**: [Client Agent Documentation](../client/index.md)

## Next Steps

- [API Reference](api-reference.md) - Integrate with external systems