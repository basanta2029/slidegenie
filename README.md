# SlideGenie

> Transform Research into Presentations in Minutes, Not Hours

SlideGenie is an AI-powered platform that automatically transforms research papers, abstracts, and ideas into professional, citation-compliant academic presentations.

## 🌟 Features

- **AI-Powered Generation**: Leverage OpenAI and Anthropic APIs to create high-quality presentations
- **Multiple Input Formats**: Support for PDF, DOCX, LaTeX, and plain text
- **Academic Templates**: Pre-built templates for conferences, lectures, and thesis defenses
- **Export Options**: PowerPoint, PDF, Beamer (LaTeX), and Google Slides
- **Real-time Collaboration**: WebSocket-based real-time editing
- **Citation Management**: Automatic citation formatting and bibliography generation
- **Quality Assurance**: Built-in checks for academic standards and consistency

## 🏗️ Architecture

This is a monorepo containing two main applications:

```
slidegenie/
├── slidegenie-backend/    # FastAPI backend with Python/Poetry
├── slidegenie-frontend/   # Next.js frontend with TypeScript
└── package.json          # Root monorepo scripts
```

## 🚀 Quick Start

### Prerequisites

- **Node.js** 18+ and npm 9+
- **Python** 3.11+
- **Poetry** (Python package manager)
- **Docker** and Docker Compose
- **Git**

### Initial Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/slidegenie.git
   cd slidegenie
   ```

2. **Install root dependencies**
   ```bash
   npm install
   ```

3. **Set up environment variables**
   ```bash
   # Backend
   cp slidegenie-backend/.env.example slidegenie-backend/.env
   
   # Frontend
   cp slidegenie-frontend/.env.example slidegenie-frontend/.env.local
   ```
   
   Edit both `.env` files with your configuration (API keys, etc.)

4. **Start the development environment**
   ```bash
   # Start Docker services (PostgreSQL, Redis, MinIO)
   npm run docker:up
   
   # Run database migrations
   npm run setup:backend
   
   # Install all dependencies
   npm run install
   
   # Start both frontend and backend
   npm run dev
   ```

The applications will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/api/v1/docs

## 📚 Documentation

- [Backend Documentation](./slidegenie-backend/README.md)
- [Frontend Documentation](./slidegenie-frontend/README.md)
- [API Documentation](http://localhost:8000/api/v1/docs) (when running)
- [Product Requirements Document](./PRD.md)

## 🛠️ Development

### Available Commands

From the root directory:

```bash
# Development
npm run dev              # Start both frontend and backend
npm run dev:backend      # Start backend only
npm run dev:frontend     # Start frontend only

# Docker
npm run docker:up        # Start Docker services
npm run docker:down      # Stop Docker services
npm run docker:logs      # View Docker logs

# Testing
npm run test            # Run all tests
npm run test:backend    # Run backend tests
npm run test:frontend   # Run frontend tests

# Code Quality
npm run lint            # Run linters
npm run format          # Format code

# Utilities
npm run clean           # Clean build artifacts
npm run setup           # Full setup (Docker + migrations + install)
```

### Project Structure

#### Backend (FastAPI + Python)
- Clean architecture with separation of concerns
- Async/await throughout
- PostgreSQL with pgvector for semantic search
- Redis for caching and rate limiting
- MinIO for file storage
- Celery for background tasks

#### Frontend (Next.js + TypeScript)
- App Router (Next.js 14+)
- Tailwind CSS + shadcn/ui components
- Zustand for state management
- TanStack Query for data fetching
- Socket.io for real-time features

## 🔧 Configuration

### Required API Keys

You'll need at least one AI provider API key:
- **OpenAI API Key** (for GPT models)
- **Anthropic API Key** (for Claude models)

### Optional Integrations

- **OAuth Providers**: Google, Microsoft
- **Email Service**: SMTP configuration
- **Error Tracking**: Sentry
- **Analytics**: Google Analytics, Mixpanel

## 🧪 Testing

```bash
# Run all tests with coverage
npm run test

# Run specific test suites
cd slidegenie-backend && make test-unit
cd slidegenie-backend && make test-integration
cd slidegenie-frontend && npm test
```

## 🚢 Deployment

### Using Docker

1. Build production images:
   ```bash
   cd slidegenie-backend && docker build -t slidegenie-backend .
   cd slidegenie-frontend && docker build -t slidegenie-frontend .
   ```

2. Use `docker-compose.prod.yml` for production deployment

### Using Kubernetes

Kubernetes manifests are available in `slidegenie-backend/k8s/`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is proprietary software. All rights reserved.

## 🆘 Troubleshooting

### Common Issues

1. **Poetry not found**
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. **Database connection errors**
   - Ensure Docker services are running: `npm run docker:logs`
   - Check PostgreSQL is healthy: `docker ps`

3. **Frontend can't connect to backend**
   - Verify CORS settings in backend `.env`
   - Check `NEXT_PUBLIC_API_URL` in frontend `.env.local`

4. **AI generation not working**
   - Verify API keys are set correctly
   - Check rate limits haven't been exceeded

## 📞 Support

For issues and questions:
- Check existing [GitHub Issues](https://github.com/yourusername/slidegenie/issues)
- Review the [documentation](./docs/)
- Contact the development team

---

Built with ❤️ by the SlideGenie Team