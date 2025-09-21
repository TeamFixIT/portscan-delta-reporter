# Client Agent Documentation

## Overview

The **Client Agent** (`client_agent.py`) is a distributed network scanning component designed to run on Raspberry Pi 4 devices. It acts as a remote scanning node that communicates with the central PortScan Delta Reporter server to perform network port scans and report results back for centralized analysis and reporting.

### Purpose

- Perform distributed network port scanning from multiple network locations
- Provide scalable scanning capabilities across different network segments
- Enable network reconnaissance from strategically positioned scanning nodes
- Support continuous monitoring and change detection workflows

---

## Architecture

### Component Overview

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│  Central Server │◄──────┤  Client Agent   │──────►│  Target Network │
│    (Flask)      │       │ (Raspberry Pi)  │       │    Hosts        │
└─────────────────┘       └─────────────────┘       └─────────────────┘
        │                           │
        │                           │
        ▼                           ▼
┌─────────────────┐       ┌─────────────────┐
│    Database     │       │   Scan Results  │
│   (SQLite)      │       │   (JSON/HTTP)   │
└─────────────────┘       └─────────────────┘
```

### Communication Flow

1. **Task Polling**: Client polls server for new scan tasks
2. **Scan Execution**: Client performs port scans using nmap
3. **Result Submission**: Client sends scan results back to server
4. **Status Reporting**: Client maintains heartbeat and status updates

---

## Core Classes and Data Structures

### ScanRequest

Represents a scan task received from the server.

```python
@dataclass
class ScanRequest:
    scan_id: str          # Unique identifier for the scan
    targets: List[str]    # List of IP addresses/hostnames to scan
    ports: str           # Port specification (e.g., "1-1000", "22,80,443")
    scan_type: str       # Scan type ("tcp", "udp", "syn")
    timeout: int         # Maximum scan duration in seconds
```

**Usage Example**:

```python
request = ScanRequest(
    scan_id="scan_001",
    targets=["192.168.1.1", "192.168.1.10"],
    ports="1-1000",
    scan_type="tcp",
    timeout=300
)
```

### ScanResult

Represents the outcome of a completed scan operation.

```python
@dataclass
class ScanResult:
    scan_id: str              # Matches the original request ID
    client_id: str           # Unique identifier of the scanning client
    timestamp: str           # ISO format timestamp of scan completion
    target: str              # IP/hostname that was scanned
    status: str              # "completed", "failed", "timeout"
    open_ports: List[Dict]   # Detailed port information
    scan_duration: float     # Actual scan time in seconds
    error_message: Optional[str]  # Error details if status="failed"
```

**Open Ports Structure**:

```python
{
    "port": 80,
    "state": "open",
    "service": "http",
    "version": "Apache/2.4.41",
    "product": "Apache httpd"
}
```

---

## Core Functionality

### Client Initialization

The `PortScannerClient` class manages all client operations:

```python
client = PortScannerClient(config_file="config.yml")
```

**Initialization Process**:

1. **Client ID Generation**: Creates unique identifier based on MAC address
2. **Configuration Loading**: Loads settings from YAML configuration file
3. **nmap Scanner Setup**: Initializes the python-nmap scanner instance

### Scan Execution Process

#### 1. Task Polling

```python
def check_for_tasks(self) -> Optional[ScanRequest]:
    """Check server for new scan tasks"""
```

- **Endpoint**: `GET /api/scan-tasks/{client_id}`
- **Frequency**: Every 30 seconds (configurable)
- **Response**: ScanRequest object or None

#### 2. Port Scanning

```python
def perform_scan(self, scan_request: ScanRequest) -> ScanResult:
    """Perform a port scan based on the request"""
```

**Scan Process**:

1. Extract target and port specifications from request
2. Execute nmap scan with appropriate arguments
3. Parse scan results to identify open ports
4. Extract service information (name, version, product)
5. Calculate scan duration and create result object

**nmap Integration**:

```python
self.nm.scan(target, ports, arguments=f'-s{scan_type.upper()}')
```

#### 3. Result Transmission

```python
def send_result(self, result: ScanResult) -> bool:
    """Send scan result back to server"""
```

- **Endpoint**: `POST /api/scan-results`
- **Format**: JSON serialized ScanResult
- **Timeout**: 30 seconds
- **Retry Logic**: Currently none (returns False on failure)

---

## Configuration

### Default Configuration

```python
{
    'server_url': 'http://localhost:5000',
    'check_interval': 30,           # Task polling interval (seconds)
    'max_concurrent_scans': 2       # Maximum parallel scans
}
```

### Configuration File (config.yml)

```yaml
server:
  url: "http://192.168.1.100:5000"
  timeout: 30

