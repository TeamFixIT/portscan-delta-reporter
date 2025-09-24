#!/bin/bash
# Setup script for the client environment

echo "Setting up Port Scanner Client environment..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create virtual environment"
        echo "Try: python3 -m pip install --upgrade pip"
        exit 1
    fi
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing client dependencies..."
pip install -r requirements.txt

# Copy config template if config doesn't exist
if [ ! -f "config.yml" ]; then
    echo "Creating config file from template..."
    cp config.example.yml config.yml
    echo "⚠️  Please edit config.yml with your server details"
fi

echo "✅ Client setup complete!"
echo ""
echo "To start the client:"
echo "  source venv/bin/activate - on macOS/Linux"
echo "  source venv/Scripts/activate - on Windows"
echo "  python client_agent.py"
