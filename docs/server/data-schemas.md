---
layout: default
title: Data Schemas
nav_order: 6
parent: Server
---

# Data Schemas

This document summarizes the key JSON payloads for scan results and delta reports.

## Scan Result Payload (client → server)

```json
{
  "scan_id": "123",
  "task_id": "task-uuid",
  "result_id": "456",
  "client_id": "scanner-01",
  "status": "completed",
  "scan_duration": 42.1,
  "parsed_results": {
    "192.168.1.10": {
      "hostname": "host-a",
      "state": "up",
      "open_ports": [22, 80],
      "port_details": {
        "22": { "protocol": "tcp", "name": "ssh", "product": "OpenSSH" },
        "80": { "protocol": "tcp", "name": "http", "product": "nginx" }
      }
    }
  },
  "summary_stats": {
    "total_targets": 1,
    "scanned_targets": 1,
    "targets_up": 1,
    "targets_down": 0,
    "error_targets": 0,
    "total_open_ports": 2
  },
  "timestamp": "2026-02-04T00:00:00Z",
  "raw_results": {
    "192.168.1.10": {
      "nmap": { "command_line": "...", "scaninfo": {}, "scanstats": {} },
      "scan": { "status": { "state": "up" } }
    }
  }
}
```

Notes:
- `raw_results` is optional and only stored when `STORE_RAW_RESULTS=true` on the server and `send_raw_results=true` on the client.
- `parsed_results` drives delta report generation.

## Delta Report Schema (server output)

```json
{
  "scanner": {
    "name": "nmap",
    "version": "unknown",
    "comparison_time": "2026-02-04T00:05:00Z"
  },
  "report": {
    "scan_id": 1,
    "baseline_result_id": 10,
    "current_result_id": 11,
    "generated_at": "2026-02-04T00:05:00Z"
  },
  "scan": {
    "scan_id": 1,
    "name": "Weekly Scan",
    "target": "192.168.1.0/24",
    "ports": "1-65535",
    "scan_arguments": "-sS -sV"
  },
  "scan_window": {
    "baseline_started_at": "2026-02-04T00:00:00Z",
    "baseline_completed_at": "2026-02-04T00:02:00Z",
    "current_started_at": "2026-02-11T00:00:00Z",
    "current_completed_at": "2026-02-11T00:02:00Z"
  },
  "baseline": {
    "result_id": 10,
    "completed_at": "2026-02-04T00:02:00Z",
    "total_hosts": 10,
    "total_open_ports": 20
  },
  "current": {
    "result_id": 11,
    "completed_at": "2026-02-11T00:02:00Z",
    "total_hosts": 11,
    "total_open_ports": 23
  },
  "delta": {
    "new_up_hosts": ["192.168.1.20"],
    "new_down_hosts": ["192.168.1.5"],
    "added_ports": [
      {
        "host": "192.168.1.20",
        "port": 443,
        "protocol": "tcp",
        "service": "https",
        "product": "nginx",
        "version": "1.26"
      }
    ],
    "removed_ports": [],
    "changed_ports": []
  },
  "summary": {
    "new_hosts_count": 1,
    "removed_hosts_count": 1,
    "new_ports_count": 1,
    "closed_ports_count": 0,
    "changed_services_count": 0
  }
}
```
