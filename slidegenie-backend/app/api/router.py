"""
Main API router with comprehensive endpoint integration and monitoring.

This module provides the main API router that integrates all endpoints with:
- Comprehensive error handling
- Request/response validation
- API metrics collection
- Health monitoring
- Rate limiting integration
- Authentication integration
"""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import generate_latest

from app.api.dependencies import (
    get_api_version,
    get_current_admin_user,
    get_pagination_params,
    PaginationParams,
)
from app.api.exceptions import (
    APIException,
    HealthCheckException,
    MaintenanceException,
)
from app.api.middleware import get_metrics
from app.api.v1.endpoints import (
    academic,
    # admin,  # TODO: Fix decorator issues
    # analytics,  # TODO: Fix decorator issues
    auth,
    document_upload,
    export,
    generation,
    health,
    oauth,
    presentations,
    realtime,
    slides,
    templates,
    users,
    websocket,
)
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.database.models import User

logger = get_logger(__name__)

# Create main API router
api_router = APIRouter()

# API Information endpoint
@api_router.get(
    "/",
    summary="API Information",
    description="Get basic API information and available endpoints",
    response_model=Dict[str, Any],
    tags=["api-info"],
)
async def api_info(
    request: Request,
    api_version: str = Depends(get_api_version),
) -> Dict[str, Any]:
    """
    Get API information and available endpoints.
    
    Returns:
        API information including version, endpoints, and documentation links
    """
    base_url = str(request.base_url).rstrip("/")
    api_prefix = settings.API_V1_PREFIX
    
    endpoints = {
        "authentication": f"{base_url}{api_prefix}/auth",
        "oauth": f"{base_url}{api_prefix}/oauth",
        "users": f"{base_url}{api_prefix}/users",
        "presentations": f"{base_url}{api_prefix}/presentations",
        "templates": f"{base_url}{api_prefix}/templates",
        "generation": f"{base_url}{api_prefix}/generation",
        "slides": f"{base_url}{api_prefix}/slides",
        "documents": f"{base_url}{api_prefix}/documents",
        "export": f"{base_url}{api_prefix}/export",
        "analytics": f"{base_url}{api_prefix}/analytics",
        "realtime": f"{base_url}{api_prefix}/realtime",
        "websocket": f"{base_url}{api_prefix}/ws",
        "health": f"{base_url}{api_prefix}/health",
    }
    
    # Admin endpoints (only show to admin users)
    try:
        admin_user = await get_current_admin_user()
        if admin_user:
            endpoints["admin"] = f"{base_url}{api_prefix}/admin"
    except:
        pass  # Not an admin user or not authenticated
    
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.APP_VERSION,
        "api_version": api_version,
        "environment": settings.ENVIRONMENT,
        "endpoints": endpoints,
        "documentation": {
            "openapi": f"{base_url}{api_prefix}/openapi.json" if not settings.is_production else None,
            "swagger_ui": f"{base_url}{api_prefix}/docs" if not settings.is_production else None,
            "redoc": f"{base_url}{api_prefix}/redoc" if not settings.is_production else None,
        },
        "features": {
            "websocket_support": True,
            "realtime_collaboration": settings.ENABLE_COLLABORATION,
            "ai_generation": True,
            "multiple_export_formats": True,
            "academic_templates": True,
            "oauth_providers": ["google", "microsoft"],
        },
        "limits": {
            "max_file_size_mb": settings.MAX_UPLOAD_SIZE_MB,
            "supported_file_types": settings.ALLOWED_UPLOAD_EXTENSIONS,
            "max_slides_per_presentation": settings.MAX_SLIDES_PER_PRESENTATION,
        },
    }


