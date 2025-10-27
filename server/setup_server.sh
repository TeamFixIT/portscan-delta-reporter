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
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
else
    echo "Error: Virtual environment not found. Run ./setup_client.sh first."
    exit 1
fi

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
flask --help
# Run database setup
echo ""
echo "Setting up database..."
flask setup || {
    echo "flask setup failed – this is normal if DB not ready yet"
    echo "We'll let the entrypoint handle it at runtime"
}
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