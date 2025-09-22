#!/bin/bash

echo "Starting App..."

# Kill any existing processes
pkill -f "python.*server" || true

# Start backend
echo "🐍 Starting server..."
cd server
source venv/bin/activate
python run.py &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 3

echo "Services started!"
echo "Web Application: http://localhost:5000"
echo "Backend API: http://localhost:5000/api"
echo "API Docs: http://localhost:5000/docs"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait and cleanup on exit
trap 'echo "Stopping services..."; kill $BACKEND_PID 2>/dev/null; exit' INT
wait