# API Status endpoint
@api_router.get(
    "/status",
    summary="API Status",
    description="Get detailed API status including component health",
    response_model=Dict[str, Any],
    tags=["api-info"],
)
async def api_status() -> Dict[str, Any]:
    """
    Get detailed API status including component health.
    
    Returns:
        Comprehensive API status information
    """
    try:
        # Import here to avoid circular imports
        from app.infrastructure.cache.redis import get_redis
        from app.infrastructure.database.base import get_db
        from sqlalchemy import text
        
        components = {
            "api": {"status": "healthy", "details": "API server running"},
            "database": {"status": "unknown", "details": "Checking..."},
            "cache": {"status": "unknown", "details": "Checking..."},
            "ai_services": {"status": "unknown", "details": "Checking..."},
        }
        
        # Check database
        try:
            async for db in get_db():
                result = await db.execute(text("SELECT 1"))
                result.scalar()
                components["database"] = {
                    "status": "healthy",
                    "details": "Database connection successful"
                }
                break
        except Exception as e:
            components["database"] = {
                "status": "unhealthy",
                "details": f"Database connection failed: {str(e)}"
            }
        
        # Check Redis
        try:
            redis_client = await get_redis()
            await redis_client.ping()
            components["cache"] = {
                "status": "healthy",
                "details": "Redis connection successful"
            }
        except Exception as e:
            components["cache"] = {
                "status": "unhealthy",
                "details": f"Redis connection failed: {str(e)}"
            }
        
        # Check AI services
        ai_config = settings.get_ai_config()
        if ai_config["has_anthropic"] or ai_config["has_openai"]:
            components["ai_services"] = {
                "status": "healthy",
                "details": f"AI providers available: "
                          f"{'Anthropic' if ai_config['has_anthropic'] else ''}"
                          f"{', ' if ai_config['has_anthropic'] and ai_config['has_openai'] else ''}"
                          f"{'OpenAI' if ai_config['has_openai'] else ''}"
            }
        else:
            components["ai_services"] = {
                "status": "degraded",
                "details": "No AI providers configured"
            }
        
        # Overall status
        all_healthy = all(
            comp["status"] == "healthy" 
            for comp in components.values()
        )
        
        any_degraded = any(
            comp["status"] == "degraded" 
            for comp in components.values()
        )
        
        overall_status = "healthy" if all_healthy else ("degraded" if any_degraded else "unhealthy")
        
        return {
            "status": overall_status,
            "timestamp": int(__import__("time").time()),
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "components": components,
            "uptime_seconds": int(__import__("time").time()),  # Simplified uptime
        }
        
    except Exception as e:
        logger.error("Status check failed", exc_info=e)
        raise HealthCheckException(
            component="api",
            detail=str(e),
        )


# Metrics endpoint (for monitoring systems)
@api_router.get(
    "/metrics",
    summary="Prometheus Metrics",
    description="Get Prometheus metrics for monitoring",
    response_class=PlainTextResponse,
    tags=["monitoring"],
)
async def get_prometheus_metrics() -> Response:
    """
    Get Prometheus metrics for monitoring systems.
    
    Returns:
        Prometheus metrics in text format
    """
    return await get_metrics()


# API Limits endpoint
@api_router.get(
    "/limits",
    summary="API Limits",
    description="Get current API limits and quotas",
    response_model=Dict[str, Any],
    tags=["api-info"],
)
async def api_limits() -> Dict[str, Any]:
    """
    Get current API limits and quotas.
    
    Returns:
        API limits and quota information
    """
    return {
        "rate_limits": {
            "requests_per_minute": {
                "default": 100,
                "authenticated": 200,
                "premium": 500,
            },
            "file_upload": {
                "requests_per_minute": 10,
                "max_file_size_mb": settings.MAX_UPLOAD_SIZE_MB,
            },
            "ai_generation": {
                "requests_per_minute": 5,
                "premium_requests_per_minute": 20,
            },
        },
        "quotas": {
            "free_tier": {
                "presentations_per_month": settings.FREE_TIER_PRESENTATIONS_PER_MONTH,
                "storage_mb": settings.FREE_TIER_STORAGE_MB,
            },
            "premium_tier": {
                "presentations_per_month": "unlimited",
                "storage_gb": 10,
            },
        },
        "file_limits": {
            "max_upload_size_mb": settings.MAX_UPLOAD_SIZE_MB,
            "supported_extensions": settings.ALLOWED_UPLOAD_EXTENSIONS,
            "max_files_per_upload": 10,
        },
        "presentation_limits": {
            "max_slides": settings.MAX_SLIDES_PER_PRESENTATION,
            "max_title_length": 200,
            "max_content_length": 10000,
        },
    }


