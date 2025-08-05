#!/bin/bash

echo "Starting SlideGenie Frontend..."
echo "==============================="
echo ""
echo "Frontend will be available at: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Navigate to frontend directory
cd /Users/basantabaral/Desktop/slidegenie/slidegenie-frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Start the frontend
npm run dev