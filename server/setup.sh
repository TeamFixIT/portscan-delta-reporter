#!/bin/bash
# Setup script for the server environment
# Works on macOS, Linux, and WSL

echo "Setting up Port Scanner Server environment..."

# Check if Python3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed or not in PATH"
    echo "Please install Python 3.8+ first"
    exit 1
fi

echo "Using Python version: $(python3 --version)"

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

# Install dependencies with fallback
echo "Installing server dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Warning: Failed to install from requirements.txt"
    echo "Trying flexible requirements..."
    pip install -r requirements-flexible.txt
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install dependencies"
        echo "Please check the error messages above and install missing system dependencies"
        exit 1
    fi
fi

# Initialize database
echo "Initializing database..."
python run.py init-db

echo "Server setup complete!"
echo ""
echo "To start the server:"
echo "  source venv/bin/activate"
echo "  python run.py"
