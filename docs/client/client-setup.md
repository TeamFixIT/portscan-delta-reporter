# Port Scanner Client Agent

Lightweight client agent for the Port Scanner Delta Reporter system. Connects to the central server and executes port scans on behalf of the server.

## Quick Start

### Automated Setup

```bash
pip install .

portscanner-client-config

portscanner-client
```

### Manual Setup

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install package
pip install -e .

# 3. Configure (interactive wizard)
portscanner-client-config

# 4. Start the client
portscanner-client
```

## Installation

### Prerequisites

- Python 3.9 or higher
- `nmap` installed on the system
  ```bash
  # Ubuntu/Debian
  sudo apt-get install nmap
  
  # macOS
  brew install nmap
  
  ```

### Install from source

```bash
pip install -e .
```

### Install with dev dependencies

```bash
pip install -e ".[dev]"
```

## Configuration

### Option 1: Interactive Wizard (Recommended)

```bash
portscanner-client-config
```

This will guide you through all configuration options.

### Option 2: Manual Configuration

Copy the example config and edit:

```bash
cp config.example.yml config.yml
nano config.yml
```

### Configuration Options

```yaml
# Server connection
server_url: "http://localhost:5000"
client_port: 8080
client_host: "0.0.0.0"

# Optional: Override auto-detection
client_id: "CUSTOM_ID"          # Default: MAC address
hostname: "scanner-01"           # Default: system hostname

# Scan settings
chunk_size: 1                    # Targets per chunk
per_target_timeout: 120          # Seconds per target
progress_report_interval: 10     # Progress update frequency

# Connection settings
heartbeat_interval: 60           # Heartbeat frequency
check_approval_interval: 30      # Approval check frequency
retry_attempts: 3                # Connection retry attempts
retry_delay: 5                   # Seconds between retries

# Optional: Restrict scanning to specific range
scan_range: "192.168.1.0/24"
```

## Usage

### Start the Client

```bash
# Using the command
portscanner-client

# Or using the script
./start_client.sh
```

### Reconfigure

```bash
portscanner-client-config
```

### Check Configuration

```bash
cat config.yml
```

## Available Commands

After installation, these commands are available:

- `portscanner-client` - Start the client agent
- `portscanner-client-config` - Run configuration wizard

## Running as a Service

### systemd (Linux)

Create `/etc/systemd/system/portscanner-client.service`:

```ini
[Unit]
Description=Port Scanner Client Agent
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/portscanner-client
Environment="PATH=/home/pi/portscanner-client/venv/bin"
ExecStart=/home/pi/portscanner-client/venv/bin/portscanner-client
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable portscanner-client
sudo systemctl start portscanner-client
sudo systemctl status portscanner-client
```

View logs:

```bash
sudo journalctl -u portscanner-client -f
```

### launchd (macOS)

Create `~/Library/LaunchAgents/com.portscanner.client.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.portscanner.client</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/venv/bin/portscanner-client</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/portscanner-client</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/portscanner-client.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/portscanner-client.error.log</string>
</dict>
</plist>
```

Load and start:

```bash
launchctl load ~/Library/LaunchAgents/com.portscanner.client.plist
launchctl start com.portscanner.client
```

## Troubleshooting

### "nmap not found"

Install nmap on your system:

```bash
# Ubuntu/Debian
sudo apt-get install nmap

# macOS
brew install nmap
```

### "Permission denied" errors

Nmap requires root privileges for certain scan types. Either:

1. Run as root: `sudo portscanner-client`
2. Give nmap capabilities: `sudo setcap cap_net_raw,cap_net_admin=eip /usr/bin/nmap`

### "Cannot connect to server"

Check:
- Server is running
- `server_url` in config.yml is correct
- Network connectivity: `ping <server-ip>`
- Firewall allows connection

### Client not appearing in server

Check:
- Client is approved in server dashboard
- Heartbeat is being sent (check logs)
- Client ID is unique

### View logs

If running as a service:

```bash
# systemd
sudo journalctl -u portscanner-client -f

# Check config
portscanner-client-config
```

## Development

### Install dev dependencies

```bash
pip install -e ".[dev]"
```

### Run tests

```bash
pytest
```

### Format code

```bash
black client_agent.py
```

### Lint code

```bash
flake8 client_agent.py
```

## Architecture

The client agent:

1. Registers with the server using MAC address as client ID
2. Sends periodic heartbeats to maintain connection
3. Waits for approval from server admin
4. Polls for scan tasks when approved
5. Executes nmap scans on assigned targets
6. Reports results back to server
7. Handles network failures with automatic retry

## Security Considerations

- Client must be approved by server admin before executing scans
- Scans are restricted to configured `scan_range` if set
- All communication with server should use HTTPS in production
- Client credentials should be kept secure

## Hardware Requirements

Minimum:
- 512MB RAM
- 1GB disk space
- Network connectivity

## License

MIT License - see LICENSE file