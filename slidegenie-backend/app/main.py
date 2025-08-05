"""
SlideGenie API - Main application entry point.
"""
import time
from contextlib import asynccontextmanager
from typing import Any, Dict

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from structlog.contextvars import bind_contextvars, clear_contextvars

from app.api.router import api_router
from app.api.middleware import setup_middleware
from app.core.config import settings
from app.core.logging import get_logger, log_request_details, setup_logging
from app.infrastructure.database.base import engine

# Setup logging
setup_logging()
logger = get_logger(__name__)


# Initialize Sentry if configured
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.SENTRY_ENVIRONMENT or settings.ENVIRONMENT,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        integrations=[
            SqlalchemyIntegration(),
        ],
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    """
    # Startup
    logger.info(
        "Starting SlideGenie API",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )
    
    # Initialize database
    # Note: In production, use Alembic migrations instead
    if settings.is_development:
        try:
            from app.infrastructure.database.base import Base
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        except Exception as e:
            logger.warning(f"Database initialization skipped: {e}")
            logger.info("Running without database - some features may be unavailable")
    
    yield
    
    # Shutdown
    logger.info("Shutting down SlideGenie API")
    try:
        await engine.dispose()
    except Exception as e:
        logger.warning(f"Error during engine disposal: {e}")


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.APP_VERSION,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json" if not settings.is_production else None,
    docs_url=f"{settings.API_V1_PREFIX}/docs" if not settings.is_production else None,
    redoc_url=f"{settings.API_V1_PREFIX}/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

# Setup comprehensive middleware stack
setup_middleware(app)


# Add Sentry middleware if configured
if settings.SENTRY_DSN:
    app.add_middleware(SentryAsgiMiddleware)


# Note: Exception handling is now managed by middleware


# Basic health check endpoint (more comprehensive health checks are in the API router)
@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.
    
    Returns:
        Health status and application info
    """
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# Root endpoint
@app.get("/")
async def root() -> Dict[str, str]:
    """
    Root endpoint.
    
    Returns:
        API information
    """
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": f"{settings.API_V1_PREFIX}/docs" if not settings.is_production else "Disabled in production",
    }