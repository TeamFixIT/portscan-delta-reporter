#!/bin/bash
set -e

# Configuration
SERVER_CONTAINER="portscan-server"
DB_PATH="/app/instance/portscan.db"
VOLUME_NAME="server_instance"

echo "Pruning database for $SERVER_CONTAINER..."

# Step 1: Stop the server container
echo "Stopping $SERVER_CONTAINER..."
docker compose stop $SERVER_CONTAINER

# Step 2: Remove the database file from the server_instance volume
echo "Removing database file from $VOLUME_NAME..."
docker run --rm -v $VOLUME_NAME:/data alpine sh -c "rm -f /data/portscan.db"

# Step 3: Restart the server to reinitialize the database
echo "Restarting $SERVER_CONTAINER..."
docker compose up -d $SERVER_CONTAINER

# Step 4: Wait for server to be healthy
echo "Waiting for $SERVER_CONTAINER to be healthy..."
timeout 60s bash -c "
until docker inspect $SERVER_CONTAINER | grep -q '\"Status\": \"healthy\"'; do
  sleep 1
  echo 'Waiting for server to be healthy...'
done
"
if [ $? -eq 0 ]; then
  echo "Database pruned and $SERVER_CONTAINER restarted successfully!"
else
  echo "Error: $SERVER_CONTAINER did not reach healthy status in time."
  exit 1
fi

echo "You may need to re-run quick-start.sh to re-register clients and initialize the system."