client:
  check_interval: 30
  max_concurrent_scans: 2
  log_level: "INFO"

scanning:
  default_timeout: 300
  nmap_arguments: "-sS -O" # Additional nmap flags
```

**Note**: YAML configuration loading is marked as TODO in current implementation.

---

## Deployment

### Prerequisites

**Hardware Requirements**:

- Raspberry Pi 4 (minimum 2GB RAM recommended)
- MicroSD card (16GB+)
- Network connectivity (Ethernet or WiFi)

**Software Requirements**:

- Python 3.8+
- nmap system package
- Required Python packages (see requirements.txt)

### Installation Steps

1. **System Preparation**:

   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install nmap python3-pip python3-venv -y
   ```

2. **Client Setup**:

   ```bash
   cd /opt
   sudo git clone <repository-url>
   cd portscan_delta_reporter/client
   sudo ./setup.sh
   ```

3. **Configuration**:

   ```bash
   cp config.example.yml config.yml
   # Edit config.yml with your server details
   ```

4. **Service Installation**:
   ```bash
   sudo cp ../infra/portscan-client.service /etc/systemd/system/
   sudo systemctl enable portscan-client
   sudo systemctl start portscan-client
   ```

### Running the Client

**Development Mode**:

```bash
source venv/bin/activate
python client_agent.py
```

**Production Mode**:

```bash
sudo systemctl start portscan-client
sudo systemctl status portscan-client
```

---

## Monitoring and Logging

### Log Format

```
2024-09-21 10:30:45 - PortScannerClient - INFO - Client AA:BB:CC:DD:EE:FF starting...
2024-09-21 10:31:15 - PortScannerClient - INFO - Starting scan scan_001 for target 192.168.1.1
2024-09-21 10:31:45 - PortScannerClient - INFO - Successfully sent result for scan scan_001
```

### Key Metrics to Monitor

- **Task Polling Frequency**: Should occur every 30 seconds
- **Scan Success Rate**: Percentage of successful vs failed scans
- **Network Connectivity**: Connection failures to central server
- **Resource Usage**: CPU and memory consumption during scans

### Health Checks

Monitor the following indicators:

```bash
# Service status
sudo systemctl status portscan-client

# Recent logs
sudo journalctl -u portscan-client -f

# Process monitoring
ps aux | grep client_agent
```

---

## Error Handling

### Common Issues and Solutions

#### 1. Connection Refused (Server Unreachable)

**Symptoms**:

```
Failed to check for tasks: HTTPConnectionPool(...): Max retries exceeded
```

**Solutions**:

- Verify server URL in configuration
- Check network connectivity to server
- Confirm server is running and accessible

#### 2. Permission Denied (nmap)

**Symptoms**:

```
Scan failed: [Errno 13] Permission denied
```

**Solutions**:

- Run client with sudo privileges for raw socket access
- Use TCP connect scans instead of SYN scans
- Configure proper capabilities for the nmap binary

#### 3. Timeout Errors

**Symptoms**:

```
Scan failed: Scan timeout exceeded
```

**Solutions**:

- Increase timeout values in scan requests
- Reduce port range for intensive scans
- Check target host responsiveness

### Error Recovery

The client implements basic error recovery:

- **Network Errors**: Continue polling after delay
- **Scan Failures**: Log error and continue with next task
- **Server Errors**: Maintain local queue (TODO: not implemented)

---

## API Integration

### Server Endpoints Used

#### GET /api/scan-tasks/{client_id}

**Purpose**: Retrieve pending scan tasks for this client

**Response**:

```json
{
  "scan_id": "scan_001",
  "targets": ["192.168.1.1"],
  "ports": "1-1000",
  "scan_type": "tcp",
  "timeout": 300
}
```

#### POST /api/scan-results

**Purpose**: Submit completed scan results

**Request Body**:

```json
{
  "scan_id": "scan_001",
  "client_id": "AABBCCDDEEFF",
  "timestamp": "2024-09-21 10:31:45",
  "target": "192.168.1.1",
  "status": "completed",
  "open_ports": [
    {
      "port": 80,
      "state": "open",
      "service": "http",
      "version": "Apache/2.4.41",
      "product": "Apache httpd"
    }
  ],
  "scan_duration": 45.2
}
```

---

## Security Considerations

### Network Security

- **Firewall Rules**: Ensure client can reach server on configured port
- **Authentication**: Currently no authentication (TODO for production)
- **Encryption**: HTTP traffic is unencrypted (consider HTTPS)

### System Security

- **Privilege Escalation**: nmap may require root privileges
- **Network Interfaces**: Client reads MAC addresses for identification
- **Process Isolation**: Run client in dedicated user context

### Scanning Ethics

