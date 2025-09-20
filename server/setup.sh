#!/bin/bash
# Setup script for the server environment

echo "Setting up Port Scanner Server environment..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing server dependencies..."
pip install -r requirements.txt

# Initialize database
echo "Initializing database..."
python run.py init-db

echo "Server setup complete!"
echo ""
echo "To start the server:"
echo "  source venv/bin/activate"
echo "  python run.py"