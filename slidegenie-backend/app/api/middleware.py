"""
Comprehensive middleware stack for the SlideGenie API.

This module provides a complete set of middleware components including:
- API versioning support
- CORS handling
- Rate limiting
- Request/response logging
- Error handling
- Request/response validation
- API metrics collection
- Security headers
"""

import asyncio
import json
import time
import uuid
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import RequestResponseEndpoint
from structlog.contextvars import bind_contextvars, clear_contextvars

from app.core.config import settings
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    RateLimitError,
    SlideGenieException,
    ValidationError,
)
from app.core.logging import get_logger
from app.infrastructure.cache.redis import get_redis

logger = get_logger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code', 'version']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint', 'version']
)

RATE_LIMIT_HITS = Counter(
    'rate_limit_hits_total',
    'Total rate limit hits',
    ['endpoint', 'client_ip']
)

ERROR_COUNT = Counter(
    'http_errors_total',
    'Total HTTP errors',
    ['status_code', 'endpoint']
)


class APIVersioningMiddleware(BaseHTTPMiddleware):
    """
    API versioning middleware supporting both header and URL-based versioning.
    
    Supports:
    - URL versioning: /api/v1/endpoint
    - Header versioning: API-Version: v1
    - Accept header versioning: application/vnd.api+json;version=1
    """
    
    def __init__(self, app: FastAPI, default_version: str = "v1"):
        super().__init__(app)
        self.default_version = default_version
        self.supported_versions = ["v1"]  # Add new versions here
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process API versioning."""
        version = self._extract_version(request)
        
        # Validate version
        if version not in self.supported_versions:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "unsupported_version",
                    "message": f"API version '{version}' is not supported",
                    "supported_versions": self.supported_versions
                }
            )
        
        # Store version in request state
        request.state.api_version = version
        
        # Add version to response headers
        response = await call_next(request)
        response.headers["API-Version"] = version
        response.headers["Supported-Versions"] = ",".join(self.supported_versions)
        
        return response
    
    def _extract_version(self, request: Request) -> str:
        """Extract API version from request."""
        # 1. Check URL path (highest priority)
        path_parts = request.url.path.strip("/").split("/")
        if len(path_parts) >= 2 and path_parts[0] == "api" and path_parts[1].startswith("v"):
            return path_parts[1]
        
        # 2. Check API-Version header
        version_header = request.headers.get("API-Version")
        if version_header:
            return version_header.lower()
        
        # 3. Check Accept header for versioned media type
        accept_header = request.headers.get("Accept", "")
        if "version=" in accept_header:
            try:
                version_part = accept_header.split("version=")[1].split(";")[0].split(",")[0]
                return f"v{version_part.strip()}"
            except (IndexError, ValueError):
                pass
        
        # 4. Return default version
        return self.default_version


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Advanced rate limiting middleware with multiple strategies.
    
    Features:
    - Per-IP rate limiting
    - Per-user rate limiting (when authenticated)
    - Per-endpoint rate limiting
    - Sliding window algorithm
    - Configurable limits per endpoint
    """
    
    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.redis_client: Optional[redis.Redis] = None
        
        # Default rate limits (requests per minute)
        self.default_limits = {
            "global": 100,          # Global limit per IP
            "auth": 20,             # Auth endpoints
            "upload": 10,           # File upload endpoints
            "generation": 5,        # AI generation endpoints
            "export": 10,           # Export endpoints
        }
        
        # Endpoint patterns and their limits
        self.endpoint_limits = {
            "/auth/": self.default_limits["auth"],
            "/documents/upload": self.default_limits["upload"],
            "/generation/": self.default_limits["generation"],
            "/export/": self.default_limits["export"],
        }
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Apply rate limiting."""
        try:
            # Get Redis client
            if not self.redis_client:
                self.redis_client = await get_redis()
            
            # Check rate limits
            client_ip = get_remote_address(request)
            endpoint = request.url.path
            user_id = getattr(request.state, "user_id", None)
            
            # Determine rate limit
            limit = self._get_endpoint_limit(endpoint)
            
            # Check rate limit
            is_allowed, reset_time = await self._check_rate_limit(
                client_ip, endpoint, user_id, limit
            )
            
            if not is_allowed:
                RATE_LIMIT_HITS.labels(
                    endpoint=endpoint,
                    client_ip=client_ip
                ).inc()
                
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "rate_limit_exceeded",
                        "message": "Rate limit exceeded",
                        "retry_after": reset_time
                    },
                    headers={
                        "Retry-After": str(reset_time),
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Reset": str(reset_time)
                    }
                )
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers
            remaining = await self._get_remaining_requests(client_ip, endpoint, user_id, limit)
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(reset_time)
            
            return response
            
        except Exception as e:
            logger.error("Rate limiting error", exc_info=e)
            # Don't block requests if rate limiting fails
            return await call_next(request)
    
    def _get_endpoint_limit(self, endpoint: str) -> int:
        """Get rate limit for specific endpoint."""
        for pattern, limit in self.endpoint_limits.items():
            if pattern in endpoint:
                return limit
        return self.default_limits["global"]
    
    async def _check_rate_limit(
        self, 
        client_ip: str, 
        endpoint: str, 
        user_id: Optional[str], 
        limit: int
    ) -> Tuple[bool, int]:
        """Check if request is within rate limit."""
        if not self.redis_client:
            return True, 0  # Allow if Redis is unavailable
        
        current_time = int(time.time())
        window_start = current_time - 60  # 1-minute sliding window
        
        # Create keys for different rate limiting strategies
        keys = [
            f"rate_limit:ip:{client_ip}:{endpoint}",
            f"rate_limit:global:ip:{client_ip}",
        ]
        
        if user_id:
            keys.append(f"rate_limit:user:{user_id}:{endpoint}")
        
        # Check each key
        for key in keys:
            try:
                # Remove old entries
                await self.redis_client.zremrangebyscore(key, 0, window_start)
                
                # Count current requests
                current_count = await self.redis_client.zcard(key)
                
                if current_count >= limit:
                    return False, 60  # Not allowed, retry in 60 seconds
                
                # Add current request
                await self.redis_client.zadd(key, {str(uuid.uuid4()): current_time})
                await self.redis_client.expire(key, 60)
                
            except Exception as e:
                logger.error(f"Redis rate limit check failed for key {key}", exc_info=e)
                continue
        
        return True, 60
    
    async def _get_remaining_requests(
        self, 
        client_ip: str, 
        endpoint: str, 
        user_id: Optional[str], 
        limit: int
    ) -> int:
        """Get remaining requests for the current window."""
        if not self.redis_client:
            return limit
        
        key = f"rate_limit:ip:{client_ip}:{endpoint}"
        try:
            current_count = await self.redis_client.zcard(key)
            return max(0, limit - current_count)
        except Exception:
            return limit


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive request/response logging middleware.
    
    Features:
    - Request/response logging with timing
    - Request ID tracking
    - Sensitive data filtering
    - Structured logging
    - Performance metrics
    """
    
    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.sensitive_headers = {
            "authorization", "cookie", "x-api-key", "x-auth-token"
        }
        self.sensitive_fields = {
            "password", "token", "secret", "key", "credential"
        }
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Log request and response."""
        # Generate request ID if not present
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        # Clear and bind logging context
        clear_contextvars()
        bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=get_remote_address(request),
            user_agent=request.headers.get("User-Agent", ""),
        )
        
        # Log request start
        start_time = time.time()
        
        # Read request body for logging (if small enough)
        request_body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if len(body) < 1024:  # Only log small bodies
                    request_body = self._filter_sensitive_data(body.decode("utf-8"))
            except Exception:
                pass
        
        logger.info(
            "Request started",
            headers=self._filter_headers(dict(request.headers)),
            query_params=dict(request.query_params),
            body_preview=request_body[:200] if request_body else None,
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Update metrics
            version = getattr(request.state, "api_version", "unknown")
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code,
                version=version
            ).inc()
            
            REQUEST_DURATION.labels(
                method=request.method,
                endpoint=request.url.path,
                version=version
            ).observe(duration)
            
            # Log response
            logger.info(
                "Request completed",
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
                response_size=response.headers.get("content-length", "unknown"),
            )
            
            # Add request ID to response
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Log error
            logger.error(
                "Request failed",
                duration_ms=round(duration * 1000, 2),
                exc_info=e,
            )
            
            # Update error metrics
            ERROR_COUNT.labels(
                status_code=500,
                endpoint=request.url.path
            ).inc()
            
            raise
    
    def _filter_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Filter sensitive headers."""
        filtered = {}
        for key, value in headers.items():
            if key.lower() in self.sensitive_headers:
                filtered[key] = "[FILTERED]"
            else:
                filtered[key] = value
        return filtered
    
    def _filter_sensitive_data(self, data: str) -> str:
        """Filter sensitive data from request bodies."""
        try:
            # Try to parse as JSON
            json_data = json.loads(data)
            filtered_data = self._filter_json_sensitive(json_data)
            return json.dumps(filtered_data)
        except (json.JSONDecodeError, TypeError):
            # Return original if not JSON
            return data
    
    def _filter_json_sensitive(self, data: Any) -> Any:
        """Recursively filter sensitive fields from JSON data."""
        if isinstance(data, dict):
            filtered = {}
            for key, value in data.items():
                if any(sensitive in key.lower() for sensitive in self.sensitive_fields):
                    filtered[key] = "[FILTERED]"
                else:
                    filtered[key] = self._filter_json_sensitive(value)
            return filtered
        elif isinstance(data, list):
            return [self._filter_json_sensitive(item) for item in data]
        else:
            return data


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Standardized error handling middleware.
    
    Features:
    - Consistent error response format
    - Exception logging
    - Error classification
    - Security-aware error responses
    """
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Handle errors consistently."""
        try:
            return await call_next(request)
        except SlideGenieException as e:
            # Log application errors
            logger.warning(
                "Application error",
                error_type=type(e).__name__,
                message=e.message,
                status_code=e.status_code,
                details=e.details,
            )
            
            # Update error metrics
            ERROR_COUNT.labels(
                status_code=e.status_code,
                endpoint=request.url.path
            ).inc()
            
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": type(e).__name__.replace("Error", "").lower(),
                    "message": e.message,
                    "details": e.details if not settings.is_production else {},
                    "timestamp": int(time.time()),
                }
            )
        
        except HTTPException as e:
            # Log HTTP errors
            logger.warning(
                "HTTP error",
                status_code=e.status_code,
                detail=e.detail,
            )
            
            ERROR_COUNT.labels(
                status_code=e.status_code,
                endpoint=request.url.path
            ).inc()
            
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": "http_error",
                    "message": e.detail,
                    "timestamp": int(time.time()),
                }
            )
        
        except Exception as e:
            # Log unexpected errors
            logger.error(
                "Unexpected error",
                exc_info=e,
                path=request.url.path,
                method=request.method,
            )
            
            ERROR_COUNT.labels(
                status_code=500,
                endpoint=request.url.path
            ).inc()
            
            # Don't expose internal errors in production
            if settings.is_production:
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": "internal_error",
                        "message": "An internal error occurred",
                        "timestamp": int(time.time()),
                    }
                )
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": "internal_error",
                    "message": str(e),
                    "timestamp": int(time.time()),
                }
            )


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Request/response validation middleware.
    
    Features:
    - Content-Type validation
    - Request size limits
    - Response validation
    - Security headers
    """
    
    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.max_request_size = settings.max_upload_size_bytes
        self.allowed_content_types = {
            "application/json",
            "multipart/form-data",
            "application/x-www-form-urlencoded",
            "text/plain",
        }
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Validate request and add security headers."""
        # Validate request size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_request_size:
            return JSONResponse(
                status_code=413,
                content={
                    "error": "payload_too_large",
                    "message": f"Request size exceeds maximum of {self.max_request_size} bytes",
                    "max_size": self.max_request_size,
                }
            )
        
        # Validate Content-Type for requests with body
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "").split(";")[0]
            if content_type and not any(
                allowed in content_type for allowed in self.allowed_content_types
            ):
                return JSONResponse(
                    status_code=415,
                    content={
                        "error": "unsupported_media_type",
                        "message": f"Content-Type '{content_type}' is not supported",
                        "supported_types": list(self.allowed_content_types),
                    }
                )
        
        # Process request
        response = await call_next(request)
        
        # Add security headers
        response.headers.update({
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self'",
        })
        
        # Add CORS headers if not already present
        if "Access-Control-Allow-Origin" not in response.headers:
            origin = request.headers.get("origin")
            if origin in settings.BACKEND_CORS_ORIGINS:
                response.headers["Access-Control-Allow-Origin"] = origin
        
        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    API metrics collection middleware.
    
    Features:
    - Prometheus metrics
    - Custom metrics
    - Performance monitoring
    - Business metrics
    """
    
    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.metrics_cache = defaultdict(int)
        self.last_flush = time.time()
        self.flush_interval = 60  # Flush every minute
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Collect metrics."""
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Collect metrics
        duration = time.time() - start_time
        endpoint = request.url.path
        method = request.method
        status_code = response.status_code
        version = getattr(request.state, "api_version", "unknown")
        
        # Update cache
        self.metrics_cache[f"requests:{method}:{endpoint}"] += 1
        self.metrics_cache[f"status:{status_code}"] += 1
        self.metrics_cache[f"version:{version}"] += 1
        
        # Track slow requests
        if duration > 1.0:  # Requests taking more than 1 second
            self.metrics_cache[f"slow_requests:{endpoint}"] += 1
        
        # Periodic flush to persistent storage
        if time.time() - self.last_flush > self.flush_interval:
            await self._flush_metrics()
            self.last_flush = time.time()
        
        return response
    
    async def _flush_metrics(self):
        """Flush metrics to Redis for persistence."""
        try:
            redis_client = await get_redis()
            if redis_client and self.metrics_cache:
                # Store metrics with timestamp
                timestamp = int(time.time())
                pipe = redis_client.pipeline()
                
                for key, value in self.metrics_cache.items():
                    pipe.hincrby(f"metrics:{timestamp//3600}", key, value)  # Hourly buckets
                    pipe.expire(f"metrics:{timestamp//3600}", 86400 * 7)  # Keep for 7 days
                
                await pipe.execute()
                self.metrics_cache.clear()
                
        except Exception as e:
            logger.error("Failed to flush metrics to Redis", exc_info=e)


def setup_middleware(app: FastAPI) -> None:
    """
    Setup all middleware for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    # Add middleware in reverse order (last added is executed first)
    
    # 1. Metrics collection (outermost)
    app.add_middleware(MetricsMiddleware)
    
    # 2. Error handling
    app.add_middleware(ErrorHandlingMiddleware)
    
    # 3. Request validation and security headers
    app.add_middleware(RequestValidationMiddleware)
    
    # 4. Request logging
    app.add_middleware(RequestLoggingMiddleware)
    
    # 5. Rate limiting
    app.add_middleware(RateLimitingMiddleware)
    
    # 6. API versioning (innermost, runs first)
    app.add_middleware(APIVersioningMiddleware)
    
    # 7. CORS (built-in FastAPI middleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-RateLimit-*", "API-Version"],
    )


# Metrics endpoint
async def get_metrics() -> Response:
    """
    Get Prometheus metrics.
    
    Returns:
        Prometheus metrics in text format
    """
    return Response(
        content=generate_latest(),
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )