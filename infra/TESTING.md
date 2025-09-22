# Port Scanner Test Environment - Quick Reference

## 🚀 Quick Start

```bash
cd infra
./test-environment.sh start    # Start everything
./test-environment.sh test     # Run test scan
./test-environment.sh stop     # Stop everything
```

## 🎯 Test Targets

| Service     | IP          | Ports                | Purpose               |
| ----------- | ----------- | -------------------- | --------------------- |
| SSH Server  | 172.20.0.10 | 2222                 | SSH service testing   |
| Web Server  | 172.20.0.11 | 80, 443              | HTTP/HTTPS testing    |
| Database    | 172.20.0.12 | 3306                 | MySQL testing         |
| FTP Server  | 172.20.0.13 | 21, 30000-30009      | FTP testing           |
| Redis Cache | 172.20.0.14 | 6379                 | Cache service testing |
| Multi-port  | 172.20.0.15 | 22, 8080, 8443, 9000 | Multiple services     |

## 🔧 Development Configurations

### For Docker Testing (Container → Container)

- Config: `test-config.yml`
- Server URL: `http://server:5000`
- Client ID: `rpi-test-client-001`

### For Local Development (Local → Docker)

- Config: `dev-config.yml`
- Server URL: `http://localhost:5000`
- Client ID: `dev-client-local`

## 📋 Common Commands

```bash
# Interactive container access
docker exec -it rpi-client bash

# View logs
docker logs rpi-client --follow
docker logs portscan-server --follow

# Manual scan test
docker exec rpi-client nmap -sS 172.20.0.0/24

# Check network connectivity
docker exec rpi-client ping 172.20.0.11

# Server health check
curl http://localhost:5000/
```

## 🐛 Troubleshooting

### Services won't start

```bash
docker-compose ps              # Check status
docker-compose logs           # View all logs
./test-environment.sh clean   # Clean reset
```

### Scans failing

```bash
# Check nmap is working
docker exec rpi-client nmap --version

# Test basic connectivity
docker exec rpi-client ping 172.20.0.11

# Check privileged mode
docker inspect rpi-client | grep -i privileged
```

### Server not responding

```bash
# Check server logs
docker logs portscan-server

# Test direct connection
curl -v http://localhost:5000/

# Restart server
docker-compose restart server
```

## 📁 File Structure

```
infra/
├── docker-compose.yml      # Main orchestration
├── client.dockerfile       # Raspberry Pi client image
├── server.dockerfile       # Flask server image
├── test-config.yml         # Docker test configuration
├── dev-config.yml          # Local development configuration
├── test-environment.sh     # Test automation script
├── test-web/               # Web server content
│   └── index.html
└── README.md              # Detailed documentation
```

## 🔄 Development Workflow

1. **Edit Code**: Modify client or server code
2. **Rebuild**: `docker-compose build <service>`
3. **Restart**: `docker-compose restart <service>`
4. **Test**: `./test-environment.sh test`
5. **Debug**: Check logs and test manually

## 🎛️ Environment Variables

| Variable     | Default                   | Description             |
| ------------ | ------------------------- | ----------------------- |
| FLASK_ENV    | development               | Flask environment       |
| FLASK_DEBUG  | 1                         | Enable Flask debug mode |
| DATABASE_URL | sqlite:///portscan_dev.db | Database connection     |
| PYTHONPATH   | /app                      | Python module path      |

## 🧪 Test Scenarios

- **Basic Discovery**: Verify port detection across all targets
- **Service Fingerprinting**: Test version detection capabilities
- **Delta Reporting**: Compare scan results over time
- **Network Range**: Test subnet scanning functionality
- **Error Handling**: Test with unreachable targets
- **Performance**: Measure scan duration and resource usage
