"""
Prometheus metrics instrumentation for SlideGenie application.
"""
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Create custom registry for application metrics
registry = CollectorRegistry()

# =============================================================================
# HTTP Metrics
# =============================================================================

# HTTP request metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status'],
    registry=registry
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0),
    registry=registry
)

http_request_size_bytes = Histogram(
    'http_request_size_bytes',
    'HTTP request size in bytes',
    ['method', 'endpoint'],
    registry=registry
)

http_response_size_bytes = Histogram(
    'http_response_size_bytes',
    'HTTP response size in bytes',
    ['method', 'endpoint'],
    registry=registry
)

# =============================================================================
# Business Metrics
# =============================================================================

# User metrics
slidegenie_user_registrations_total = Counter(
    'slidegenie_user_registrations_total',
    'Total user registrations',
    ['source'],
    registry=registry
)

slidegenie_user_logins_total = Counter(
    'slidegenie_user_logins_total',
    'Total user logins',
    ['method'],
    registry=registry
)

slidegenie_active_users = Gauge(
    'slidegenie_active_users',
    'Currently active users',
    registry=registry
)

# Presentation metrics
slidegenie_presentations_generated_total = Counter(
    'slidegenie_presentations_generated_total',
    'Total presentations generated',
    ['status', 'template_type'],
    registry=registry
)

slidegenie_presentation_generation_duration_seconds = Histogram(
    'slidegenie_presentation_generation_duration_seconds',
    'Time taken to generate presentations',
    ['template_type'],
    buckets=(1, 2, 5, 10, 20, 30, 60, 120, 300),
    registry=registry
)

# Document processing metrics
slidegenie_documents_processed_total = Counter(
    'slidegenie_documents_processed_total',
    'Total documents processed',
    ['status', 'document_type'],
    registry=registry
)

slidegenie_document_processing_duration_seconds = Histogram(
    'slidegenie_document_processing_duration_seconds',
    'Time taken to process documents',
    ['document_type'],
    buckets=(0.5, 1, 2, 5, 10, 20, 30, 60, 120),
    registry=registry
)

slidegenie_document_size_bytes = Histogram(
    'slidegenie_document_size_bytes',
    'Size of processed documents',
    ['document_type'],
    registry=registry
)

# Export metrics
slidegenie_exports_total = Counter(
    'slidegenie_exports_total',
    'Total presentation exports',
    ['status', 'format'],
    registry=registry
)

slidegenie_export_duration_seconds = Histogram(
    'slidegenie_export_duration_seconds',
    'Time taken to export presentations',
    ['format'],
    buckets=(1, 2, 5, 10, 20, 30, 60),
    registry=registry
)

# Template metrics
slidegenie_template_usage_total = Counter(
    'slidegenie_template_usage_total',
    'Total template usage',
    ['template_id', 'template_name'],
    registry=registry
)

# File upload metrics
slidegenie_file_uploads_total = Counter(
    'slidegenie_file_uploads_total',
    'Total file uploads',
    ['status', 'file_type'],
    registry=registry
)

slidegenie_file_upload_size_bytes = Histogram(
    'slidegenie_file_upload_size_bytes',
    'Size of uploaded files',
    ['file_type'],
    registry=registry
)

# =============================================================================
# AI/ML Metrics
# =============================================================================

# AI API metrics
slidegenie_ai_api_requests_total = Counter(
    'slidegenie_ai_api_requests_total',
    'Total AI API requests',
    ['provider', 'model', 'status'],
    registry=registry
)

slidegenie_ai_api_duration_seconds = Histogram(
    'slidegenie_ai_api_duration_seconds',
    'AI API request duration',
    ['provider', 'model'],
    buckets=(0.1, 0.5, 1, 2, 5, 10, 20, 30, 60),
    registry=registry
)

slidegenie_ai_tokens_consumed_total = Counter(
    'slidegenie_ai_tokens_consumed_total',
    'Total AI tokens consumed',
    ['provider', 'model', 'token_type'],
    registry=registry
)

slidegenie_ai_cost_total = Counter(
    'slidegenie_ai_cost_total',
    'Total AI API costs',
    ['provider', 'model'],
    registry=registry
)

slidegenie_ai_content_quality_score = Gauge(
    'slidegenie_ai_content_quality_score',
    'AI-generated content quality score (0-10)',
    ['content_type'],
    registry=registry
)

slidegenie_ai_generation_pipeline_duration_seconds = Histogram(
    'slidegenie_ai_generation_pipeline_duration_seconds',
    'Full AI generation pipeline duration',
    ['pipeline_type'],
    buckets=(5, 10, 20, 30, 60, 120, 300),
    registry=registry
)

# =============================================================================
# Queue and Background Job Metrics
# =============================================================================

