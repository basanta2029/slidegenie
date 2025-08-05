#!/bin/bash

# Setup script for SlideGenie test environment

set -e

echo "🚀 Setting up SlideGenie test environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running in CI environment
if [ -n "$CI" ]; then
    echo "Running in CI environment"
    CI_MODE=true
else
    echo "Running in local environment"
    CI_MODE=false
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to wait for service
wait_for_service() {
    local service=$1
    local port=$2
    local max_attempts=30
    local attempt=0
    
    echo "Waiting for $service on port $port..."
    
    while ! nc -z localhost $port; do
        attempt=$((attempt + 1))
        if [ $attempt -eq $max_attempts ]; then
            echo -e "${RED}❌ $service failed to start${NC}"
            return 1
        fi
        sleep 1
    done
    
    echo -e "${GREEN}✓ $service is ready${NC}"
    return 0
}

# Check prerequisites
echo "Checking prerequisites..."

if ! command_exists docker; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    exit 1
fi

if ! command_exists docker-compose; then
    echo -e "${RED}❌ Docker Compose is not installed${NC}"
    exit 1
fi

if ! command_exists python3; then
    echo -e "${RED}❌ Python 3 is not installed${NC}"
    exit 1
fi

if ! command_exists poetry; then
    echo -e "${YELLOW}⚠️  Poetry is not installed. Installing...${NC}"
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
fi

echo -e "${GREEN}✓ All prerequisites installed${NC}"

# Load environment variables
if [ -f .env.test ]; then
    echo "Loading test environment variables..."
    export $(cat .env.test | grep -v '^#' | xargs)
else
    echo -e "${YELLOW}⚠️  .env.test not found, using defaults${NC}"
    
    # Set default test environment variables
    export DATABASE_URL="postgresql://slidegenie_test:testpass123@localhost:5433/slidegenie_test"
    export REDIS_URL="redis://localhost:6380"
    export MINIO_ENDPOINT="localhost:9001"
    export MINIO_ACCESS_KEY="minioadmin"
    export MINIO_SECRET_KEY="minioadmin123"
    export TESTING="true"
fi

# Start test services
echo "Starting test services..."
docker-compose -f tests/docker-compose.test.yml up -d postgres-test redis-test minio-test

# Wait for services to be ready
wait_for_service "PostgreSQL" 5433
wait_for_service "Redis" 6380
wait_for_service "MinIO" 9001

# Create test database if it doesn't exist
echo "Setting up test database..."
PGPASSWORD=testpass123 psql -h localhost -p 5433 -U slidegenie_test -d postgres -c "SELECT 1 FROM pg_database WHERE datname = 'slidegenie_test'" | grep -q 1 || \
PGPASSWORD=testpass123 psql -h localhost -p 5433 -U slidegenie_test -d postgres -c "CREATE DATABASE slidegenie_test"

# Run database migrations
echo "Running database migrations..."
poetry run alembic upgrade head

# Create MinIO test bucket
echo "Setting up MinIO test bucket..."
docker run --rm --network slidegenie-test-network \
    -e MC_HOST_minio=http://minioadmin:minioadmin123@minio-test:9000 \
    minio/mc:latest \
    mb minio/test-uploads --ignore-existing

# Install test dependencies
echo "Installing test dependencies..."
poetry install --with dev

# Create test data directories
echo "Creating test data directories..."
mkdir -p tests/fixtures/files/uploads
mkdir -p tests/fixtures/files/exports
mkdir -p tests/results
mkdir -p tests/coverage
mkdir -p tests/performance/results

# Generate test fixtures
echo "Generating test fixtures..."
poetry run python tests/scripts/generate_fixtures.py

# Verify setup
echo "Verifying test environment..."
poetry run python tests/scripts/verify_setup.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Test environment setup complete!${NC}"
    echo ""
    echo "You can now run tests with:"
    echo "  poetry run pytest                    # Run all tests"
    echo "  poetry run pytest tests/unit         # Run unit tests only"
    echo "  poetry run pytest tests/integration  # Run integration tests only"
    echo "  poetry run pytest tests/e2e          # Run E2E tests only"
    echo ""
    echo "To stop test services:"
    echo "  docker-compose -f tests/docker-compose.test.yml down"
else
    echo -e "${RED}❌ Test environment setup failed!${NC}"
    exit 1
fi