---
layout: default
title: Troubleshooting
parent: Client
nav_order: 4
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