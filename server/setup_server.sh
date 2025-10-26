#!/bin/bash
# Port Scanner Delta Reporter - Setup Script

set -e

echo "=========================================="
echo "Port Scanner Delta Reporter Setup"
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

# Install package
echo ""
echo "Installing package..."
pip install -e .
echo "✓ Package installed"

# Check if .env exists
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo ""
        echo "Creating .env file from .env.example..."
        cp .env.example .env
        echo "✓ .env file created"
        echo ""
        echo "⚠️  IMPORTANT: Edit .env file and set SECRET_KEY and other configuration"
    else
        echo ""
        echo "⚠️  WARNING: No .env file found. Please create one with SECRET_KEY set."
    fi
else
    echo "✓ .env file already exists"
fi

# Run database setup
echo ""
echo "Setting up database..."
flask setup
echo "✓ Database setup complete"

# Prompt to create admin user
echo ""
read -p "Would you like to create an admin user now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    flask create-admin
    echo "✓ Admin user created"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "To start the server, run:"
echo "  source venv/bin/activate"
echo "  portscanner-server"
echo ""
echo "Or simply:"
echo "  ./start_server.sh"
echo ""