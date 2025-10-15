#!/bin/bash

# Quick Start Script for Port Scanner Test Environment
# This gets your demo environment up and running quickly

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════════════╗"
echo "║   Port Scanner Test Environment - Quick Start         ║"
echo "╚════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check prerequisites
echo -e "${BLUE}[1/5]${NC} Checking prerequisites..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker not found!${NC}"
    exit 1
fi

if docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
else
    echo -e "${RED}✗ Docker Compose not found!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker and Docker Compose found${NC}"

# Create test-web directory if it doesn't exist
echo -e "${BLUE}[2/5]${NC} Setting up test files..."
mkdir -p test-web
if [ ! -f "test-web/index.html" ]; then
    cat > test-web/index.html << 'EOF'
<!DOCTYPE html>
<html><head><title>Test Target</title></head>
<body><h1>Test Web Server</h1><p>Port scanner test target</p></body></html>
EOF
fi
echo -e "${GREEN}✓ Test files ready${NC}"

# Stop any existing containers
echo -e "${BLUE}[3/5]${NC} Cleaning up old containers..."
$DOCKER_COMPOSE_CMD down -v 2>/dev/null || true
echo -e "${GREEN}✓ Cleanup complete${NC}"

# Build and start services
echo -e "${BLUE}[4/5]${NC} Building and starting services..."
echo -e "${YELLOW}This may take a few minutes on first run...${NC}"
$DOCKER_COMPOSE_CMD up -d --build

# Wait for server to be ready
echo -e "${BLUE}[5/5]${NC} Waiting for server to start..."
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if curl -s -f http://localhost:5000 > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Server is ready!${NC}"
        break
    fi
    attempt=$((attempt + 1))
    echo -n "."
    sleep 2
done
echo ""

if [ $attempt -eq $max_attempts ]; then
    echo -e "${RED}✗ Server failed to start${NC}"
    echo -e "${YELLOW}Checking logs...${NC}"
    docker logs portscan-server --tail 30
    exit 1
fi

# Show status
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗"
echo -e "║              🎉 Environment Ready!                     ║"
echo -e "╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}📊 Service Status:${NC}"
$DOCKER_COMPOSE_CMD ps
echo ""
echo -e "${CYAN}🌐 Access Points:${NC}"
echo -e "  ${GREEN}•${NC} Web Interface: ${YELLOW}http://localhost:5000${NC}"
echo -e "  ${GREEN}•${NC} API Endpoint:  ${YELLOW}http://localhost:5000/api${NC}"
echo ""
echo -e "${CYAN}🧪 Quick Tests:${NC}"
echo -e "  ${GREEN}•${NC} Check server:    ${YELLOW}curl http://localhost:5000${NC}"
echo -e "  ${GREEN}•${NC} Run test scan:   ${YELLOW}./test-environment.sh test${NC}"
echo -e "  ${GREEN}•${NC} View logs:       ${YELLOW}docker logs portscan-server${NC}"
echo -e "  ${GREEN}•${NC} Client 1 shell:  ${YELLOW}docker exec -it rpi-client bash${NC}"
echo -e "  ${GREEN}•${NC} Client 2 shell:  ${YELLOW}docker exec -it rpi-client-2 bash${NC}"
echo -e "  ${GREEN}•${NC} Client 1 logs:   ${YELLOW}docker logs rpi-client -f${NC}"
echo -e "  ${GREEN}•${NC} Client 2 logs:   ${YELLOW}docker logs rpi-client-2 -f${NC}"
echo ""
echo -e "${CYAN}📋 Test Targets Available:${NC}"
echo -e "  ${GREEN}Client 1 (172.20.0.100)${NC} scans:"
echo -e "    • SSH Server:    172.20.0.10:2222"
echo -e "    • Web Server:    172.20.0.11:80"
echo -e "    • MySQL DB:      172.20.0.12:3306"
echo ""
echo -e "  ${GREEN}Client 2 (172.20.0.101)${NC} scans:"
echo -e "    • FTP Server:    172.20.0.13:21"
echo -e "    • Redis Cache:   172.20.0.14:6379"
echo -e "    • Multi-port:    172.20.0.15"
echo ""
echo -e "${CYAN}🛑 To stop:${NC} ${YELLOW}$DOCKER_COMPOSE_CMD down${NC}"
echo ""