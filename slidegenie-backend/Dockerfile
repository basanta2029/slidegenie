# Multi-stage optimized Dockerfile for SlideGenie
# ==============================================

# Build stage - Full Python environment for building dependencies
FROM python:3.11-slim as builder

# Metadata and labels
LABEL maintainer="SlideGenie Team"
LABEL version="1.0.0"
LABEL description="AI-powered academic presentation generator"
LABEL org.opencontainers.image.title="SlideGenie Backend"
LABEL org.opencontainers.image.description="Optimized container for SlideGenie backend service"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.created="2025-07-30"

# Build arguments for customization
ARG POETRY_VERSION=1.8.2
ARG PYTHONPATH=/app
ARG BUILD_DATE
ARG VCS_REF

# Environment variables for Python optimization
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=$PYTHONPATH \
    POETRY_VERSION=$POETRY_VERSION \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=true \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    POETRY_CACHE_DIR=/opt/poetry-cache \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Add poetry to PATH
ENV PATH="$POETRY_HOME/bin:$PATH"

# Create application directory and user
RUN groupadd -r slidegenie && useradd -r -g slidegenie -m -d /app slidegenie

# Install system dependencies required for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    pkg-config \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf2.0-dev \
    libffi-dev \
    shared-mime-info \
    libxml2-dev \
    libxslt1-dev \
    libjpeg-dev \
    libpng-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7-dev \
    libtiff5-dev \
    libwebp-dev \
    libmagic1 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - \
    && chmod +x $POETRY_HOME/bin/poetry

WORKDIR /app

# Copy dependency files with proper ownership
COPY --chown=slidegenie:slidegenie pyproject.toml poetry.lock ./

# Install dependencies to virtual environment
RUN poetry install --only=main --no-root && rm -rf $POETRY_CACHE_DIR

# ==============================================
# Production stage - Minimal runtime environment
FROM python:3.11-slim as production

# Metadata
LABEL stage="production"

# Build arguments
ARG BUILD_DATE
ARG VCS_REF

# Environment variables for runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/app/.venv/bin:$PATH" \
    DEBIAN_FRONTEND=noninteractive

# Create non-root user and group
RUN groupadd -r slidegenie && useradd -r -g slidegenie -m -d /app slidegenie

# Install only runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi8 \
    shared-mime-info \
    libxml2 \
    libxslt1.1 \
    libjpeg62-turbo \
    libpng16-16 \
    libfreetype6 \
    liblcms2-2 \
    libopenjp2-7 \
    libtiff5 \
    libwebp7 \
    libmagic1 \
    poppler-utils \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder --chown=slidegenie:slidegenie /app/.venv /app/.venv

# Copy application code
COPY --chown=slidegenie:slidegenie . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/uploads /app/exports /app/temp \
    && chown -R slidegenie:slidegenie /app \
    && chmod -R 755 /app \
    && chmod -R 777 /app/logs /app/uploads /app/exports /app/temp

# Install the application using Poetry from venv
RUN /app/.venv/bin/poetry install --only-root

# Security hardening
RUN find /app -type f -name "*.py" -exec chmod 644 {} \; \
    && find /app -type d -exec chmod 755 {} \; \
    && chmod +x /app/.venv/bin/*

# Switch to non-root user
USER slidegenie

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default production command with optimized settings
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--access-log", "--log-level", "info"]

# ==============================================
# Development stage - includes dev dependencies
FROM builder as development

LABEL stage="development"

# Install development dependencies
RUN poetry install --no-root

# Copy application code
COPY --chown=slidegenie:slidegenie . .

# Install application
RUN poetry install --only-root

# Create directories
RUN mkdir -p /app/logs /app/uploads /app/exports /app/temp \
    && chown -R slidegenie:slidegenie /app \
    && chmod -R 755 /app \
    && chmod -R 777 /app/logs /app/uploads /app/exports /app/temp

# Switch to non-root user
USER slidegenie

# Expose port
EXPOSE 8000

# Development command with hot reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-level", "debug"]

# ==============================================
# Testing stage for CI/CD
FROM development as testing

LABEL stage="testing"

USER root

# Install additional testing tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

USER slidegenie

# Run tests by default
CMD ["python", "-m", "pytest", "-v", "--cov=app", "--cov-report=term-missing"]