slidegenie_queue_jobs_total = Counter(
    'slidegenie_queue_jobs_total',
    'Total queue jobs',
    ['queue', 'state'],
    registry=registry
)

slidegenie_queue_length = Gauge(
    'slidegenie_queue_length',
    'Current queue length',
    ['queue'],
    registry=registry
)

slidegenie_job_processing_duration_seconds = Histogram(
    'slidegenie_job_processing_duration_seconds',
    'Job processing duration',
    ['queue', 'job_type'],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600),
    registry=registry
)

slidegenie_job_wait_time_seconds = Histogram(
    'slidegenie_job_wait_time_seconds',
    'Job wait time in queue',
    ['queue'],
    buckets=(1, 5, 10, 30, 60, 300, 600, 1800),
    registry=registry
)

# =============================================================================
# Security Metrics
# =============================================================================

slidegenie_auth_attempts_total = Counter(
    'slidegenie_auth_attempts_total',
    'Total authentication attempts',
    ['method', 'status'],
    registry=registry
)

slidegenie_security_events_total = Counter(
    'slidegenie_security_events_total',
    'Total security events',
    ['type', 'severity'],
    registry=registry
)

slidegenie_rate_limit_exceeded_total = Counter(
    'slidegenie_rate_limit_exceeded_total',
    'Total rate limit violations',
    ['endpoint', 'user_id'],
    registry=registry
)

slidegenie_blocked_ips_total = Gauge(
    'slidegenie_blocked_ips_total',
    'Currently blocked IP addresses',
    registry=registry
)

# =============================================================================
# Application Info
# =============================================================================

slidegenie_info = Info(
    'slidegenie_app_info',
    'SlideGenie application information',
    registry=registry
)

# =============================================================================
# WebSocket Metrics
# =============================================================================

websocket_connections_total = Gauge(
    'websocket_connections_total',
    'WebSocket connections',
    ['state'],
    registry=registry
)

websocket_messages_total = Counter(
    'websocket_messages_total',
    'WebSocket messages',
    ['direction', 'message_type'],
    registry=registry
)

websocket_message_duration_seconds = Histogram(
    'websocket_message_duration_seconds',
    'WebSocket message processing duration',
    ['message_type'],
    registry=registry
)

# =============================================================================
# Database Metrics
# =============================================================================

slidegenie_database_queries_total = Counter(
    'slidegenie_database_queries_total',
    'Total database queries',
    ['operation', 'table'],
    registry=registry
)

