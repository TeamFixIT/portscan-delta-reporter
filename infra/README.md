# Port Scanner Test Environment

This directory contains Docker infrastructure for testing the port scanner client-server system in a controlled environment that simulates a client scanning various network targets.

## Quick Start

```bash
# Start the complete test environment
./test-environment.sh start

# Run a test scan
./test-environment.sh test

# Enter interactive testing mode
./test-environment.sh interactive

# Stop the environment
./test-environment.sh stop
```

## Architecture

The test environment consists of:

### Core Services

- **portscan-server**: Flask backend server (accessible at http://localhost:5000)
- **rpi-client**: Client simulator with nmap scanning capabilities

### Test Targets (Simulated Network Devices)

- **target-ssh** (172.20.0.10): OpenSSH server with custom configuration
- **target-web** (172.20.0.11): Nginx web server with test content
- **target-db** (172.20.0.12): MySQL database server
- **target-ftp** (172.20.0.13): Pure-FTPd server with passive mode
- **target-redis** (172.20.0.14): Redis cache server with authentication
- **target-multiport** (172.20.0.15): Custom service with multiple open ports

All services run on an isolated Docker network (172.20.0.0/16) to simulate a real network environment.

## Configuration

### Client Configuration

The client uses `test-config.yml` which is automatically mounted into the container. Key settings:

- **Server URL**: `http://server:5000` (Docker service name)
- **Client ID**: `rpi-test-client-001`
- **Check Interval**: 10 seconds (faster for testing)
- **Scan Timeout**: 120 seconds
- **Log Level**: DEBUG for detailed output

### Network Layout

```
172.20.0.1    - Docker Gateway
172.20.0.10   - SSH Server (port 2222)
172.20.0.11   - Web Server (ports 80, 443)
172.20.0.12   - Database Server (port 3306)
172.20.0.13   - FTP Server (port 21, 30000-30009)
172.20.0.14   - Redis Server (port 6379)
172.20.0.15   - Multi-port Service (ports 22, 8080, 8443, 9000)
```

## Manual Testing Commands

### 1. Start Environment

```bash
docker-compose up -d --build
```

This builds and starts all services in detached mode.

### 2. Check Service Status

```bash
docker-compose ps
```

Verify all containers are running and healthy.

### 3. Access Client

```bash
docker exec -it rpi-client bash
```

Get shell access to the client container for manual testing.

### 4. Run Manual Scan

```bash
docker exec rpi-client python -c "
import nmap
nm = nmap.PortScanner()
result = nm.scan('172.20.0.11', '80,443')
print(result)
"
```

### 5. Test Client Agent

```bash
docker exec rpi-client python client_agent.py
```

Start the client agent to connect to the server.

### 6. Check Server Logs

```bash
docker logs portscan-server --follow
```

### 7. Check Client Logs

```bash
docker logs rpi-client --follow
```

## Development Workflow

### For Client Development

1. Edit client code in `../client/`
2. Restart client container: `docker-compose restart rpi-client`
3. Test changes: `./test-environment.sh test`

### For Server Development

1. Edit server code in `../server/`
2. Restart server container: `docker-compose restart server`
3. Access web interface: http://localhost:5000

### For Configuration Changes

1. Edit `test-config.yml`
2. Restart client: `docker-compose restart rpi-client`

## Testing Scenarios

### Basic Port Discovery

Test that the client can discover open ports on target services:

```bash
# SSH server test
docker exec rpi-client nmap -p 22,2222 172.20.0.10

# Web server test
docker exec rpi-client nmap -p 80,443 172.20.0.11

# Database server test
docker exec rpi-client nmap -p 3306 172.20.0.12
```

### Service Version Detection

Test service fingerprinting capabilities:

```bash
docker exec rpi-client nmap -sV 172.20.0.11
```

### Network Range Scanning

Test subnet scanning:

```bash
docker exec rpi-client nmap -sn 172.20.0.0/24
```

### Delta Reporting Test

1. Run initial scan and record results
2. Modify a target service (e.g., stop nginx)
3. Run second scan
4. Verify delta detection

## Troubleshooting

### Container Issues

```bash
# Check container status
docker-compose ps

# View all logs
docker-compose logs

# Rebuild specific service
docker-compose build rpi-client
docker-compose up -d rpi-client
```

### Network Issues

```bash
# Check network connectivity
docker exec rpi-client ping 172.20.0.11

# Check DNS resolution
docker exec rpi-client nslookup server

# Test port accessibility
docker exec rpi-client nc -zv 172.20.0.11 80
```

### Permission Issues

```bash
# The client container runs with privileged mode for nmap
# If scans fail, check container capabilities:
docker exec rpi-client nmap --iflist
```

## Cleanup

### Stop and Remove Everything

```bash
./test-environment.sh clean
```

This stops all containers, removes volumes, and cleans up Docker resources.

### Manual Cleanup

```bash
# Stop services
docker-compose down

# Remove volumes
docker-compose down -v

# Clean up Docker system
docker system prune -f
```

## Advanced Configuration

### Adding New Test Targets

1. Add service to `docker-compose.yml`
2. Assign static IP in 172.20.0.x range
3. Update `test-config.yml` with target details
4. Restart environment

### Modifying Scan Parameters

Edit `test-config.yml`:

- Change `default_args` for different nmap options
- Adjust `default_timeout` for scan duration
- Modify `check_interval` for polling frequency

### Custom Test Scripts

The `test-environment.sh` script can be extended with additional test scenarios or integrated into CI/CD pipelines for automated testing.