- **Authorization**: Only scan networks you own or have permission to test
- **Rate Limiting**: Respect target network capacity
- **Logging**: Maintain audit trails of all scanning activity

---

## Performance Optimization

### Scan Performance

**Current Limitations**:

- Single-threaded scanning per client
- No scan result caching
- Synchronous communication with server

**Optimization Strategies**:

1. **Parallel Scanning**: Implement multi-threading for multiple targets
2. **Incremental Scans**: Only scan changed ports on subsequent runs
3. **Result Compression**: Compress large scan results before transmission
4. **Connection Pooling**: Reuse HTTP connections to server

### Resource Management

**Memory Usage**:

- nmap results stored in memory during processing
- Consider streaming large results for memory efficiency

**CPU Usage**:

- nmap scanning is CPU-intensive
- Implement configurable scan intensity levels

---

## Future Enhancements

### Planned Features

1. **Configuration Management**:

   - YAML configuration file support
   - Dynamic configuration updates from server
   - Environment variable overrides

2. **Advanced Scanning**:

   - UDP port scanning support
   - Service version detection improvements
   - Custom nmap script integration

3. **Reliability Improvements**:

   - Retry logic for failed operations
   - Local result queuing for offline scenarios
   - Health monitoring and self-recovery

4. **Security Enhancements**:
   - API authentication and authorization
   - TLS/SSL encryption for communications
   - Client certificate-based authentication

### Technical Debt

- **TODO Items in Code**:
  - YAML configuration loading implementation
  - Multiple target scanning support
  - Concurrent scan management
  - Result queuing for offline operation

---

## Testing

### Unit Testing

Currently, no unit tests are implemented. Recommended test coverage:

```python
# Example test structure
def test_client_id_generation():
    """Test client ID generation from MAC address"""

def test_scan_execution():
    """Test port scan execution and result parsing"""

def test_server_communication():
    """Test HTTP communication with server"""
```

### Integration Testing

Test scenarios:

1. **End-to-End Workflow**: Full scan request → execution → result submission
2. **Network Failure Recovery**: Server connectivity loss and recovery
3. **Invalid Input Handling**: Malformed scan requests and responses

---

## Troubleshooting Guide

### Debug Mode

Enable verbose logging:

```python
logging.basicConfig(level=logging.DEBUG)
```

### Common Problems

| Problem                  | Symptoms                    | Solution                                   |
| ------------------------ | --------------------------- | ------------------------------------------ |
| Server Connection Failed | `Failed to check for tasks` | Verify server URL and network connectivity |
| nmap Not Found           | `nmap command not found`    | Install nmap: `sudo apt install nmap`      |
| Permission Denied        | `Permission denied`         | Run with sudo or set nmap capabilities     |
| Port Already in Use      | `Address already in use`    | Check for multiple client instances        |

### Diagnostic Commands

```bash
# Test server connectivity
curl -v http://server:5000/api/scan-tasks/test-client

# Test nmap functionality
nmap -sT -p 80 google.com

# Check client logs
tail -f /var/log/portscan-client.log

# Monitor network traffic
sudo tcpdump -i any host server-ip
```

---

## Contributing

### Code Style

- Follow PEP 8 Python style guidelines
- Use type hints for all function parameters and returns
- Document all public methods with docstrings
- Maintain consistent error handling patterns

### Development Setup

```bash
# Development environment
cd client/
python -m venv venv-dev
source venv-dev/bin/activate
pip install -r requirements.txt
pip install pytest black flake8  # Development tools
```

### Submitting Changes

1. Create feature branch from main
2. Implement changes with appropriate tests
3. Run code quality checks: `black client_agent.py && flake8 client_agent.py`
4. Submit pull request with detailed description

---

## Appendix

### Dependencies

Key Python packages used:

- `requests`: HTTP communication with server
- `python-nmap`: nmap integration and result parsing
- `psutil`: System information and process monitoring
- `netifaces`: Network interface information
- `pyyaml`: Configuration file parsing (planned)

### Reference Links

- [nmap Official Documentation](https://nmap.org/book/)
- [python-nmap Library](https://pypi.org/project/python-nmap/)
- [Raspberry Pi Documentation](https://www.raspberrypi.org/documentation/)
- [Flask Framework](https://flask.palletsprojects.com/)

### Changelog

| Version | Date       | Changes                                                  |
| ------- | ---------- | -------------------------------------------------------- |
| 1.0.0   | 2024-09-21 | Initial implementation with basic scanning functionality |

---

_This documentation serves as a template for future component documentation in the PortScan Delta Reporter project. Each component should follow this structure: Overview, Architecture, Core Functionality, Configuration, Deployment, Monitoring, Error Handling, API Integration, Security, Performance, Future Enhancements, Testing, Troubleshooting, Contributing, and Appendix._