slidegenie_database_query_duration_seconds = Histogram(
    'slidegenie_database_query_duration_seconds',
    'Database query duration',
    ['operation', 'table'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
    registry=registry
)

# =============================================================================
# Utility Functions
# =============================================================================

def track_presentation_generation(template_type: str, status: str, duration: float):
    """Track presentation generation metrics."""
    slidegenie_presentations_generated_total.labels(
        status=status,
        template_type=template_type
    ).inc()
    
    if status == "success":
        slidegenie_presentation_generation_duration_seconds.labels(
            template_type=template_type
        ).observe(duration)

def track_document_processing(document_type: str, status: str, duration: float, size_bytes: int):
    """Track document processing metrics."""
    slidegenie_documents_processed_total.labels(
        status=status,
        document_type=document_type
    ).inc()
    
    if status == "success":
        slidegenie_document_processing_duration_seconds.labels(
            document_type=document_type
        ).observe(duration)
        
        slidegenie_document_size_bytes.labels(
            document_type=document_type
        ).observe(size_bytes)

def track_ai_api_call(provider: str, model: str, status: str, duration: float, 
                     input_tokens: int = 0, output_tokens: int = 0, cost: float = 0.0):
    """Track AI API call metrics."""
    slidegenie_ai_api_requests_total.labels(
        provider=provider,
        model=model,
        status=status
    ).inc()
    
    slidegenie_ai_api_duration_seconds.labels(
        provider=provider,
        model=model
    ).observe(duration)
    
    if input_tokens > 0:
        slidegenie_ai_tokens_consumed_total.labels(
            provider=provider,
            model=model,
            token_type="input"
        ).inc(input_tokens)
    
    if output_tokens > 0:
        slidegenie_ai_tokens_consumed_total.labels(
            provider=provider,
            model=model,
            token_type="output"
        ).inc(output_tokens)
    
    if cost > 0:
        slidegenie_ai_cost_total.labels(
            provider=provider,
            model=model
        ).inc(cost)

def track_export_operation(format: str, status: str, duration: float = None):
    """Track export operation metrics."""
    slidegenie_exports_total.labels(
        status=status,
        format=format
    ).inc()
    
    if duration is not None and status == "success":
        slidegenie_export_duration_seconds.labels(
            format=format
        ).observe(duration)

def track_user_activity(action: str, **labels):
    """Track user activity metrics."""
    if action == "login":
        method = labels.get("method", "unknown")
        slidegenie_user_logins_total.labels(method=method).inc()
    elif action == "registration":
        source = labels.get("source", "unknown")
        slidegenie_user_registrations_total.labels(source=source).inc()

def track_security_event(event_type: str, severity: str = "info"):
    """Track security events."""
    slidegenie_security_events_total.labels(
        type=event_type,
        severity=severity
    ).inc()

def track_auth_attempt(method: str, status: str):
    """Track authentication attempts."""
    slidegenie_auth_attempts_total.labels(
        method=method,
        status=status
    ).inc()

def track_queue_job(queue: str, job_type: str, state: str, 
                   processing_duration: float = None, wait_time: float = None):
    """Track queue job metrics."""
    slidegenie_queue_jobs_total.labels(
        queue=queue,
        state=state
    ).inc()
    
    if processing_duration is not None:
        slidegenie_job_processing_duration_seconds.labels(
            queue=queue,
            job_type=job_type
        ).observe(processing_duration)
    
    if wait_time is not None:
        slidegenie_job_wait_time_seconds.labels(
            queue=queue
        ).observe(wait_time)

def track_file_upload(file_type: str, status: str, size_bytes: int = None):
    """Track file upload metrics."""
    slidegenie_file_uploads_total.labels(
        status=status,
        file_type=file_type
    ).inc()
    
    if size_bytes is not None and status == "success":
        slidegenie_file_upload_size_bytes.labels(
            file_type=file_type
        ).observe(size_bytes)

# =============================================================================
# Decorators
# =============================================================================

def monitor_ai_api_call(provider: str, model: str):
    """Decorator to monitor AI API calls."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            
            try:
                result = await func(*args, **kwargs)
                
                # Extract token usage from result if available
                input_tokens = getattr(result, 'input_tokens', 0)
                output_tokens = getattr(result, 'output_tokens', 0)
                cost = getattr(result, 'cost', 0.0)
                
                track_ai_api_call(
                    provider=provider,
                    model=model,
                    status=status,
                    duration=time.time() - start_time,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost=cost
                )
                
                return result
            except Exception as e:
                status = "error"
                track_ai_api_call(
                    provider=provider,
                    model=model,
                    status=status,
                    duration=time.time() - start_time
                )
                raise
        
        return wrapper
    return decorator

def monitor_business_operation(operation_type: str, **labels):
    """Decorator to monitor business operations."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                if operation_type == "presentation_generation":
                    track_presentation_generation(
                        template_type=labels.get("template_type", "unknown"),
                        status="success",
                        duration=duration
                    )
                elif operation_type == "document_processing":
                    track_document_processing(
                        document_type=labels.get("document_type", "unknown"),
                        status="success",
                        duration=duration,
                        size_bytes=labels.get("size_bytes", 0)
                    )
                elif operation_type == "export":
                    track_export_operation(
                        format=labels.get("format", "unknown"),
                        status="success",
                        duration=duration
                    )
                
                return result
            except Exception as e:
                if operation_type == "presentation_generation":
                    track_presentation_generation(
                        template_type=labels.get("template_type", "unknown"),
                        status="failure",
                        duration=time.time() - start_time
                    )
                elif operation_type == "document_processing":
                    track_document_processing(
                        document_type=labels.get("document_type", "unknown"),
                        status="failure",
                        duration=time.time() - start_time,
                        size_bytes=0
                    )
                elif operation_type == "export":
                    track_export_operation(
                        format=labels.get("format", "unknown"),
                        status="failure",
                        duration=time.time() - start_time
                    )
                raise
        
        return wrapper
    return decorator

# =============================================================================
# FastAPI Middleware
# =============================================================================

class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP metrics."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Get request size
        request_size = int(request.headers.get("content-length", 0))
        
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Get response size
        response_size = int(response.headers.get("content-length", 0))
        
        # Extract endpoint from path
        endpoint = request.url.path
        method = request.method
        status = str(response.status_code)
        
        # Record metrics
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=status
        ).inc()
        
        http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
        
        if request_size > 0:
            http_request_size_bytes.labels(
                method=method,
                endpoint=endpoint
            ).observe(request_size)
        
        if response_size > 0:
            http_response_size_bytes.labels(
                method=method,
                endpoint=endpoint
            ).observe(response_size)
        
        return response

# =============================================================================
# Metrics Endpoint
# =============================================================================

def get_metrics():
    """Get Prometheus metrics."""
    return Response(
        generate_latest(registry),
        media_type=CONTENT_TYPE_LATEST
    )

def set_app_info(version: str, environment: str, git_commit: str = "unknown"):
    """Set application information."""
    slidegenie_info.info({
        'version': version,
        'environment': environment,
        'git_commit': git_commit
    })