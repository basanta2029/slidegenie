#!/bin/bash

echo "Starting SlideGenie Backend..."

# Export environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Check if Redis is available (optional)
if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        echo "✓ Redis is running"
    else
        echo "⚠ Redis is not running. Starting without Redis support (limited functionality)"
    fi
else
    echo "⚠ Redis not installed. Starting without Redis support (limited functionality)"
fi

# Use Poetry to run the server
echo "Starting server with Poetry..."
poetry run python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload