"""API response factories for testing."""

import factory
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import random
import json

from .base import BaseFactory, DictFactory, fake


class APIResponseFactory(DictFactory):
    """Factory for creating API response test data."""
    
    status_code = factory.LazyAttribute(
        lambda o: random.choice([200, 201, 204, 400, 401, 403, 404, 422, 500])
    )
    
    success = factory.LazyAttribute(lambda o: o.status_code < 400)
    
    # Response metadata
    request_id = factory.LazyAttribute(lambda o: BaseFactory.random_string(16, "req_"))
    timestamp = factory.LazyFunction(lambda: datetime.now(timezone.utc).isoformat())
    
    # Response time simulation
    response_time_ms = factory.LazyAttribute(
        lambda o: random.randint(10, 500) if o.success else random.randint(5, 100)
    )
    
    # Headers
    headers = factory.LazyAttribute(lambda o: {
        "Content-Type": "application/json",
        "X-Request-ID": o.request_id,
        "X-Response-Time": str(o.response_time_ms),
        "X-Rate-Limit-Limit": "1000",
        "X-Rate-Limit-Remaining": str(random.randint(0, 1000)),
        "X-Rate-Limit-Reset": str(int(datetime.now(timezone.utc).timestamp() + 3600)),
    })
    
    # Response body
    data = factory.LazyAttribute(lambda o: _generate_response_data(o.status_code, o.endpoint))
    
    # Error details
    error = factory.LazyAttribute(
        lambda o: _generate_error_response(o.status_code) if not o.success else None
    )
    
    # Pagination metadata
    pagination = factory.LazyAttribute(
        lambda o: {
            "page": 1,
            "per_page": 20,
            "total": random.randint(0, 1000),
            "total_pages": random.randint(1, 50),
            "has_next": random.choice([True, False]),
            "has_prev": False,
        } if o.success and o.is_list else None
    )
    
    # Additional parameters
    endpoint = factory.LazyAttribute(
        lambda o: random.choice([
            "/api/v1/presentations",
            "/api/v1/users",
            "/api/v1/templates",
            "/api/v1/slides",
            "/api/v1/auth/login",
        ])
    )
    
    is_list = factory.LazyAttribute(
        lambda o: o.endpoint.endswith(("presentations", "users", "templates", "slides"))
    )
    
    class Params:
        success_response = factory.Trait(
            status_code=200,
            success=True,
            error=None,
        )
        
        created_response = factory.Trait(
            status_code=201,
            success=True,
            error=None,
        )
        
        validation_error = factory.Trait(
            status_code=422,
            success=False,
        )
        
        unauthorized = factory.Trait(
            status_code=401,
            success=False,
        )
        
        server_error = factory.Trait(
            status_code=500,
            success=False,
        )


class MockResponseFactory(DictFactory):
    """Factory for creating mock HTTP responses."""
    
    status_code = 200
    
    json_data = factory.LazyAttribute(lambda o: o.data)
    
    text = factory.LazyAttribute(lambda o: json.dumps(o.json_data))
    
    headers = factory.LazyAttribute(lambda o: {
        "Content-Type": "application/json",
        "Content-Length": str(len(o.text)),
    })
    
    elapsed_ms = factory.LazyAttribute(lambda o: random.randint(10, 500))
    
    url = factory.LazyAttribute(
        lambda o: f"https://api.slidegenie.io{o.endpoint}"
    )
    
    endpoint = "/api/v1/resource"
    
    data = factory.LazyAttribute(lambda o: {"id": "123", "status": "success"})
    
    def json(self):
        """Mock json() method for response objects."""
        return self.get("json_data")
    
    def raise_for_status(self):
        """Mock raise_for_status() method."""
        if self.get("status_code") >= 400:
            raise Exception(f"HTTP {self.get('status_code')} Error")
    
    class Params:
        error_response = factory.Trait(
            status_code=400,
            data=factory.LazyAttribute(lambda o: {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid input data",
                }
            }),
        )


