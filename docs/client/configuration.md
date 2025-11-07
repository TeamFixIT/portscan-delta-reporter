---
layout: default
title: Configuration
parent: Client
nav_order: 2
---

# Client Configuration

The client agent is configured via `config.yml`.

---

### Interactive Configuration Wizard (Recommended)

The easiest way to configure the client:

```bash
portscanner-client-config
```

The wizard will guide you through:
1. Server connection details
2. Client identification
3. Scan settings
4. Network options
5. Connection parameters

### Manual Configuration

If you prefer to configure manually:

```bash
# Copy example configuration
cp config.example.yml config.yml

# Edit with your preferred editor
nano config.yml
```

Example `config.yml`:

```yaml
# Server Connection
server_url: "http://localhost:5000"
client_port: 8080
client_host: "0.0.0.0"

# Client Identification (optional - auto-detected if not set)
client_id: "CUSTOM_ID"          # Default: MAC address
hostname: "scanner-01"           # Default: system hostname

# Scanning Configuration
chunk_size: 1                    # Targets processed per chunk
per_target_timeout: 120          # Timeout per target (seconds)
progress_report_interval: 10     # Progress update frequency (seconds)

# Connection Settings
heartbeat_interval: 60           # Heartbeat frequency (seconds)
check_approval_interval: 30      # Check approval status (seconds)
retry_attempts: 3                # Connection retry attempts
retry_delay: 5                   # Delay between retries (seconds)

# Optional: Restrict Scanning Range
scan_range: "192.168.1.0/24"    # CIDR notation, null = no restriction
```

### Configuration Options Explained

#### Server Connection

| Option | Description | Default |
|--------|-------------|---------|
| `server_url` | URL of the central server | `http://localhost:5000` |
| `client_port` | Port for client HTTP server | `8080` |
| `client_host` | Bind address for client server | `0.0.0.0` |

#### Client Identification

| Option | Description | Default |
|--------|-------------|---------|
| `client_id` | Unique client identifier | MAC address |
| `hostname` | Display name for client | System hostname |

#### Scanning Configuration

| Option | Description | Default |
|--------|-------------|---------|
| `chunk_size` | Targets per scanning chunk | `1` |
| `per_target_timeout` | Timeout for each target | `120` seconds |
| `progress_report_interval` | How often to report progress | `10` seconds |

#### Connection Settings

| Option | Description | Default |
|--------|-------------|---------|
| `heartbeat_interval` | Frequency of heartbeat messages | `60` seconds |
| `check_approval_interval` | Check approval status frequency | `30` seconds |
| `retry_attempts` | Connection retry attempts | `3` |
| `retry_delay` | Delay between retries | `5` seconds |

#### Security Options

| Option | Description | Default |
|--------|-------------|---------|
| `scan_range` | Restrict scanning to IP range (CIDR) | `null` (unrestricted) |

### Reconfigure Anytime

You can re-run the configuration wizard at any time:

```bash
portscanner-client-config
```
