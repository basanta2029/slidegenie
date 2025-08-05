# SlideGenie Startup Guide

## Prerequisites
- Python 3.11+ with Poetry installed
- Node.js 18+ and npm
- Docker and Docker Compose
- Valid API keys for OpenAI and/or Anthropic

## Quick Start

### 1. Backend Setup

```bash
cd slidegenie-backend

# Install Python dependencies
poetry install

# Start Docker services (PostgreSQL, Redis, MinIO)
make docker-up

# Wait for services to be healthy (check with)
docker-compose ps

# Run database migrations
make migrate

# Start the backend server
make run
```

The backend will be available at http://localhost:8000
API documentation at http://localhost:8000/docs

### 2. Frontend Setup

Open a new terminal:

```bash
cd slidegenie-frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

The frontend will be available at http://localhost:3000

## Important Notes

### API Keys
The application requires valid API keys to function properly:
- **OpenAI API Key**: Get from https://platform.openai.com/api-keys
- **Anthropic API Key**: Get from https://console.anthropic.com/

Update these in `slidegenie-backend/.env`:
- `OPENAI_API_KEY=your-actual-key`
- `ANTHROPIC_API_KEY=your-actual-key`

### Docker Services
- **PostgreSQL**: Port 5432 (user: basanta1, password: 1234567890Sb.@)
- **Redis**: Port 6379 (password: 1234567890Sb.@)
- **MinIO**: Port 9000 (API), 9001 (Console)
  - Console: http://localhost:9001
  - Default credentials: minioadmin/minioadmin

### Troubleshooting

#### If Docker services fail to start:
```bash
# Check logs
make docker-logs

# Clean and restart
make docker-clean
make docker-up
```

#### If migrations fail:
```bash
# Check database connection
docker-compose exec postgres psql -U basanta1 -d slidegenie

# Manually create database if needed
CREATE DATABASE slidegenie;
```

#### If frontend can't connect to backend:
- Ensure backend is running on port 8000
- Check CORS settings in backend .env
- Verify `NEXT_PUBLIC_API_URL` in frontend .env.local

## Development Commands

### Backend
```bash
make help           # Show all available commands
make test          # Run tests
make format        # Format code
make lint          # Run linter
make docker-logs   # View Docker logs
```

### Frontend
```bash
npm run dev        # Start development server
npm run build      # Build for production
npm run lint       # Run linter
npm test          # Run tests
```

## Stopping Services

```bash
# Backend
make docker-down   # Stop Docker services
# Press Ctrl+C to stop the backend server

# Frontend
# Press Ctrl+C to stop the frontend server
```