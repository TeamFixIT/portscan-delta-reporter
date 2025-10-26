#!/bin/bash
# Port Scanner Delta Reporter - Start Script

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
else
    echo "Error: Virtual environment not found. Run ./setup_client.sh first."
    exit 1
fi

# Check if database exists
if [ ! -f "data/app.db" ]; then
    echo "Error: Database not found. Run ./setup_app.sh first."
    exit 1
fi

# Start the server
echo "Starting Port Scanner Delta Reporter..."
portscanner-server