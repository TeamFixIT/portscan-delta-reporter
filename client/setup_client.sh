#!/bin/bash
# Port Scanner Client Agent - Setup Script

set -e

echo "=========================================="
echo "Port Scanner Client Agent Setup"
echo "=========================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install package
echo ""
echo "Installing package..."
pip install -e .
echo "✓ Package installed"

# Check if config.yml exists
if [ ! -f "config.yml" ]; then
    echo ""
    read -p "Would you like to run the configuration wizard? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        portscanner-client-config
    else
        if [ -f "config.example.yml" ]; then
            echo ""
            echo "Creating config.yml from config.example.yml..."
            cp config.example.yml config.yml
            echo "✓ config.yml created"
            echo ""
            echo "⚠️  IMPORTANT: Edit config.yml and configure:"
            echo "  - server_url: URL of your Port Scanner server"
            echo "  - scan_range: Network range to scan"
        else
            echo ""
            echo "⚠️  WARNING: No config.example.yml found."
            echo "Run 'portscanner-client-config' to create config.yml"
        fi
    fi
else
    echo "✓ config.yml already exists"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "To start the client agent, run:"
echo "  source venv/bin/activate"
echo "  portscanner-client"
echo ""
echo "To reconfigure, run:"
echo "  portscanner-client-config"
echo ""
echo "Or simply:"
echo "  ./start_client.sh"
echo ""