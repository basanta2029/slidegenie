#!/bin/bash

echo "Starting SlideGenie Backend..."
echo "================================"
echo ""
echo "Backend will be available at: http://localhost:8000"
echo "API docs will be at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the backend server
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000