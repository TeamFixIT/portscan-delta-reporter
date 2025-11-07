---
layout: default
title: Usage
parent: Client
nav_order: 3
---

## Running the Client

### Start Manually

```bash
portscanner-client
```

Or use the included script:

```bash
./start_client.sh
```

### Command Line Options

```bash
portscanner-client --help
```

Available options:
- `--config PATH` - Specify custom config file location
- `--debug` - Enable debug logging
- `--server URL` - Override server URL from config
- `--port PORT` - Override client port from config

### Example Commands

```bash
# Use custom config file
portscanner-client --config /etc/scanner/config.yml

# Enable debug logging
portscanner-client --debug

# Override server URL
portscanner-client --server http://192.168.1.100:5000
```

---

## Running as a System Service

For production deployments, run the client as a system service.

### Linux (systemd)

#### Create Service File

Create `/etc/systemd/system/portscanner-client.service`:

```ini
[Unit]
Description=Port Scanner Client Agent
After=network.target

[Service]
Type=simple
User=scanner
Group=scanner
WorkingDirectory=/opt/portscanner-client
Environment="PATH=/opt/portscanner-client/venv/bin"
ExecStart=/opt/portscanner-client/venv/bin/portscanner-client
Restart=always
RestartSec=10

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/portscanner-client

[Install]
WantedBy=multi-user.target
```

#### Enable and Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable portscanner-client

# Start the service
sudo systemctl start portscanner-client

# Check status
sudo systemctl status portscanner-client
```

#### View Logs

```bash
# Follow logs in real-time
sudo journalctl -u portscanner-client -f

# View last 100 lines
sudo journalctl -u portscanner-client -n 100

# View logs since today
sudo journalctl -u portscanner-client --since today
```

#### Control Service

```bash
# Stop service
sudo systemctl stop portscanner-client

# Restart service
sudo systemctl restart portscanner-client

# Disable service
sudo systemctl disable portscanner-client
```

### macOS (launchd)

#### Create Launch Agent

Create `~/Library/LaunchAgents/com.portscanner.client.plist`:

```xml

<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" 
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">


    Label
    com.portscanner.client
    
    ProgramArguments
    
        /Users/username/portscanner-client/venv/bin/portscanner-client
    
    
    WorkingDirectory
    /Users/username/portscanner-client
    
    RunAtLoad
    
    
    KeepAlive
    
    
    StandardOutPath
    /tmp/portscanner-client.log
    
    StandardErrorPath
    /tmp/portscanner-client.error.log


```

#### Load and Start

```bash
# Load the service
launchctl load ~/Library/LaunchAgents/com.portscanner.client.plist

# Start the service
launchctl start com.portscanner.client

# Check if running
launchctl list | grep portscanner
```

#### View Logs

```bash
# Standard output
tail -f /tmp/portscanner-client.log

# Error output
tail -f /tmp/portscanner-client.error.log
```

#### Control Service

```bash
# Stop service
launchctl stop com.portscanner.client

# Unload service
launchctl unload ~/Library/LaunchAgents/com.portscanner.client.plist
```

---

## Permissions and Security

### Nmap Permissions

Nmap requires elevated privileges for certain scan types (SYN scans, OS detection).

#### Option 1: Run as Root (Simple)

```bash
sudo portscanner-client
```

Or in systemd service, set `User=root`.

#### Option 2: Grant Capabilities (Linux, More Secure)

Give nmap specific capabilities without running as root:

```bash
sudo setcap cap_net_raw,cap_net_admin,cap_net_bind_service=eip $(which nmap)
```

This allows nmap to:
- `cap_net_raw` - Use raw sockets (for SYN scans)
- `cap_net_admin` - Perform network administration
- `cap_net_bind_service` - Bind to privileged ports

Verify capabilities:

```bash
getcap $(which nmap)
```

#### Scan Type Limitations Without Root

| Scan Type | Requires Root | Alternative |
|-----------|---------------|-------------|
| TCP Connect | No | Default without root |
| TCP SYN | Yes | Use TCP Connect |
| UDP | Yes | N/A |
| OS Detection | Yes | Service detection only |

### Firewall Configuration

Ensure the client can communicate with the server:

#### Allow Outbound Connection

The client needs to:
- Connect to server on port 5000 (or configured port)
- Receive inbound connections on `client_port` (default 8080)

#### Example UFW Rules (Ubuntu)

```bash
# Allow outbound to server
sudo ufw allow out to  port 5000

# Allow inbound on client port
sudo ufw allow 8080/tcp

# Apply rules
sudo ufw reload
```

---

## Verification

### Check Installation

```bash
# Verify client command exists
which portscanner-client

# Verify configuration command exists
which portscanner-client-config

# Check Python package
pip show portscanner-client
```

### Test Connection

```bash
# Start the client
portscanner-client

# Check logs for:
# - "Connected to server as..."
# - "awaiting approval" or "approved client"
```

### Verify Server Registration

1. Log into the server web interface
2. Navigate to **Clients** page
3. Find your client in the list
4. Status should show "Connected"
5. Approve the client if needed

---

## Next Steps

After installation:

1. **[Configure the client](configuration.md)** - Customize settings
2. **[Approve in server](../server/#client-approval)** - User must approve

---

## Troubleshooting

See the [Troubleshooting Guide](troubleshooting.md) for common issues and solutions.

Quick checks:
- Is nmap installed? `nmap --version`
- Can you reach the server? `ping <server-ip>`
- Is the config file valid? `cat config.yml`
- Are logs showing errors? `journalctl -u portscanner-client -f`

---

## Support

Need help?
- **Issues**: [GitHub Issues](https://github.com/TeamFixIT/portscanner-delta-reporter/issues)
- **Documentation**: [Full Docs](../)

---