# Maintenance endpoint (admin only)
@api_router.post(
    "/maintenance",
    summary="Toggle Maintenance Mode",
    description="Enable or disable maintenance mode (admin only)",
    response_model=Dict[str, Any],
    tags=["admin"],
)
async def toggle_maintenance(
    enable: bool,
    message: str = "Service temporarily unavailable for maintenance",
    admin_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Toggle maintenance mode.
    
    Args:
        enable: Whether to enable maintenance mode
        message: Maintenance message to display
        admin_user: Admin user (from dependency)
        
    Returns:
        Maintenance mode status
    """
    # In a real implementation, this would set a flag in Redis or database
    # For now, we'll just return the status
    
    logger.info(
        f"Maintenance mode {'enabled' if enable else 'disabled'} by admin",
        admin_id=str(admin_user.id),
        message=message,
    )
    
    return {
        "maintenance_mode": enable,
        "message": message if enable else "Service is operational",
        "enabled_by": str(admin_user.id),
        "timestamp": int(__import__("time").time()),
    }


# Include all endpoint routers with proper configuration
def setup_api_routes() -> APIRouter:
    """
    Setup and configure all API routes.
    
    Returns:
        Configured API router
    """
    # Health and monitoring endpoints (no authentication required)
    api_router.include_router(
        health.router,
        prefix="/health",
        tags=["health"],
    )
    
    # Authentication endpoints
    api_router.include_router(
        auth.router,
        prefix="/auth",
        tags=["authentication"],
    )
    
    # OAuth endpoints
    api_router.include_router(
        oauth.router,
        prefix="/oauth",
        tags=["oauth"],
    )
    
    # Academic validation endpoints
    api_router.include_router(
        academic.router,
        prefix="/academic",
        tags=["academic"],
    )
    
    # User management endpoints
    api_router.include_router(
        users.router,
        prefix="/users",
        tags=["users"],
    )
    
    # Presentation management endpoints
    api_router.include_router(
        presentations.router,
        prefix="/presentations",
        tags=["presentations"],
    )
    
    # Template management endpoints
    api_router.include_router(
        templates.router,
        prefix="/templates",
        tags=["templates"],
    )
    
    # AI generation endpoints
    api_router.include_router(
        generation.router,
        prefix="/generation",
        tags=["generation"],
    )
    
    # Slide management endpoints
    api_router.include_router(
        slides.router,
        prefix="/slides",
        tags=["slides"],
    )
    
    # Document upload endpoints
    api_router.include_router(
        document_upload.router,
        prefix="/documents/upload",
        tags=["document-upload"],
    )
    
    # Export endpoints
    api_router.include_router(
        export.router,
        prefix="/export",
        tags=["export"],
    )
    
    # Real-time collaboration endpoints
    api_router.include_router(
        realtime.router,
        prefix="/realtime",
        tags=["realtime"],
    )
    
    # WebSocket endpoints
    api_router.include_router(
        websocket.router,
        prefix="/ws",
        tags=["websocket"],
    )
    
    # Analytics endpoints
    # api_router.include_router(
    #     analytics.router,  # TODO: Fix decorator issues
    #     prefix="/analytics",
    #     tags=["analytics"],
    # )
    
    # Admin endpoints (requires admin authentication)
    # api_router.include_router(
    #     admin.router,  # TODO: Fix decorator issues
    #     prefix="/admin",
    #     tags=["admin"],
    # )
    
    return api_router


# Setup routes
setup_api_routes()


# Global exception handlers for the API router
# # NOTE: Exception handlers should be added at the app level in main.py, not on routers
# # @api_router.exception_handler(APIException)
# # async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
#     """
#     Handle API exceptions with consistent formatting.
#     
#     Args:
#         request: FastAPI request
#         exc: API exception
#         
#     Returns:
#         JSON response with error details
#     """
#     logger.warning(
#         "API exception occurred",
#         error_code=exc.error_code,
#         status_code=exc.status_code,
#         detail=exc.detail,
#         path=request.url.path,
#         method=request.method,
#     )
#     
#     return JSONResponse(
#         status_code=exc.status_code,
#         content=exc.detail,
#         headers=exc.headers,
#     )
# 
# 
# @api_router.exception_handler(HTTPException)
# async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
#     """
#     Handle HTTP exceptions with consistent formatting.
#     
#     Args:
#         request: FastAPI request
#         exc: HTTP exception
#         
#     Returns:
#         JSON response with error details
#     """
#     logger.warning(
#         "HTTP exception occurred",
#         status_code=exc.status_code,
#         detail=exc.detail,
#         path=request.url.path,
#         method=request.method,
#     )
#     
#     return JSONResponse(
#         status_code=exc.status_code,
#         content={
#             "error_code": "http_error",
#             "message": exc.detail,
#             "context": {},
#         },
#         headers=exc.headers,
#     )
# 
# 
# @api_router.exception_handler(Exception)
# async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
#     """
#     Handle unexpected exceptions.
#     
#     Args:
#         request: FastAPI request
#         exc: Unexpected exception
#         
#     Returns:
#         JSON response with error details
#     """
#     logger.error(
#         "Unexpected exception occurred",
#         exc_info=exc,
#         path=request.url.path,
#         method=request.method,
#     )
#     
#     # Don't expose internal errors in production
#     if settings.is_production:
#         return JSONResponse(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             content={
#                 "error_code": "internal_error",
#                 "message": "An internal error occurred",
#                 "context": {},
#             },
#         )
#     
#     return JSONResponse(
#         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#         content={
#             "error_code": "internal_error",
#             "message": str(exc),
#             "context": {"exception_type": type(exc).__name__},
#         },
#     )