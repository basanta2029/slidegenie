#!/bin/bash

echo "🚀 Starting SlideGenie Application"
echo "=================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if ports are free
check_port() {
    if lsof -i :$1 >/dev/null 2>&1; then
        echo -e "${RED}❌ Port $1 is already in use!${NC}"
        echo "Please stop the process using port $1 and try again."
        exit 1
    fi
}

echo "Checking ports..."
check_port 3000
check_port 8000
echo -e "${GREEN}✅ Ports are available${NC}"
echo ""

# Start Backend
echo -e "${BLUE}Starting Backend Server...${NC}"
cd /Users/basantabaral/Desktop/slidegenie/slidegenie-backend
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend started (PID: $BACKEND_PID)"
echo "Backend logs: tail -f /Users/basantabaral/Desktop/slidegenie/slidegenie-backend/backend.log"

# Wait for backend to be ready
echo -n "Waiting for backend to start"
for i in {1..30}; do
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        echo -e "\n${GREEN}✅ Backend is ready!${NC}"
        break
    fi
    echo -n "."
    sleep 1
done

# Start Frontend
echo ""
echo -e "${BLUE}Starting Frontend Server...${NC}"
cd /Users/basantabaral/Desktop/slidegenie/slidegenie-frontend
npm run dev > /Users/basantabaral/Desktop/slidegenie/slidegenie-backend/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend started (PID: $FRONTEND_PID)"
echo "Frontend logs: tail -f /Users/basantabaral/Desktop/slidegenie/slidegenie-backend/frontend.log"

# Wait for frontend to be ready
echo -n "Waiting for frontend to start"
for i in {1..30}; do
    if curl -s http://localhost:3000 >/dev/null 2>&1; then
        echo -e "\n${GREEN}✅ Frontend is ready!${NC}"
        break
    fi
    echo -n "."
    sleep 1
done

echo ""
echo -e "${GREEN}🎉 SlideGenie is running!${NC}"
echo ""
echo "📍 Access your app at:"
echo "   Frontend: http://localhost:3000"
echo "   Backend API: http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "📋 View logs:"
echo "   Backend: tail -f backend.log"
echo "   Frontend: tail -f frontend.log"
echo ""
echo "Press Ctrl+C to stop all servers"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Stopping servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
    echo "Servers stopped."
    exit 0
}

# Set up trap
trap cleanup EXIT INT TERM

# Keep script running
while true; do
    sleep 1
done