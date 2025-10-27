#!/bin/bash
# Script for Port Scanner Test Environment
set -e
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Check for -r flag
RUNNING_MODE=false
while getopts "r" opt; do
    case $opt in
        r) RUNNING_MODE=true ;;
        *) echo -e "${RED}✗ Invalid option. Use -r to skip to interactive mode if services are running.${NC}"; exit 1 ;;
    esac
done

# Function to enter interactive CLI mode
enter_interactive_mode() {
    echo -e "${CYAN}Entering interactive CLI mode...${NC}"
    echo "Available commands:"
    echo "  flask <flask-command>  - Run a Flask command (e.g., flask create-admin)"
    echo "  logs [container-name]  - View live logs (no container name for all services)"
    echo "  help                   - Show this help message"
    echo "  exit                   - Quit interactive mode"
    echo "  stop                   - Stop the services"
    while true; do
        read -r -p "> " input
        if [ -z "$input" ]; then
            continue
        fi
        # Split input into command and arguments more robustly
        cmd=$(echo "$input" | awk '{print $1}')
        # Only capture args if there are additional fields
        args=""
        if [ "$(echo "$input" | wc -w)" -gt 1 ]; then
            args=$(echo "$input" | cut -d' ' -f2-)
        fi
        if [ "$cmd" = "exit" ]; then
            break
        elif [ "$cmd" = "flask" ]; then
            if [ -z "$args" ]; then
                echo -e "${RED}✗ Please provide a Flask command after 'flask'${NC}"
                continue
            fi
            echo -e "${BLUE}Running flask $args...${NC}"
            $DOCKER_COMPOSE_CMD exec server flask $args
        elif [ "$cmd" = "logs" ]; then
            if [ -z "$args" ]; then
                echo -e "${BLUE}Viewing live logs for all services... (Ctrl+C to stop)${NC}"
                $DOCKER_COMPOSE_CMD logs -f || echo -e "${RED}✗ Stopped viewing logs for all services${NC}"
            else
                echo -e "${BLUE}Viewing live logs for $args... (Ctrl+C to stop)${NC}"
                docker logs -f "$args" || echo -e "${RED}✗ Stopped viewing logs for $args${NC}"
            fi
        elif [ "$cmd" = "help" ]; then
            echo "Available commands:"
            echo "  flask <flask-command>  - Run a Flask command (e.g., flask create-admin)"
            echo "  logs [container-name]  - View live logs (no container name for all services)"
            echo "  help                   - Show this help message"
            echo "  exit                   - Quit interactive mode"
            echo "  stop                   - Stop the services"
        elif [ "$cmd" = "stop" ]; then
            echo -e "${BLUE}Stopping services...${NC}"
            $DOCKER_COMPOSE_CMD down
            echo -e "${GREEN}✓ Services stopped.${NC}"
            break
        else
            echo -e "${RED}✗ Unknown command: $cmd${NC}"
        fi
    done
    echo -e "${GREEN}Exiting interactive mode.${NC}"
}

# Set DOCKER_COMPOSE_CMD explicitly
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
else
    echo -e "${RED}✗ Docker Compose not found!${NC}"
    exit 1
fi

# Check if services are running and -r flag is set
if [ "$RUNNING_MODE" = true ]; then
    echo -e "${BLUE}Checking if services are running...${NC}"
    # Use --services --filter status=running to check for running services
    if [ -n "$($DOCKER_COMPOSE_CMD ps --services --filter status=running)" ]; then
        echo -e "${GREEN}✓ Services are running, entering interactive mode.${NC}"
        enter_interactive_mode
        exit 0
    else
        echo -e "${YELLOW}No services are running, proceeding with full setup...${NC}"
    fi
fi

echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════════════╗"
echo "║              Port Scanner Test Environment             ║"
echo "╚════════════════════════════════════════════════════════╝"
echo -e "${NC}"
# Check prerequisites
echo -e "${BLUE}[1/6]${NC} Checking prerequisites..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker not found!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker found${NC}"
# DOCKER_COMPOSE_CMD already set above
echo -e "${GREEN}✓ Docker Compose set to: $DOCKER_COMPOSE_CMD${NC}"
# Create test-web directory if it doesn't exist
echo -e "${BLUE}[2/6]${NC} Setting up env files..."
# Create server.env if it doesn't exist
if [ ! -f "server.env" ]; then
    cat > server.env << 'EOF'
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:////app/instance/app.db
REDIS_URL=redis://server-redis:6379/0
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email-username
MAIL_PASSWORD=your-email-password
MAIL_SENDER=noreply@portdetector.com
ENTRA_CLIENT_ID=your-entra-client-id
ENTRA_CLIENT_SECRET=your-entra-client-secret
ENTRA_TENANT_ID=your-entra-tenant-id
SESSION_COOKIE_SECURE=false
EOF
    echo -e "${YELLOW}✓ Created server.env (please update with your credentials)${NC}"
else
    echo -e "${GREEN}✓ server.env exists${NC}"
fi
# Stop any existing containers
echo -e "${BLUE}[3/6]${NC} Cleaning up old containers..."
$DOCKER_COMPOSE_CMD down -v 2>/dev/null || true
echo -e "${GREEN}✓ Cleanup complete${NC}"
# Build and start services
echo -e "${BLUE}[4/6]${NC} Building and starting services..."
echo -e "${YELLOW}This may take a few minutes on first run...${NC}"
$DOCKER_COMPOSE_CMD up -d --build
# Interactive database selection
echo -e "${BLUE}[Database Setup]${NC} Configuring database..."
echo "Do you want to use a new database or an existing one? (new/current/other)"
read -r db_choice
if [ "$db_choice" = "new" ]; then
    $DOCKER_COMPOSE_CMD exec server rm -f /app/instance/app.db
    $DOCKER_COMPOSE_CMD exec server rm -rf /app/migrations
    echo -e "${GREEN}✓ Set to use new database${NC}"
elif [ "$db_choice" = "current" ]; then
    echo -e "${YELLOW}✓ Set to use current database${NC}"
else
    echo "Enter the full path to the existing .db file:"
    read -r db_path
    if [ ! -f "$db_path" ]; then
        echo -e "${RED}✗ File not found: $db_path${NC}"
        exit 1
    fi
    $DOCKER_COMPOSE_CMD cp "$db_path" server:/app/instance/app.db
    echo -e "${GREEN}✓ Copied $db_path to ../server/instance/app.db${NC}"
fi
# initialise database
echo -e "${BLUE}[5/6]${NC} Initialising database..."
if [ ! -f ../server/instance/app.db ]; then
    if ! $DOCKER_COMPOSE_CMD exec server flask db init 2>/dev/null; then
        echo -e "${YELLOW}Database migrations already initialised${NC}"
    fi
    $DOCKER_COMPOSE_CMD exec server flask db migrate -m "Initial migration" || {
        echo -e "${RED}✗ Migration failed, resetting database...${NC}"
        $DOCKER_COMPOSE_CMD exec server flask reset-db
        $DOCKER_COMPOSE_CMD exec server flask db init
        $DOCKER_COMPOSE_CMD exec server flask db migrate -m "Initial migration"
    }
    $DOCKER_COMPOSE_CMD exec server flask db upgrade
    $DOCKER_COMPOSE_CMD exec server flask init-db
else
    echo -e "${YELLOW}Database already exists, attempting to upgrade...${NC}"
    $DOCKER_COMPOSE_CMD exec server flask db upgrade || {
        echo -e "${RED}✗ Upgrade failed, resetting database...${NC}"
        $DOCKER_COMPOSE_CMD exec server flask reset-db
        $DOCKER_COMPOSE_CMD exec server flask db init
        $DOCKER_COMPOSE_CMD exec server flask db migrate -m "Initial migration"
        $DOCKER_COMPOSE_CMD exec server flask db upgrade
        $DOCKER_COMPOSE_CMD exec server flask init-db
    }
fi
# Interactive admin user creation
echo -e "${BLUE}[Admin Setup]${NC} Do you want to create an admin user? (y/n)"
read -r admin_choice
if [ "$admin_choice" = "y" ]; then
    echo -n "Enter username: "
    read -r admin_user
    echo -n "Enter email: "
    read -r admin_email
    echo -n "Enter password: "
    read -r -s admin_pass # -s for silent input
    echo ""
    $DOCKER_COMPOSE_CMD exec -T server flask create-admin << EOF
$admin_user
$admin_email
$admin_pass
EOF
    echo -e "${GREEN}✓ Admin user created${NC}"
else
    echo -e "${YELLOW}Skipping admin user creation${NC}"
fi
echo -e "${GREEN}✓ Database initialised${NC}"
# Wait for server to be ready
echo -e "${BLUE}[6/6]${NC} Waiting for server to start..."
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
echo -e "║                       Environment Ready!                       ║"
echo -e "╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN} Service Status:${NC}"
$DOCKER_COMPOSE_CMD ps
echo ""
echo -e "${CYAN}🌐 Access Points:${NC}"
echo -e " ${GREEN}•${NC} Web Interface: ${YELLOW}http://localhost:5000${NC}"
echo -e " ${GREEN}•${NC} Port Changer Interface: ${YELLOW}http://localhost:5001${NC}"
echo ""
# Enter interactive mode
enter_interactive_mode