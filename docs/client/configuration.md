---
layout: default
title: Client Configuration
---

# Client Configuration

The client agent is configured via `config.yml`.

## Configuration File

Create `config.yml` in the client directory:

```yaml
# Server connection
server_url: http://localhost:5000

# Client settings
client_port: 8080
client_host: 0.0.0.0

# Scanning configuration
max_concurrent_scans: 2
scan_range: "192.168.1.0/24"  # Optional: restrict scanning to this range

# Connection settings
heartbeat_interval: 60        # Seconds between heartbeats
check_approval_interval: 30   # Check approval status frequency

# Retry settings
retry_attempts: 3
retry_delay: 5                # Seconds between retries
```

## Configuration Options

### server_url
- **Type**: String (URL)
- **Required**: Yes
- **Default**: `http://localhost:5000`
- **Description**: URL of the central server

### client_port
- **Type**: Integer
- **Required**: No
- **Default**: `8080`
- **Description**: Port for client HTTP server

### max_concurrent_scans
- **Type**: Integer
- **Required**: No
- **Default**: `2`
- **Description**: Maximum number of parallel scans

### scan_range
- **Type**: String (CIDR notation)
- **Required**: No
- **Default**: `null` (no restriction)
- **Description**: Restrict scanning to specific IP range
- **Example**: `10.0.0.0/8`, `192.168.1.0/24`

### heartbeat_interval
- **Type**: Integer (seconds)
- **Required**: No
- **Default**: `60`
- **Description**: Frequency of status updates to server

## Environment Variables

You can override configuration with environment variables:

```bash
export PORTSCANNER_SERVER_URL=http://server:5000
export PORTSCANNER_CLIENT_PORT=9090
export PORTSCANNER_MAX_SCANS=4
```

## Security Considerations

1. **Firewall Rules**: Ensure client can reach server
2. **Port Access**: Client port must be accessible from server
3. **Scan Range**: Use `scan_range` to prevent unauthorized scanning
4. **Approval**: Always use the approval system in production

## Example Configurations

### Development Setup
```yaml
server_url: http://localhost:5000
client_port: 8080
max_concurrent_scans: 1
heartbeat_interval: 30
```

### Production Setup
```yaml
server_url: https://scanner-server.company.com
client_port: 8443
client_host: 0.0.0.0
max_concurrent_scans: 4
scan_range: "10.0.0.0/8"
heartbeat_interval: 60
check_approval_interval: 30
retry_attempts: 5
retry_delay: 10
```

### High-Volume Scanner
```yaml
server_url: http://scanner-server:5000
client_port: 8080
max_concurrent_scans: 8
heartbeat_interval: 120
retry_attempts: 3
```