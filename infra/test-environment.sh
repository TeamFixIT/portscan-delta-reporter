#!/bin/bash

# Port Scanner Test Environment Setup and Testing Script
# This script helps set up and test the Raspberry Pi client scanner in Docker

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if Docker and Docker Compose are available
check_prerequisites() {
    print_step "Checking prerequisites..."

    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        exit 1
    fi

    if docker compose version &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker compose"
    elif command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker-compose"
    else
        print_error "Docker Compose is not installed or not in PATH"
        exit 1
    fi

    print_status "Prerequisites check passed (using $DOCKER_COMPOSE_CMD)"
}

# Build and start the test environment
start_environment() {
    print_step "Starting test environment..."
    $DOCKER_COMPOSE_CMD up -d --build

    print_status "Waiting for services to start..."
    sleep 10

    print_step "Checking service status..."
    $DOCKER_COMPOSE_CMD ps
}

# Stop the test environment
stop_environment() {
    print_step "Stopping test environment..."
    $DOCKER_COMPOSE_CMD down
    print_status "Test environment stopped"
}

# Run a test scan from the client
run_test_scan() {
    print_step "Running test scan from Raspberry Pi client..."

    docker exec -i rpi-client python <<'EOF'
import yaml
import nmap
import json
from datetime import datetime

with open("config.yml", "r") as f:
    config = yaml.safe_load(f)

print("=== Port Scanner Test Results ===")
print(f"Client ID: {config['client']['client_id']}")
print(f"Server URL: {config['server']['url']}")
print(f"Test Subnet: {config['scanning']['test_subnet']}")
print()

nm = nmap.PortScanner()

for target in config["test_targets"]:
    print(f"Scanning {target['name']} ({target['ip']})...")
    try:
        scan_result = nm.scan(
            target["ip"],
            target["ports"],
            arguments=config["scanning"]["default_args"]
        )

        if target["ip"] in scan_result["scan"]:
            host_info = scan_result["scan"][target["ip"]]
            print(f"  Host state: {host_info.get('status', {}).get('state', 'unknown')}")

            if "tcp" in host_info:
                open_ports = [p for p, info in host_info["tcp"].items() if info["state"] == "open"]
                print(f"  Open ports: {open_ports}")
                for port in open_ports:
                    port_info = host_info["tcp"][port]
                    service = port_info.get("name", "unknown")
                    version = port_info.get("version", "")
                    print(f"    {port}/tcp: {service} {version}".strip())
            else:
                print("  No TCP ports found")
        else:
            print("  Host not found in scan results")

    except Exception as e:
        print(f"  Scan failed: {str(e)}")
    print()

print("=== Test Scan Complete ===")
EOF
}

# Check server connectivity
check_server() {
    print_step "Checking server connectivity..."
    if curl -f -s http://localhost:5000/ > /dev/null; then
        print_status "Server is responding on http://localhost:5000"
    else
        print_warning "Server not responding, checking container logs..."
        docker logs portscan-server --tail 20
    fi
}

# Show container logs
show_logs() {
    local service=$1
    print_step "Showing logs for $service..."
    docker logs "$service" --tail 50
}

# Interactive mode
interactive_mode() {
    print_step "Entering interactive mode..."
    print_status "Available commands: scan, server, logs, exec, status, stop, quit"
    echo

    while true; do
        read -p "test> " cmd args
        case $cmd in
            scan) run_test_scan ;;
            server) check_server ;;
            logs)
                if [ -n "$args" ]; then
                    show_logs "$args"
                else
                    echo "Available containers: rpi-client, portscan-server, target-ssh, target-web, target-db, target-ftp, target-redis, target-multiport"
                    read -p "Container name: " container
                    show_logs "$container"
                fi
                ;;
            exec)
                if [ -n "$args" ]; then
                    docker exec -it rpi-client $args
                else
                    docker exec -it rpi-client bash
                fi
                ;;
            status) $DOCKER_COMPOSE_CMD ps ;;
            stop) stop_environment; break ;;
            quit) break ;;
            help|?) print_status "Available commands: scan, server, logs, exec, status, stop, quit" ;;
            *) print_warning "Unknown command: $cmd" ;;
        esac
        echo
    done
}

main() {
    echo "======================================"
    echo "Port Scanner Test Environment Manager"
    echo "======================================"
    echo

    case "${1:-start}" in
        start)
            check_prerequisites
            start_environment
            check_server
            print_status "Test environment is ready!"
            print_status "Access the web interface at: http://localhost:5000"
            print_status "Run '$0 test' to execute a test scan"
            print_status "Run '$0 interactive' for interactive mode"
            ;;
        stop) stop_environment ;;
        test) run_test_scan ;;
        logs) show_logs "${2:-rpi-client}" ;;
        server) check_server ;;
        interactive) interactive_mode ;;
        clean)
            print_step "Cleaning up environment..."
            $DOCKER_COMPOSE_CMD down -v
            docker system prune -f
            print_status "Cleanup complete"
            ;;
        *)
            echo "Usage: $0 {start|stop|test|logs|server|interactive|clean}"
            exit 1
            ;;
    esac
}

main "$@"
