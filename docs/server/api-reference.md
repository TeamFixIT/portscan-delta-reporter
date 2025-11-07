---
layout: default
title: API Reference
parent: Server
nav_order: 3
---

# API Reference

Complete REST API documentation for the Port Scanner Delta Reporter server.

## Table of Contents
- [Authentication](#authentication)
- [Client Management](#client-management)
- [Scan Management](#scan-management)
- [Delta Reports](#delta-reports)
- [Scan Results](#scan-results)
- [SSE Streaming](#sse-streaming)

## Base URL

```
http://localhost:5000/api
```

## Authentication

### Login

Authenticate and obtain session cookie.

**Endpoint:** `POST /auth/login`

**Request Body:**
```json
{
  "username": "admin",
  "password": "your-password",
  "remember": false
}
```

**Response:**
```json
{
  "success": true,
  "redirect": "/dashboard"
}
```

### Register

Create a new user account.

**Endpoint:** `POST /auth/register`

**Request Body:**
```json
{
  "username": "newuser",
  "email": "user@example.com",
  "password": "SecurePass123",
  "confirm_password": "SecurePass123",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Response:**
```json
{
  "success": true,
  "redirect": "/dashboard"
}
```

### Logout

**Endpoint:** `GET /auth/logout`

**Response:** Redirects to login page

## Client Management

### Register Client Heartbeat

Client agents call this endpoint to register or update their status.

**Endpoint:** `POST /api/clients/<client_id>/heartbeat`

**Request Body:**
```json
{
  "client_id": "aa:bb:cc:dd:ee:ff",
  "hostname": "scanner-01",
  "ip_address": "192.168.1.100",
  "port": 8080,
  "scan_range": "192.168.1.0/24"
}
```

**Response (Approved Client):**
```json
{
  "status": "success",
  "message": "Client updated successfully",
  "approved": true
}
```

**Response (Unapproved Client):**
```json
{
  "status": "success",
  "message": "Client updated but awaiting approval",
  "approved": false
}
```
**Status Code:** 403 (Unapproved), 200 (Approved)

### Get Client Details

**Endpoint:** `GET /api/clients/<client_id>`

**Response:**
```json
{
  "status": "success",
  "client": {
    "id": 1,
    "client_id": "aa:bb:cc:dd:ee:ff",
    "hostname": "scanner-01",
    "ip_address": "192.168.1.100",
    "scan_range": "192.168.1.0/24",
    "status": "online",
    "is_approved": true,
    "last_seen": "2025-01-15T10:30:00Z",
    "created_at": "2025-01-10T08:00:00Z"
  },
  "recent_tasks": [...]
}
```

### Update Client

**Endpoint:** `PUT /api/clients/<client_id>`

**Request Body:**
```json
{
  "hostname": "scanner-01-updated",
  "status": "online"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Client updated successfully",
  "client": {...}
}
```

### Approve Client

**Endpoint:** `POST /api/clients/<client_id>/approve`

**Authentication:** Required (Admin)

**Response:**
```json
{
  "status": "success",
  "message": "Client approved successfully",
  "client": {...}
}
```

### Revoke Client Approval

**Endpoint:** `POST /api/clients/<client_id>/revoke`

**Authentication:** Required (Admin)

**Response:**
```json
{
  "status": "success",
  "message": "Client approval revoked successfully",
  "client": {...}
}
```

### Toggle Client Visibility

**Endpoint:** `POST /api/clients/<client_id>/toggle`

**Response:**
```json
{
  "status": "success",
  "message": "Client marked as offline"
}
```

## Scan Management

### List Scans

Get all scans for the current user.

**Endpoint:** `GET /api/scans`

**Authentication:** Required

**Query Parameters:**
- `is_active` (boolean): Filter by active status
- `is_scheduled` (boolean): Filter by scheduled status
- `limit` (integer): Number of results (default: 50)
- `offset` (integer): Pagination offset

**Response:**
```json
{
  "status": "success",
  "total": 10,
  "limit": 50,
  "offset": 0,
  "scans": [
    {
      "id": 1,
      "name": "Weekly Network Scan",
      "target": "192.168.1.0/24",
      "ports": "1-65535",
      "scan_arguments": "-T4 -sV",
      "interval_minutes": 10080,
      "is_active": true,
      "is_scheduled": true,
      "last_run": "2025-01-15T09:00:00Z",
      "next_run": "2025-01-22T09:00:00Z",
      "created_at": "2025-01-01T00:00:00Z",
      "result_count": 15,
      "success_rate": 93.33
    }
  ]
}
```

### Get Scan Details

**Endpoint:** `GET /api/scans/<scan_id>`

**Authentication:** Required

**Response:**
```json
{
  "status": "success",
  "scan": {
    "id": 1,
    "name": "Weekly Network Scan",
    "description": "Comprehensive network scan",
    "target": "192.168.1.0/24",
    "ports": "1-65535",
    "scan_arguments": "-T4 -sV",
    "interval_minutes": 10080,
    "is_active": true,
    "is_scheduled": true,
    "last_run": "2025-01-15T09:00:00Z",
    "next_run": "2025-01-22T09:00:00Z",
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-15T09:00:00Z",
    "recent_results": [...],
    "statistics": {
      "total_results": 15,
      "success_rate": 93.33,
      "last_success": "2025-01-15T09:00:00Z",
      "last_failure": null
    }
  }
}
```

### Create Scan

**Endpoint:** `POST /api/scans`

**Authentication:** Required

**Request Body:**
```json
{
  "name": "New Network Scan",
  "description": "Scan description",
  "target": "192.168.1.0/24",
  "ports": "1-65535",
  "scan_arguments": "-T4 -sV",
  "interval_minutes": 10080,
  "is_active": true,
  "is_scheduled": true
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Scan created successfully",
  "scan": {...}
}
```

### Update Scan

**Endpoint:** `PUT /api/scans/<scan_id>`

**Authentication:** Required

**Request Body:**
```json
{
  "name": "Updated Scan Name",
  "interval_minutes": 7200,
  "is_active": false
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Scan updated successfully",
  "scan": {...}
}
```

### Delete Scan

**Endpoint:** `DELETE /api/scans/<scan_id>`

**Authentication:** Required

**Response:**
```json
{
  "status": "success",
  "message": "Scan deactivated successfully"
}
```

### Execute Scan

Manually trigger a scan execution.

**Endpoint:** `GET /api/scans/<scan_id>/execute`

**Authentication:** Required

**Response:**
```json
{
  "status": "success",
  "message": "Scan delegated to 3 clients",
  "result_id": 42,
  "clients_triggered": 3,
  "unassigned_targets": []
}
```

### Toggle Scan Status

**Endpoint:** `POST /api/scans/<scan_id>/toggle`

**Authentication:** Required

**Response:**
```json
{
  "status": "success",
  "message": "Scan activated",
  "scan": {...}
}
```

## Delta Reports

### Get Scan Reports

Get all delta reports for a specific scan.

**Endpoint:** `GET /api/scan/<scan_id>/reports`

**Authentication:** Required

**Query Parameters:**
- `page` (integer): Page number (default: 1)
- `per_page` (integer): Items per page (default: 10, max: 100)
- `only_changes` (boolean): Only show reports with changes

**Response:**
```json
{
  "reports": [
    {
      "id": 1,
      "scan_id": 1,
      "baseline_result_id": 10,
      "current_result_id": 11,
      "report_type": "delta",
      "status": "generated",
      "created_at": "2025-01-15T09:30:00Z",
      "new_ports_count": 5,
      "closed_ports_count": 2,
      "changed_services_count": 1,
      "new_hosts_count": 0,
      "removed_hosts_count": 0,
      "has_changes": true
    }
  ],
  "total": 15,
  "pages": 2,
  "current_page": 1,
  "per_page": 10,
  "has_next": true,
  "has_prev": false
}
```

### Get Report Details

**Endpoint:** `GET /api/report/<report_id>`

**Authentication:** Required

**Query Parameters:**
- `include_data` (boolean): Include full delta_data (default: false)

**Response:**
```json
{
  "id": 1,
  "scan_id": 1,
  "baseline_result_id": 10,
  "current_result_id": 11,
  "report_type": "delta",
  "status": "generated",
  "created_at": "2025-01-15T09:30:00Z",
  "new_ports_count": 5,
  "closed_ports_count": 2,
  "changed_services_count": 1,
  "new_hosts_count": 0,
  "removed_hosts_count": 0,
  "has_changes": true,
  "delta_data": {
    "scanner": {...},
    "baseline": {...},
    "current": {...},
    "delta": {
      "new_up_hosts": [],
      "new_down_hosts": [],
      "added_ports": [...],
      "removed_ports": [...],
      "changed_ports": [...]
    }
  }
}
```

### Export Report as CSV

**Endpoint:** `GET /api/report/<report_id>/export/csv`

**Authentication:** Required

**Response:** CSV file download

### Delete Report

**Endpoint:** `DELETE /api/report/<report_id>`

**Authentication:** Required

**Response:**
```json
{
  "message": "Delta report deleted successfully"
}
```

### Get Scan Summary

Get summary of all changes for a scan over time.

**Endpoint:** `GET /api/scan/<scan_id>/summary`

**Authentication:** Required

**Query Parameters:**
- `days` (integer): Include last N days (default: 30)

**Response:**
```json
{
  "scan_id": 1,
  "days": 30,
  "period_start": "2024-12-15T00:00:00Z",
  "period_end": "2025-01-15T00:00:00Z",
  "total_reports": 30,
  "reports_with_changes": 12,
  "summary": {
    "total_new_ports": 45,
    "total_closed_ports": 20,
    "total_changed_services": 8,
    "total_new_hosts": 5,
    "total_removed_hosts": 2
  },
  "trend": {
    "most_active_hosts": [
      {"host": "192.168.1.50", "change_count": 10}
    ],
    "most_changed_ports": [
      {"port": 80, "change_count": 15}
    ]
  }
}
```

### Get User Reports

Get all delta reports across all scans for current user.

**Endpoint:** `GET /api/user/reports`

**Authentication:** Required

**Query Parameters:**
- `page` (integer): Page number
- `per_page` (integer): Items per page
- `only_changes` (boolean): Only show reports with changes

**Response:**
```json
{
  "reports": [...],
  "pagination": {
    "page": 1,
    "per_page": 10,
    "total_items": 50,
    "total_pages": 5,
    "has_next": true,
    "has_prev": false
  }
}
```

### Export All Reports

Export all delta reports for a scan as ZIP file.

**Endpoint:** `GET /api/scan/<scan_id>/export-all`

**Authentication:** Required

**Response:** ZIP file download containing CSV files for each report

## Scan Results

### Submit Scan Results

Client agents submit scan results to this endpoint.

**Endpoint:** `POST /api/clients/<client_id>/results`

**Request Body:**
```json
{
  "result_id": 42,
  "task_id": "abc-123-def",
  "status": "completed",
  "parsed_results": {
    "192.168.1.100": {
      "hostname": "server-01",
      "state": "up",
      "open_ports": [22, 80, 443],
      "port_details": {
        "22": {
          "protocol": "tcp",
          "name": "ssh",
          "product": "OpenSSH",
          "version": "8.2"
        },
        "80": {
          "protocol": "tcp",
          "name": "http",
          "product": "nginx",
          "version": "1.18"
        }
      }
    }
  },
  "summary_stats": {
    "total_targets": 254,
    "completed_targets": 254,
    "error_targets": 0,
    "total_open_ports": 156
  }
}
```

**Response:**
```json
{
  "message": "Scan results received successfully",
  "result_id": 42,
  "summary": {
    "total_targets": 254,
    "completed_targets": 254,
    "failed_targets": 0,
    "total_open_ports": 156,
    "contributing_clients": 3
  }
}
```

## System Monitoring

### Health Check

**Endpoint:** `GET /api/health`

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T10:30:00Z",
  "version": "1.0.0",
  "stats": {
    "active_clients": 5,
    "pending_tasks": 3,
    "running_tasks": 2
  }
}
```

### Get Statistics

**Endpoint:** `GET /api/stats`

**Query Parameters:**
- `hours` (integer): Time range in hours (default: 24)

**Response:**
```json
{
  "status": "success",
  "period_hours": 24,
  "since": "2025-01-14T10:00:00Z",
  "stats": {
    "clients": {
      "total": 10,
      "online": 5,
      "scanning": 2,
      "offline": 3
    },
    "tasks": {
      "total": 150,
      "pending": 5,
      "running": 3,
      "completed": 140,
      "failed": 2
    },
    "scans": {
      "total": 25,
      "completed": 23,
      "failed": 2
    }
  }
}
```

## SSE Streaming

### Event Stream

Subscribe to real-time server-sent events.

**Endpoint:** `GET /api/stream`

**Authentication:** Optional (user-specific events require login)

**Response:** Server-Sent Events stream

**Event Types:**

```javascript
// Alert notification
data: {"message": "New scan completed", "type": "success"}

// Redirect event
data: {"type": "redirect", "url": "/auth/login", "endpoint": "auth.login"}
```

**Client Example:**
```javascript
const eventSource = new EventSource('/api/stream');

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'redirect') {
    window.location.href = data.url;
  } else if (data.message) {
    showNotification(data.message, data.type);
  }
};
```

### Broadcast Message

**Endpoint:** `POST /api/broadcast`

**Request Body:**
```json
{
  "message": "System update complete",
  "type": "success"
}
```

**Response:**
```json
{
  "status": "Message broadcasted"
}
```

## Error Responses

All endpoints may return these error responses:

### 400 Bad Request
```json
{
  "error": "Missing required fields",
  "missing_fields": ["target", "ports"]
}
```

### 401 Unauthorized
```json
{
  "error": "Authentication required"
}
```

### 403 Forbidden
```json
{
  "error": "Unauthorized"
}
```

### 404 Not Found
```json
{
  "error": "Scan not found"
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal server error",
  "details": "Database connection failed"
}
```

## Rate Limiting

API endpoints are rate-limited (if enabled in configuration):
- Default: 100 requests per hour per IP
- Authenticated users: 1000 requests per hour

**Headers:**
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Time when limit resets (Unix timestamp)

## Pagination

List endpoints support pagination:

**Query Parameters:**
- `page`: Page number (1-indexed)
- `per_page`: Items per page
- `limit`: Alias for per_page
- `offset`: Skip N items

**Response includes:**
```json
{
  "total": 100,
  "page": 1,
  "per_page": 25,
  "has_next": true,
  "has_prev": false
}
```

## Next Steps

- [Usage Guide](usage.md) - Learn how to use the API
- [Configuration](configuration.md) - API configuration options