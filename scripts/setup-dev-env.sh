#!/bin/bash
set -e

echo "🚀 Setting up Port Detector development environment..."

# Check prerequisites
check_requirements() {
    echo "📋 Checking requirements..."

    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python 3 is required but not installed"
        exit 1
    fi

    # Check Node.js
    if ! command -v node &> /dev/null; then
        echo "❌ Node.js is required but not installed"
        exit 1
    fi

    # Check Docker (optional but recommended)
    if ! command -v docker &> /dev/null; then
        echo "⚠️  Docker not found - some features may not work"
    fi

    echo "✅ Requirements check passed"
}

# Setup server
setup_server() {
    echo "🐍 Setting up server..."
    cd server

    # Create virtual environment
    python3 -m venv venv
    source venv/bin/activate

    # Install dependencies
    pip install -r requirements.txt

    # Setup database
    flask db upgrade

    echo "✅ server setup complete"
    cd ..
}

# Setup client
setup_client() {
    echo "🔍 Setting up client..."
    cd client

    # Create virtual environment
    python3 -m venv venv
    source venv/bin/activate

    # Install dependencies
    pip install -r requirements.txt

    echo "✅ Client setup complete"
    cd ..
}

# Main setup
main() {
    check_requirements
    setup_server
    setup_client

    echo ""
    echo "🎉 Setup complete! Next steps:"
    echo "1. Open the project in VS Code: code ."
    echo "2. Install recommended extensions when prompted"
    echo "3. Run: bash scripts/start-all.sh (starts all services)"
    echo ""
    echo "📚 Check docs/development/getting-started.md for detailed instructions"
}

main
