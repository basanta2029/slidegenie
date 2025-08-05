#!/bin/bash

echo "Starting SlideGenie Application"
echo "==============================="
echo ""
echo "This script will start both backend and frontend servers."
echo ""
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all servers"
echo ""

# Function to handle cleanup
cleanup() {
    echo ""
    echo "Stopping servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}

# Set up trap to call cleanup on script exit
trap cleanup EXIT INT TERM

# Start Backend
echo "Starting Backend Server..."
cd /Users/basantabaral/Desktop/slidegenie/slidegenie-backend
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "Backend started with PID: $BACKEND_PID"

# Wait a bit for backend to start
sleep 3

# Start Frontend
echo ""
echo "Starting Frontend Server..."
cd /Users/basantabaral/Desktop/slidegenie/slidegenie-frontend
npm run dev &
FRONTEND_PID=$!
echo "Frontend started with PID: $FRONTEND_PID"

echo ""
echo "Both servers are running!"
echo ""
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo ""

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID