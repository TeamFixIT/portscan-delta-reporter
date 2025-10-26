#!/bin/bash
# Port Scanner Client Agent - Start Script

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
else
    echo "Error: Virtual environment not found. Run ./setup_client.sh first."
    exit 1
fi

# Check if config exists
if [ ! -f "config.yml" ]; then
    echo "Error: config.yml not found. Run ./setup_client.sh first."
    exit 1
fi

# Start the client
echo "Starting Port Scanner Client Agent..."
portscanner-client