class WebSocketMessageFactory(DictFactory):
    """Factory for WebSocket message test data."""
    
    id = factory.LazyAttribute(lambda o: BaseFactory.random_string(16, "msg_"))
    
    type = factory.LazyAttribute(
        lambda o: random.choice([
            "connection", "presentation_update", "slide_update",
            "collaboration", "notification", "error", "ping", "pong"
        ])
    )
    
    event = factory.LazyAttribute(lambda o: {
        "connection": random.choice(["connected", "disconnected", "reconnected"]),
        "presentation_update": random.choice(["created", "updated", "deleted"]),
        "slide_update": random.choice(["added", "modified", "removed", "reordered"]),
        "collaboration": random.choice(["user_joined", "user_left", "cursor_moved", "selection_changed"]),
        "notification": random.choice(["info", "warning", "error", "success"]),
    }.get(o.type, o.type))
    
    payload = factory.LazyAttribute(lambda o: _generate_websocket_payload(o.type, o.event))
    
    timestamp = factory.LazyFunction(lambda: datetime.now(timezone.utc).isoformat())
    
    user_id = factory.LazyAttribute(lambda o: f"user_{random.randint(1, 100)}")
    
    room_id = factory.LazyAttribute(
        lambda o: f"pres_{random.randint(1, 100)}" 
        if o.type in ["presentation_update", "slide_update", "collaboration"] else None
    )
    
    ack_required = factory.LazyAttribute(
        lambda o: o.type in ["presentation_update", "slide_update"]
    )
    
    class Params:
        connection_message = factory.Trait(
            type="connection",
            event="connected",
            payload=factory.LazyAttribute(lambda o: {
                "session_id": BaseFactory.random_string(32),
                "user": {
                    "id": o.user_id,
                    "name": fake.name(),
                    "avatar": fake.image_url(),
                },
                "permissions": ["read", "write"],
            }),
        )
        
        slide_update_message = factory.Trait(
            type="slide_update",
            event="modified",
            ack_required=True,
        )


class StreamingResponseFactory(DictFactory):
    """Factory for SSE/streaming response test data."""
    
    event_type = factory.LazyAttribute(
        lambda o: random.choice([
            "progress", "result", "error", "complete", "heartbeat"
        ])
    )
    
    id = factory.Sequence(lambda n: str(n))
    
    data = factory.LazyAttribute(lambda o: _generate_streaming_data(o.event_type))
    
    retry = factory.LazyAttribute(
        lambda o: 5000 if o.event_type == "heartbeat" else None
    )
    
    formatted = factory.LazyAttribute(lambda o: _format_sse_message(o))
    
    class Params:
        progress_event = factory.Trait(
            event_type="progress",
            data=factory.LazyAttribute(lambda o: {
                "step": random.choice(["analyzing", "generating", "optimizing", "finalizing"]),
                "progress": random.randint(0, 100),
                "message": fake.sentence(),
            }),
        )
        
        complete_event = factory.Trait(
            event_type="complete",
            data=factory.LazyAttribute(lambda o: {
                "presentation_id": f"pres_{random.randint(1, 1000)}",
                "slides_count": random.randint(10, 30),
                "duration": random.uniform(5, 60),
            }),
        )


class BatchResponseFactory(DictFactory):
    """Factory for batch API response test data."""
    
    batch_id = factory.LazyAttribute(lambda o: BaseFactory.random_string(16, "batch_"))
    
    operations = factory.LazyAttribute(
        lambda o: [
            {
                "id": f"op_{i}",
                "method": random.choice(["GET", "POST", "PUT", "DELETE"]),
                "path": f"/api/v1/{random.choice(['presentations', 'slides', 'templates'])}/{i}",
                "status": random.choice([200, 201, 400, 404, 500]),
                "response": _generate_response_data(
                    random.choice([200, 201, 400, 404, 500]),
                    f"/api/v1/resource/{i}"
                ),
            }
            for i in range(random.randint(2, 10))
        ]
    )
    
    summary = factory.LazyAttribute(lambda o: {
        "total": len(o.operations),
        "successful": sum(1 for op in o.operations if op["status"] < 400),
        "failed": sum(1 for op in o.operations if op["status"] >= 400),
    })
    
    execution_time_ms = factory.LazyAttribute(
        lambda o: sum(random.randint(10, 100) for _ in o.operations)
    )


def _generate_response_data(status_code: int, endpoint: str) -> Any:
    """Generate response data based on status code and endpoint."""
    
    if status_code >= 400:
        return None
    
    if "/presentations" in endpoint:
        if endpoint.endswith("/presentations"):
            # List response
            return [
                {
                    "id": f"pres_{i}",
                    "title": fake.sentence(nb_words=6)[:-1],
                    "created_at": fake.date_time_between(start_date="-1y").isoformat(),
                    "slide_count": random.randint(5, 30),
                    "status": random.choice(["draft", "published", "archived"]),
                }
                for i in range(random.randint(5, 20))
            ]
        else:
            # Single presentation
            return {
                "id": f"pres_{random.randint(1, 1000)}",
                "title": fake.sentence(nb_words=6)[:-1],
                "description": fake.text(max_nb_chars=200),
                "created_at": fake.date_time_between(start_date="-1y").isoformat(),
                "slides": [
                    {
                        "id": f"slide_{i}",
                        "title": fake.sentence(nb_words=4)[:-1],
                        "type": random.choice(["title", "content", "image", "conclusion"]),
                    }
                    for i in range(random.randint(5, 15))
                ],
            }
    
    elif "/users" in endpoint:
        return {
            "id": f"user_{random.randint(1, 1000)}",
            "email": fake.email(),
            "name": fake.name(),
            "role": random.choice(["user", "admin", "premium"]),
        }
    
    elif "/auth/login" in endpoint:
        return {
            "access_token": BaseFactory.random_string(64),
            "refresh_token": BaseFactory.random_string(64),
            "token_type": "bearer",
            "expires_in": 3600,
        }
    
    else:
        return {"id": BaseFactory.random_string(10), "status": "success"}


