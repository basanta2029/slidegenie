"""
SlideGenie API Documentation Package.

This package provides comprehensive OpenAPI documentation generation
and interactive API documentation features.
"""

from .api_examples import APIExamples
from .openapi_generator import OpenAPIGenerator, generate_api_documentation
from .openapi_schemas import (
    ErrorResponse,
    PaginationMeta,
    RateLimitHeaders,
    WebhookEvent,
    WebSocketMessage,
)

__all__ = [
    "APIExamples",
    "OpenAPIGenerator", 
    "generate_api_documentation",
    "ErrorResponse",
    "PaginationMeta", 
    "RateLimitHeaders",
    "WebhookEvent",
    "WebSocketMessage",
]