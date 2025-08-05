"""
Dynamic OpenAPI 3.0 specification generator for SlideGenie API.

This module generates comprehensive OpenAPI documentation with:
- Complete endpoint documentation
- Request/response schemas with examples
- Authentication and security schemes
- Error handling standardization
- WebSocket API documentation
- Rate limiting information
"""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, Union

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel

from app.core.config import settings
from app.docs.openapi_schemas import (
    ErrorResponse,
    PaginationMeta,
    RateLimitHeaders,
    WebhookEvent,
    WebSocketMessage,
)
from app.docs.api_examples import APIExamples


class OpenAPIGenerator:
    """
    Generates comprehensive OpenAPI 3.0 documentation for SlideGenie API.
    """

    def __init__(self, app: FastAPI):
        self.app = app
        self.examples = APIExamples()

    def generate_openapi_schema(self) -> Dict[str, Any]:
        """
        Generate complete OpenAPI 3.0 schema with custom enhancements.
        
        Returns:
            Complete OpenAPI 3.0 specification
        """
        # Get base OpenAPI schema from FastAPI
        openapi_schema = get_openapi(
            title=f"{settings.PROJECT_NAME} API",
            version=settings.APP_VERSION,
            description=self._get_api_description(),
            routes=self.app.routes,
            servers=self._get_servers(),
        )

        # Add custom enhancements
        openapi_schema = self._add_security_schemes(openapi_schema)
        openapi_schema = self._add_error_responses(openapi_schema)
        openapi_schema = self._add_rate_limiting_info(openapi_schema)
        openapi_schema = self._add_webhook_documentation(openapi_schema)
        openapi_schema = self._add_websocket_documentation(openapi_schema)
        openapi_schema = self._add_examples(openapi_schema)
        openapi_schema = self._add_tags_metadata(openapi_schema)
        openapi_schema = self._add_external_docs(openapi_schema)

        return openapi_schema

    def _get_api_description(self) -> str:
        """Get comprehensive API description."""
        return """
## SlideGenie REST API

SlideGenie is an AI-powered academic presentation generation platform that transforms research papers, documents, and academic content into professional slide presentations.

### Key Features

- **Document Processing**: Upload PDFs, Word documents, LaTeX files, and other academic formats
- **AI-Powered Generation**: Advanced AI models create structured, academic-quality presentations
- **Multiple Export Formats**: Export to PowerPoint, PDF, LaTeX Beamer, and Google Slides
- **Real-time Collaboration**: WebSocket-based real-time editing and collaboration
- **Academic Templates**: Specialized templates for research papers, theses, and conferences
- **Citation Management**: Automatic citation parsing and bibliography generation
- **Quality Assurance**: Built-in quality checks for academic standards

### API Design Principles

- **RESTful**: Standard HTTP methods and status codes
- **Versioned**: `/api/v1` prefix for version management
- **Consistent**: Standardized request/response formats
- **Secure**: JWT-based authentication with role-based access control
- **Rate Limited**: Fair usage policies to ensure service quality
- **Real-time**: WebSocket support for live updates

### Authentication

The API uses JWT (JSON Web Tokens) for authentication:

1. **Registration/Login**: Obtain access and refresh tokens
2. **Request Headers**: Include `Authorization: Bearer <token>` header
3. **Token Refresh**: Use refresh token to obtain new access tokens
4. **Academic Validation**: Support for institutional email verification

### Rate Limiting

Rate limits are applied per user and endpoint:

- **Authentication**: 10 requests per minute
- **File Upload**: 5 requests per hour
- **Generation**: 20 requests per hour (free tier)
- **General API**: 1000 requests per hour

### Error Handling

All errors follow a consistent format with:

- **HTTP Status Codes**: Standard codes (400, 401, 403, 404, 422, 500)
- **Error Details**: Structured error messages with codes
- **Request IDs**: Unique identifiers for debugging
- **Validation Errors**: Detailed field-level error information

### WebSocket Integration

Real-time features are provided via WebSocket connections:

- **Generation Progress**: Live updates during slide generation
- **Collaboration**: Multi-user editing and commenting
- **Notifications**: System alerts and user notifications

### Webhooks

Register webhook endpoints to receive notifications about:

- **Generation Complete**: When slide generation finishes
- **Export Ready**: When export files are available
- **User Events**: Registration, verification, etc.

### SDKs and Integration

- **Python SDK**: Official Python client library
- **JavaScript SDK**: Browser and Node.js support
- **Postman Collection**: Ready-to-import API collection
- **OpenAPI Generators**: Support for code generation in multiple languages
        """

    def _get_servers(self) -> List[Dict[str, str]]:
        """Get server configurations for different environments."""
        servers = []

        if settings.is_development:
            servers.extend([
                {
                    "url": "http://localhost:8000",
                    "description": "Development server"
                },
                {
                    "url": "http://127.0.0.1:8000",
                    "description": "Local development server"
                }
            ])

        # Add staging/production servers based on environment
        if not settings.is_production:
            servers.append({
                "url": "https://api-staging.slidegenie.com",
                "description": "Staging server"
            })

        servers.append({
            "url": "https://api.slidegenie.com",
            "description": "Production server"
        })

        return servers

    def _add_security_schemes(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Add comprehensive security scheme definitions."""
        if "components" not in schema:
            schema["components"] = {}

        if "securitySchemes" not in schema["components"]:
            schema["components"]["securitySchemes"] = {}

        schema["components"]["securitySchemes"].update({
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT token obtained from login or registration"
            },
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": "API key for service-to-service authentication"
            },
            "OAuth2": {
                "type": "oauth2",
                "description": "OAuth2 authentication with Google and Microsoft",
                "flows": {
                    "authorizationCode": {
                        "authorizationUrl": f"{settings.API_BASE_URL}/api/v1/oauth/authorize",
                        "tokenUrl": f"{settings.API_BASE_URL}/api/v1/oauth/token",
                        "scopes": {
                            "read": "Read access to user data",
                            "write": "Write access to user data",
                            "admin": "Administrative access"
                        }
                    }
                }
            }
        })

        # Add global security requirement
        schema["security"] = [
            {"BearerAuth": []},
            {"ApiKeyAuth": []},
            {"OAuth2": ["read", "write"]}
        ]

        return schema

    def _add_error_responses(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Add standardized error response schemas."""
        if "components" not in schema:
            schema["components"] = {}

        if "schemas" not in schema["components"]:
            schema["components"]["schemas"] = {}

        # Add error response schemas
        error_schemas = {
            "ErrorResponse": {
                "type": "object",
                "properties": {
                    "error": {
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "Machine-readable error code"
                            },
                            "message": {
                                "type": "string",
                                "description": "Human-readable error message"
                            },
                            "details": {
                                "type": "object",
                                "description": "Additional error details",
                                "additionalProperties": True
                            },
                            "request_id": {
                                "type": "string",
                                "description": "Unique request identifier for debugging"
                            },
                            "timestamp": {
                                "type": "string",
                                "format": "date-time",
                                "description": "Error timestamp in ISO 8601 format"
                            }
                        },
                        "required": ["code", "message"]
                    }
                },
                "required": ["error"]
            },
            "ValidationError": {
                "type": "object",
                "properties": {
                    "error": {
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "enum": ["VALIDATION_ERROR"]
                            },
                            "message": {
                                "type": "string"
                            },
                            "details": {
                                "type": "object",
                                "properties": {
                                    "field_errors": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "field": {"type": "string"},
                                                "message": {"type": "string"},
                                                "code": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "RateLimitError": {
                "type": "object",
                "properties": {
                    "error": {
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "enum": ["RATE_LIMIT_EXCEEDED"]
                            },
                            "message": {
                                "type": "string"
                            },
                            "details": {
                                "type": "object",
                                "properties": {
                                    "limit": {"type": "integer"},
                                    "remaining": {"type": "integer"},
                                    "reset_at": {"type": "string", "format": "date-time"}
                                }
                            }
                        }
                    }
                }
            }
        }

        schema["components"]["schemas"].update(error_schemas)

        # Add common error responses to all endpoints
        common_responses = {
            "400": {
                "description": "Bad Request - Invalid request data",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                        "examples": {
                            "invalid_request": {
                                "summary": "Invalid request format",
                                "value": self.examples.get_error_example("INVALID_REQUEST")
                            }
                        }
                    }
                }
            },
            "401": {
                "description": "Unauthorized - Authentication required",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                        "examples": {
                            "unauthorized": {
                                "summary": "Missing or invalid authentication",
                                "value": self.examples.get_error_example("UNAUTHORIZED")
                            }
                        }
                    }
                }
            },
            "403": {
                "description": "Forbidden - Insufficient permissions",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                        "examples": {
                            "forbidden": {
                                "summary": "Insufficient permissions",
                                "value": self.examples.get_error_example("FORBIDDEN")
                            }
                        }
                    }
                }
            },
            "404": {
                "description": "Not Found - Resource not found",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                        "examples": {
                            "not_found": {
                                "summary": "Resource not found",
                                "value": self.examples.get_error_example("NOT_FOUND")
                            }
                        }
                    }
                }
            },
            "422": {
                "description": "Unprocessable Entity - Validation error",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ValidationError"},
                        "examples": {
                            "validation_error": {
                                "summary": "Field validation errors",
                                "value": self.examples.get_validation_error_example()
                            }
                        }
                    }
                }
            },
            "429": {
                "description": "Too Many Requests - Rate limit exceeded",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/RateLimitError"},
                        "examples": {
                            "rate_limit": {
                                "summary": "Rate limit exceeded",
                                "value": self.examples.get_rate_limit_error_example()
                            }
                        }
                    }
                },
                "headers": {
                    "X-RateLimit-Limit": {
                        "description": "Request limit per time window",
                        "schema": {"type": "integer"}
                    },
                    "X-RateLimit-Remaining": {
                        "description": "Remaining requests in current window",
                        "schema": {"type": "integer"}
                    },
                    "X-RateLimit-Reset": {
                        "description": "Time when the rate limit resets (Unix timestamp)",
                        "schema": {"type": "integer"}
                    }
                }
            },
            "500": {
                "description": "Internal Server Error - Server error",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                        "examples": {
                            "server_error": {
                                "summary": "Internal server error",
                                "value": self.examples.get_error_example("INTERNAL_ERROR")
                            }
                        }
                    }
                }
            }
        }

        # Add common responses to all endpoints
        if "paths" in schema:
            for path, methods in schema["paths"].items():
                for method, operation in methods.items():
                    if method.lower() in ["get", "post", "put", "patch", "delete"]:
                        if "responses" not in operation:
                            operation["responses"] = {}
                        
                        # Add common error responses if not already present
                        for status_code, response in common_responses.items():
                            if status_code not in operation["responses"]:
                                operation["responses"][status_code] = response

        return schema

    def _add_rate_limiting_info(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Add rate limiting information to endpoints."""
        rate_limits = {
            "/auth/login": {"limit": 10, "window": "1 minute"},
            "/auth/register": {"limit": 5, "window": "1 minute"},
            "/documents/upload": {"limit": 5, "window": "1 hour"},
            "/generation/create": {"limit": 20, "window": "1 hour"},
            "/export": {"limit": 10, "window": "1 hour"},
        }

        if "paths" in schema:
            for path, methods in schema["paths"].items():
                for method, operation in methods.items():
                    if method.lower() in ["get", "post", "put", "patch", "delete"]:
                        # Add rate limit info to operation description
                        if path in rate_limits:
                            limit_info = rate_limits[path]
                            if "description" not in operation:
                                operation["description"] = ""
                            
                            operation["description"] += f"\n\n**Rate Limit**: {limit_info['limit']} requests per {limit_info['window']}"

        return schema

    def _add_webhook_documentation(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Add webhook documentation."""
        webhook_info = {
            "webhooks": {
                "generation-complete": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "event": {
                                                "type": "string",
                                                "enum": ["generation.complete"]
                                            },
                                            "data": {
                                                "type": "object",
                                                "properties": {
                                                    "presentation_id": {"type": "string", "format": "uuid"},
                                                    "user_id": {"type": "string", "format": "uuid"},
                                                    "status": {"type": "string", "enum": ["completed", "failed"]},
                                                    "slides_count": {"type": "integer"},
                                                    "generation_time_ms": {"type": "integer"},
                                                    "download_url": {"type": "string", "format": "uri"}
                                                }
                                            },
                                            "timestamp": {"type": "string", "format": "date-time"},
                                            "signature": {"type": "string", "description": "HMAC signature for verification"}
                                        }
                                    },
                                    "examples": {
                                        "generation_complete": {
                                            "summary": "Generation completed successfully",
                                            "value": self.examples.get_webhook_example("generation.complete")
                                        }
                                    }
                                }
                            }
                        },
                        "responses": {
                            "200": {
                                "description": "Webhook received successfully"
                            }
                        }
                    }
                },
                "export-ready": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "event": {
                                                "type": "string",
                                                "enum": ["export.ready"]
                                            },
                                            "data": {
                                                "type": "object",
                                                "properties": {
                                                    "export_id": {"type": "string", "format": "uuid"},
                                                    "presentation_id": {"type": "string", "format": "uuid"},
                                                    "format": {"type": "string", "enum": ["pptx", "pdf", "beamer", "google_slides"]},
                                                    "download_url": {"type": "string", "format": "uri"},
                                                    "expires_at": {"type": "string", "format": "date-time"}
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        schema.update(webhook_info)
        return schema

    def _add_websocket_documentation(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Add WebSocket API documentation."""
        # Add WebSocket schemas to components
        if "components" not in schema:
            schema["components"] = {}

        if "schemas" not in schema["components"]:
            schema["components"]["schemas"] = {}

        websocket_schemas = {
            "WebSocketMessage": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["progress", "complete", "error", "ping", "pong"]
                    },
                    "data": {
                        "type": "object",
                        "description": "Message payload"
                    },
                    "timestamp": {
                        "type": "string",
                        "format": "date-time"
                    },
                    "request_id": {
                        "type": "string",
                        "description": "Request correlation ID"
                    }
                }
            },
            "ProgressMessage": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["progress"]},
                    "data": {
                        "type": "object",
                        "properties": {
                            "job_id": {"type": "string", "format": "uuid"},
                            "stage": {"type": "string"},
                            "progress": {"type": "number", "minimum": 0, "maximum": 100},
                            "message": {"type": "string"},
                            "details": {"type": "object"}
                        }
                    }
                }
            }
        }

        schema["components"]["schemas"].update(websocket_schemas)

        # Add WebSocket endpoint documentation to info
        if "info" not in schema:
            schema["info"] = {}

        websocket_docs = """

### WebSocket Endpoints

#### Generation Progress: `ws://localhost:8000/api/v1/ws/generation/{job_id}`

Subscribe to real-time generation progress updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/generation/123e4567-e89b-12d3-a456-426614174000');

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    switch (message.type) {
        case 'progress':
            console.log(`Progress: ${message.data.progress}%`);
            break;
        case 'complete':
            console.log('Generation completed!');
            break;
        case 'error':
            console.error('Generation failed:', message.data.error);
            break;
    }
};
```

#### Real-time Collaboration: `ws://localhost:8000/api/v1/ws/collaboration/{presentation_id}`

Enable real-time collaborative editing:

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/collaboration/123e4567-e89b-12d3-a456-426614174000');

// Send edit
ws.send(JSON.stringify({
    type: 'edit',
    data: {
        slide_id: 'slide-1',
        changes: { title: 'New Title' }
    }
}));
```

### WebSocket Message Types

- **progress**: Generation progress updates
- **complete**: Operation completion notification
- **error**: Error notifications
- **edit**: Collaborative editing changes
- **comment**: User comments and annotations
- **cursor**: User cursor positions
- **ping/pong**: Connection keep-alive
        """

        schema["info"]["description"] += websocket_docs

        return schema

    def _add_examples(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Add comprehensive examples to all endpoints."""
        if "paths" not in schema:
            return schema

        # Map of endpoint patterns to example methods
        endpoint_examples = {
            "/auth/register": ("post", "auth_register"),
            "/auth/login": ("post", "auth_login"),
            "/presentations": ("get", "presentations_list"),
            "/presentations": ("post", "presentations_create"),
            "/presentations/{id}": ("get", "presentations_get"),
            "/generation/create": ("post", "generation_create"),
            "/documents/upload": ("post", "document_upload"),
            "/export/{presentation_id}": ("post", "export_create"),
        }

        for path, methods in schema["paths"].items():
            for method, operation in methods.items():
                if method.lower() in ["get", "post", "put", "patch", "delete"]:
                    # Add examples based on endpoint pattern
                    example_key = f"{method.lower()}_{path.replace('/', '_').replace('{', '').replace('}', '').strip('_')}"
                    
                    if hasattr(self.examples, f"get_{example_key}_example"):
                        example_method = getattr(self.examples, f"get_{example_key}_example")
                        example_data = example_method()
                        
                        # Add request body examples
                        if "requestBody" in operation and example_data.get("request"):
                            content = operation["requestBody"].get("content", {})
                            for content_type in content:
                                if "examples" not in content[content_type]:
                                    content[content_type]["examples"] = {}
                                content[content_type]["examples"]["example"] = {
                                    "summary": "Example request",
                                    "value": example_data["request"]
                                }
                        
                        # Add response examples
                        if "responses" in operation and example_data.get("response"):
                            for status_code, response in operation["responses"].items():
                                if status_code.startswith("2") and "content" in response:
                                    content = response["content"]
                                    for content_type in content:
                                        if "examples" not in content[content_type]:
                                            content[content_type]["examples"] = {}
                                        content[content_type]["examples"]["example"] = {
                                            "summary": "Example response",
                                            "value": example_data["response"]
                                        }

        return schema

    def _add_tags_metadata(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Add comprehensive tag metadata."""
        tags = [
            {
                "name": "health",
                "description": "Health check and system status endpoints"
            },
            {
                "name": "authentication",
                "description": "User authentication, registration, and token management"
            },
            {
                "name": "oauth",
                "description": "OAuth 2.0 authentication with Google and Microsoft"
            },
            {
                "name": "academic",
                "description": "Academic institution validation and management"
            },
            {
                "name": "users",
                "description": "User profile management and preferences"
            },
            {
                "name": "presentations",
                "description": "Presentation CRUD operations and management"
            },
            {
                "name": "templates",
                "description": "Academic presentation templates and customization"
            },
            {
                "name": "generation",
                "description": "AI-powered slide generation from documents"
            },
            {
                "name": "slides",
                "description": "Individual slide management and editing"
            },
            {
                "name": "document-upload",
                "description": "Document upload and processing endpoints"
            },
            {
                "name": "export",
                "description": "Presentation export in multiple formats"
            },
            {
                "name": "websocket",
                "description": "WebSocket connections for real-time features"
            },
            {
                "name": "realtime",
                "description": "Real-time collaboration and live updates"
            },
            {
                "name": "analytics",
                "description": "Usage analytics and reporting"
            },
            {
                "name": "admin",
                "description": "Administrative endpoints and system management"
            }
        ]

        schema["tags"] = tags
        return schema

    def _add_external_docs(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Add external documentation links."""
        schema["externalDocs"] = {
            "description": "SlideGenie Documentation",
            "url": "https://docs.slidegenie.com"
        }

        return schema

    def generate_postman_collection(self) -> Dict[str, Any]:
        """
        Generate Postman collection from OpenAPI schema.
        
        Returns:
            Postman collection JSON
        """
        schema = self.generate_openapi_schema()
        
        collection = {
            "info": {
                "name": f"{settings.PROJECT_NAME} API",
                "description": schema["info"]["description"],
                "version": schema["info"]["version"],
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "auth": {
                "type": "bearer",
                "bearer": [
                    {
                        "key": "token",
                        "value": "{{access_token}}",
                        "type": "string"
                    }
                ]
            },
            "variable": [
                {
                    "key": "base_url",
                    "value": "http://localhost:8000",
                    "type": "string"
                },
                {
                    "key": "access_token",
                    "value": "",
                    "type": "string"
                }
            ],
            "item": []
        }

        # Convert OpenAPI paths to Postman requests
        if "paths" in schema:
            for path, methods in schema["paths"].items():
                folder = {
                    "name": path.split("/")[3] if len(path.split("/")) > 3 else "General",
                    "item": []
                }

                for method, operation in methods.items():
                    if method.lower() in ["get", "post", "put", "patch", "delete"]:
                        request = {
                            "name": operation.get("summary", f"{method.upper()} {path}"),
                            "request": {
                                "method": method.upper(),
                                "header": [
                                    {
                                        "key": "Content-Type",
                                        "value": "application/json"
                                    }
                                ],
                                "url": {
                                    "raw": f"{{{{base_url}}}}{path}",
                                    "host": ["{{base_url}}"],
                                    "path": path.strip("/").split("/")
                                }
                            }
                        }

                        # Add request body if present
                        if "requestBody" in operation:
                            content = operation["requestBody"].get("content", {})
                            if "application/json" in content:
                                schema_ref = content["application/json"].get("schema", {})
                                # Add example body
                                request["request"]["body"] = {
                                    "mode": "raw",
                                    "raw": json.dumps({}, indent=2)
                                }

                        folder["item"].append(request)

                if folder["item"]:
                    collection["item"].append(folder)

        return collection


def generate_api_documentation(app: FastAPI) -> Dict[str, Any]:
    """
    Generate complete API documentation including OpenAPI schema and Postman collection.
    
    Args:
        app: FastAPI application instance
        
    Returns:
        Dictionary containing OpenAPI schema and Postman collection
    """
    generator = OpenAPIGenerator(app)
    
    return {
        "openapi_schema": generator.generate_openapi_schema(),
        "postman_collection": generator.generate_postman_collection(),
        "generated_at": datetime.utcnow().isoformat(),
        "version": settings.APP_VERSION
    }