def _generate_error_response(status_code: int) -> Dict[str, Any]:
    """Generate error response based on status code."""
    
    error_mappings = {
        400: {
            "code": "BAD_REQUEST",
            "message": "Invalid request parameters",
            "details": [
                {
                    "field": random.choice(["title", "email", "password"]),
                    "message": random.choice([
                        "Field is required",
                        "Invalid format",
                        "Value too long",
                    ]),
                }
            ],
        },
        401: {
            "code": "UNAUTHORIZED",
            "message": "Authentication required",
            "details": "Please provide valid authentication credentials",
        },
        403: {
            "code": "FORBIDDEN",
            "message": "Access denied",
            "details": "You don't have permission to access this resource",
        },
        404: {
            "code": "NOT_FOUND",
            "message": "Resource not found",
            "details": "The requested resource does not exist",
        },
        422: {
            "code": "VALIDATION_ERROR",
            "message": "Validation failed",
            "details": [
                {
                    "loc": ["body", random.choice(["title", "content", "slides"])],
                    "msg": random.choice([
                        "field required",
                        "ensure this value has at least 3 characters",
                        "invalid type",
                    ]),
                    "type": "value_error",
                }
            ],
        },
        500: {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
            "details": "Please try again later or contact support",
        },
    }
    
    return error_mappings.get(status_code, {
        "code": "ERROR",
        "message": f"HTTP {status_code} Error",
    })


def _generate_websocket_payload(msg_type: str, event: str) -> Dict[str, Any]:
    """Generate WebSocket message payload based on type and event."""
    
    payloads = {
        "connection": {
            "connected": {
                "session_id": BaseFactory.random_string(32),
                "server_time": datetime.now(timezone.utc).isoformat(),
            },
            "disconnected": {
                "reason": random.choice(["client_disconnect", "timeout", "error"]),
            },
        },
        "presentation_update": {
            "created": {
                "presentation_id": f"pres_{random.randint(1, 1000)}",
                "title": fake.sentence(nb_words=6)[:-1],
            },
            "updated": {
                "presentation_id": f"pres_{random.randint(1, 1000)}",
                "fields": random.sample(["title", "description", "theme"], random.randint(1, 3)),
            },
        },
        "slide_update": {
            "added": {
                "slide_id": f"slide_{random.randint(1, 1000)}",
                "position": random.randint(1, 20),
            },
            "modified": {
                "slide_id": f"slide_{random.randint(1, 1000)}",
                "changes": random.sample(["content", "layout", "animations"], random.randint(1, 3)),
            },
        },
        "collaboration": {
            "user_joined": {
                "user": {
                    "id": f"user_{random.randint(1, 100)}",
                    "name": fake.name(),
                    "color": fake.hex_color(),
                },
            },
            "cursor_moved": {
                "user_id": f"user_{random.randint(1, 100)}",
                "slide_id": f"slide_{random.randint(1, 20)}",
                "position": {"x": random.uniform(0, 1), "y": random.uniform(0, 1)},
            },
        },
    }
    
    return payloads.get(msg_type, {}).get(event, {"type": msg_type, "event": event})


def _generate_streaming_data(event_type: str) -> Dict[str, Any]:
    """Generate streaming event data based on type."""
    
    if event_type == "progress":
        return {
            "step": random.choice([
                "Analyzing document",
                "Extracting content",
                "Generating slides",
                "Applying styles",
                "Optimizing layout",
            ]),
            "progress": random.randint(0, 100),
            "estimated_time_remaining": random.randint(0, 60),
        }
    
    elif event_type == "result":
        return {
            "slide_id": f"slide_{random.randint(1, 100)}",
            "content": fake.text(max_nb_chars=200),
            "confidence": random.uniform(0.7, 1.0),
        }
    
    elif event_type == "error":
        return {
            "code": "PROCESSING_ERROR",
            "message": "Failed to process content",
            "details": fake.sentence(),
        }
    
    elif event_type == "complete":
        return {
            "status": "success",
            "total_slides": random.randint(10, 30),
            "processing_time": random.uniform(5, 60),
        }
    
    else:
        return {"timestamp": datetime.now(timezone.utc).isoformat()}


def _format_sse_message(event: Dict[str, Any]) -> str:
    """Format event as SSE message."""
    lines = []
    
    if event.get("id"):
        lines.append(f"id: {event['id']}")
    
    if event.get("event_type"):
        lines.append(f"event: {event['event_type']}")
    
    if event.get("retry"):
        lines.append(f"retry: {event['retry']}")
    
    if event.get("data"):
        data_str = json.dumps(event["data"]) if isinstance(event["data"], dict) else str(event["data"])
        lines.append(f"data: {data_str}")
    
    lines.append("")  # Empty line to end message
    
    return "\n".join(lines)