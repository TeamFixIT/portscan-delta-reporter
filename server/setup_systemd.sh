#!/bin/bash
# Port Scanner Delta Reporter - Production Setup Script
# This script automates the setup of systemd service

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Port Scanner Delta Reporter - Production Setup ===${NC}\n"

# Get current directory
INSTALL_DIR=$(pwd)
echo -e "Installation directory: ${YELLOW}${INSTALL_DIR}${NC}"

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo -e "${RED}Error: Do not run this script as root${NC}"
    echo "Run as regular user, you'll be prompted for sudo when needed"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}Error: Virtual environment not found${NC}"
    echo "Run ./setup_client.sh first"
    exit 1
fi

# Check if database exists
if [ ! -f "data/app.db" ] && [ ! -f "app.db" ]; then
    echo -e "${RED}Error: Database not found${NC}"
    echo "Run ./setup_app.sh first"
    exit 1
fi

echo -e "\n${GREEN}Step 1: Installing production dependencies${NC}"
source venv/bin/activate
pip install gunicorn eventlet
pip freeze > requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

echo -e "\n${GREEN}Step 2: Creating system user${NC}"
if id "portscanner" &>/dev/null; then
    echo -e "${YELLOW}User 'portscanner' already exists${NC}"
else
    sudo useradd -r -s /bin/false portscanner
    echo -e "${GREEN}✓ User 'portscanner' created${NC}"
fi

echo -e "\n${GREEN}Step 3: Setting up log directory${NC}"
sudo mkdir -p /var/log/portscanner
sudo chown -R portscanner:portscanner /var/log/portscanner
echo -e "${GREEN}✓ Log directory created${NC}"

echo -e "\n${GREEN}Step 4: Setting file permissions${NC}"
sudo chown -R portscanner:portscanner "${INSTALL_DIR}"
echo -e "${GREEN}✓ Permissions set${NC}"

echo -e "\n${GREEN}Step 5: Creating systemd service file${NC}"

# Create the service file
sudo tee /etc/systemd/system/portscanner.service > /dev/null <<EOF
[Unit]
Description=Port Scanner Delta Reporter
Documentation=https://github.com/your-repo/port-scanner
After=network.target

[Service]
Type=notify
User=portscanner
Group=portscanner

# Working directory
WorkingDirectory=${INSTALL_DIR}

# Environment variables
Environment="PATH=${INSTALL_DIR}/venv/bin"
Environment="FLASK_ENV=production"

# Start command
ExecStart=${INSTALL_DIR}/venv/bin/gunicorn \\
    --worker-class eventlet \\
    -w 1 \\
    --bind 0.0.0.0:5000 \\
    --timeout 120 \\
    --graceful-timeout 30 \\
    --access-logfile /var/log/portscanner/access.log \\
    --error-logfile /var/log/portscanner/error.log \\
    --log-level info \\
    --pid /run/portscanner/portscanner.pid \\
    run:app

# Runtime directory
RuntimeDirectory=portscanner
RuntimeDirectoryMode=0755

# Restart policy
Restart=always
RestartSec=10

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=${INSTALL_DIR}/data ${INSTALL_DIR}/uploads ${INSTALL_DIR}/scan_results /var/log/portscanner

# Resource limits
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✓ Service file created at /etc/systemd/system/portscanner.service${NC}"

echo -e "\n${GREEN}Step 6: Enabling and starting service${NC}"
sudo systemctl daemon-reload
sudo systemctl enable portscanner.service
sudo systemctl start portscanner.service

sleep 2

# Check if service started successfully
if sudo systemctl is-active --quiet portscanner.service; then
    echo -e "${GREEN}✓ Service started successfully!${NC}"
else
    echo -e "${RED}✗ Service failed to start${NC}"
    echo -e "\nChecking logs...\n"
    sudo journalctl -u portscanner.service -n 20 --no-pager
    exit 1
fi

echo -e "\n${GREEN}=== Setup Complete! ===${NC}\n"

echo -e "${GREEN}Service Management Commands:${NC}"
echo -e "  Start:   ${YELLOW}sudo systemctl start portscanner.service${NC}"
echo -e "  Stop:    ${YELLOW}sudo systemctl stop portscanner.service${NC}"
echo -e "  Restart: ${YELLOW}sudo systemctl restart portscanner.service${NC}"
echo -e "  Status:  ${YELLOW}sudo systemctl status portscanner.service${NC}"
echo -e "  Logs:    ${YELLOW}sudo journalctl -u portscanner.service -f${NC}"

echo -e "\n${GREEN}Access your application:${NC}"
echo -e "  Local:  ${YELLOW}http://localhost:5000${NC}"
echo -e "  Remote: ${YELLOW}http://$(hostname -I | awk '{print $1}'):5000${NC}"

echo -e "\n${YELLOW}Note:${NC} The simple ./start.sh script will no longer work while the service is running."
echo -e "To use development mode again, stop the service first:"
echo -e "  ${YELLOW}sudo systemctl stop portscanner.service${NC}"

echo -e "\n${GREEN}Next steps:${NC}"
echo -e "  1. Configure firewall to allow port 5000 (or setup Nginx)"
echo -e "  2. Configure application settings at /settings"
echo -e "  3. Setup SSL/TLS for production (see PRODUCTION_SETUP.md)"

echo -e "\n${GREEN}Setup completed successfully!${NC}"