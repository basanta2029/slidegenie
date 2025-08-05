"""
API request and response examples for OpenAPI documentation.

This module provides comprehensive examples for all API endpoints,
including success responses, error cases, and edge cases.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List
from uuid import uuid4


class APIExamples:
    """
    Centralized API examples for OpenAPI documentation.
    """

    def __init__(self):
        """Initialize with common example data."""
        self.base_timestamp = datetime.utcnow()
        self.example_user_id = str(uuid4())
        self.example_presentation_id = str(uuid4())
        self.example_job_id = str(uuid4())

    # Authentication Examples
    def get_auth_register_example(self) -> Dict[str, Any]:
        """User registration examples."""
        return {
            "request": {
                "email": "john.doe@university.edu",
                "password": "SecurePassword123!",
                "first_name": "John",
                "last_name": "Doe",
                "institution": "University of Example",
                "department": "Computer Science",
                "terms_accepted": True
            },
            "response": {
                "success": True,
                "message": "Registration successful. Please check your email for verification.",
                "data": {
                    "user": {
                        "id": self.example_user_id,
                        "email": "john.doe@university.edu",
                        "first_name": "John",
                        "last_name": "Doe",
                        "institution": "University of Example",
                        "department": "Computer Science",
                        "role": "student",
                        "is_verified": False,
                        "is_active": True,
                        "created_at": self.base_timestamp.isoformat()
                    },
                    "tokens": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                        "expires_in": 1800,
                        "refresh_expires_in": 604800
                    }
                }
            }
        }

    def get_auth_login_example(self) -> Dict[str, Any]:
        """User login examples."""
        return {
            "request": {
                "email": "john.doe@university.edu",
                "password": "SecurePassword123!"
            },
            "response": {
                "success": True,
                "message": "Login successful",
                "data": {
                    "user": {
                        "id": self.example_user_id,
                        "email": "john.doe@university.edu",
                        "first_name": "John",
                        "last_name": "Doe",
                        "institution": "University of Example",
                        "role": "student",
                        "last_login": self.base_timestamp.isoformat()
                    },
                    "tokens": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                        "expires_in": 1800,
                        "refresh_expires_in": 604800
                    }
                }
            }
        }

    def get_auth_refresh_example(self) -> Dict[str, Any]:
        """Token refresh examples."""
        return {
            "request": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            },
            "response": {
                "success": True,
                "message": "Token refreshed successfully",
                "data": {
                    "tokens": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                        "expires_in": 1800,
                        "refresh_expires_in": 604800
                    }
                }
            }
        }

    # Presentation Examples
    def get_presentations_list_example(self) -> Dict[str, Any]:
        """Presentations list examples."""
        return {
            "response": {
                "success": True,
                "data": [
                    {
                        "id": self.example_presentation_id,
                        "title": "Machine Learning in Healthcare",
                        "description": "Exploring AI applications in medical diagnosis",
                        "status": "completed",
                        "slides_count": 15,
                        "template_id": str(uuid4()),
                        "created_at": self.base_timestamp.isoformat(),
                        "updated_at": self.base_timestamp.isoformat(),
                        "tags": ["ai", "healthcare", "research"],
                        "stats": {
                            "views": 42,
                            "exports": 3,
                            "collaborators": 2,
                            "last_accessed": self.base_timestamp.isoformat()
                        }
                    },
                    {
                        "id": str(uuid4()),
                        "title": "Climate Change Data Analysis",
                        "description": "Statistical analysis of climate trends",
                        "status": "draft",
                        "slides_count": 8,
                        "template_id": str(uuid4()),
                        "created_at": (self.base_timestamp - timedelta(days=3)).isoformat(),
                        "updated_at": (self.base_timestamp - timedelta(hours=2)).isoformat(),
                        "tags": ["climate", "statistics", "environment"],
                        "stats": {
                            "views": 12,
                            "exports": 0,
                            "collaborators": 1,
                            "last_accessed": (self.base_timestamp - timedelta(hours=2)).isoformat()
                        }
                    }
                ],
                "meta": {
                    "page": 1,
                    "per_page": 20,
                    "total": 2,
                    "pages": 1,
                    "has_next": False,
                    "has_prev": False,
                    "next_page": None,
                    "prev_page": None
                }
            }
        }

    def get_presentations_create_example(self) -> Dict[str, Any]:
        """Create presentation examples."""
        return {
            "request": {
                "title": "Quantum Computing Fundamentals",
                "description": "Introduction to quantum computing principles",
                "template_id": str(uuid4()),
                "tags": ["quantum", "computing", "physics"],
                "settings": {
                    "auto_generate_outline": True,
                    "citation_style": "APA",
                    "slide_transition": "fade",
                    "theme_color": "#1976d2"
                }
            },
            "response": {
                "success": True,
                "message": "Presentation created successfully",
                "data": {
                    "id": self.example_presentation_id,
                    "title": "Quantum Computing Fundamentals",
                    "description": "Introduction to quantum computing principles",
                    "status": "draft",
                    "slides_count": 0,
                    "template_id": str(uuid4()),
                    "created_at": self.base_timestamp.isoformat(),
                    "updated_at": self.base_timestamp.isoformat(),
                    "tags": ["quantum", "computing", "physics"],
                    "owner_id": self.example_user_id,
                    "settings": {
                        "auto_generate_outline": True,
                        "citation_style": "APA",
                        "slide_transition": "fade",
                        "theme_color": "#1976d2"
                    }
                }
            }
        }

    def get_presentations_get_example(self) -> Dict[str, Any]:
        """Get single presentation examples."""
        return {
            "response": {
                "success": True,
                "data": {
                    "id": self.example_presentation_id,
                    "title": "Machine Learning in Healthcare",
                    "description": "Exploring AI applications in medical diagnosis",
                    "status": "completed",
                    "slides_count": 15,
                    "template_id": str(uuid4()),
                    "created_at": self.base_timestamp.isoformat(),
                    "updated_at": self.base_timestamp.isoformat(),
                    "tags": ["ai", "healthcare", "research"],
                    "owner_id": self.example_user_id,
                    "slides": [
                        {
                            "id": "slide-1",
                            "title": "Introduction to AI in Healthcare",
                            "content": {
                                "type": "title_slide",
                                "title": "Machine Learning in Healthcare",
                                "subtitle": "Revolutionizing Medical Diagnosis",
                                "author": "John Doe",
                                "institution": "University of Example"
                            },
                            "position": 1,
                            "layout": "title_slide"
                        },
                        {
                            "id": "slide-2",
                            "title": "Current Challenges",
                            "content": {
                                "type": "bullet_points",
                                "title": "Current Challenges in Medical Diagnosis",
                                "points": [
                                    "Diagnostic accuracy varies by physician experience",
                                    "Time-consuming manual analysis of medical images",
                                    "Limited access to specialists in rural areas",
                                    "High healthcare costs due to misdiagnosis"
                                ]
                            },
                            "position": 2,
                            "layout": "bullet_points"
                        }
                    ],
                    "collaborators": [
                        {
                            "user_id": str(uuid4()),
                            "email": "collaborator@university.edu",
                            "permission": "edit",
                            "joined_at": self.base_timestamp.isoformat()
                        }
                    ],
                    "export_history": [
                        {
                            "format": "pptx",
                            "exported_at": self.base_timestamp.isoformat(),
                            "file_size": 2048576
                        }
                    ]
                }
            }
        }

    # Generation Examples
    def get_generation_create_example(self) -> Dict[str, Any]:
        """Create generation job examples."""
        return {
            "request": {
                "source_type": "document",
                "source_id": str(uuid4()),
                "presentation_title": "Research Paper Analysis",
                "template_id": str(uuid4()),
                "generation_options": {
                    "max_slides": 20,
                    "include_references": True,
                    "slide_style": "academic",
                    "citation_format": "APA",
                    "ai_model": "claude-3-5-sonnet-20241022",
                    "content_focus": "key_findings",
                    "audience_level": "graduate"
                }
            },
            "response": {
                "success": True,
                "message": "Generation job created successfully",
                "data": {
                    "job_id": self.example_job_id,
                    "status": "queued",
                    "presentation_id": None,
                    "progress": {
                        "stage": "initializing",
                        "progress": 0.0,
                        "message": "Job queued for processing",
                        "estimated_completion": (self.base_timestamp + timedelta(minutes=5)).isoformat()
                    },
                    "created_at": self.base_timestamp.isoformat(),
                    "updated_at": self.base_timestamp.isoformat(),
                    "expires_at": (self.base_timestamp + timedelta(hours=24)).isoformat()
                }
            }
        }

    def get_generation_status_example(self) -> Dict[str, Any]:
        """Generation job status examples."""
        return {
            "response": {
                "success": True,
                "data": {
                    "job_id": self.example_job_id,
                    "status": "processing",
                    "presentation_id": None,
                    "progress": {
                        "stage": "content_analysis",
                        "progress": 45.0,
                        "message": "Analyzing document structure and extracting key concepts",
                        "estimated_completion": (self.base_timestamp + timedelta(minutes=3)).isoformat()
                    },
                    "created_at": self.base_timestamp.isoformat(),
                    "updated_at": self.base_timestamp.isoformat(),
                    "processing_logs": [
                        {
                            "timestamp": self.base_timestamp.isoformat(),
                            "stage": "document_parsing",
                            "message": "Document parsed successfully: 25 pages, 8,453 words"
                        },
                        {
                            "timestamp": (self.base_timestamp + timedelta(seconds=30)).isoformat(),
                            "stage": "content_analysis",
                            "message": "Identified 5 main sections and 23 key concepts"
                        }
                    ]
                }
            }
        }

    # Document Upload Examples
    def get_document_upload_example(self) -> Dict[str, Any]:
        """Document upload examples."""
        return {
            "request": {
                "file": "binary_file_data",
                "filename": "research_paper.pdf",
                "content_type": "application/pdf",
                "processing_options": {
                    "extract_citations": True,
                    "detect_sections": True,
                    "parse_equations": True,
                    "extract_figures": True
                }
            },
            "response": {
                "success": True,
                "message": "File uploaded and processing started",
                "data": {
                    "file_id": str(uuid4()),
                    "filename": "research_paper.pdf",
                    "size": 2048576,
                    "content_type": "application/pdf",
                    "upload_url": f"https://storage.slidegenie.com/uploads/{uuid4()}/research_paper.pdf",
                    "processing_status": "processing",
                    "metadata": {
                        "pages": 25,
                        "word_count": 8453,
                        "language": "en",
                        "has_citations": True,
                        "academic_format": "research_paper"
                    },
                    "created_at": self.base_timestamp.isoformat(),
                    "processing_job_id": str(uuid4())
                }
            }
        }

    # Export Examples
    def get_export_create_example(self) -> Dict[str, Any]:
        """Export creation examples."""
        return {
            "request": {
                "format": "pptx",
                "options": {
                    "include_notes": True,
                    "theme": "professional",
                    "slide_size": "16:9",
                    "export_quality": "high",
                    "include_animations": False
                }
            },
            "response": {
                "success": True,
                "message": "Export job created successfully",
                "data": {
                    "export_id": str(uuid4()),
                    "presentation_id": self.example_presentation_id,
                    "format": "pptx",
                    "status": "processing",
                    "created_at": self.base_timestamp.isoformat(),
                    "estimated_completion": (self.base_timestamp + timedelta(minutes=2)).isoformat()
                }
            }
        }

    def get_export_status_example(self) -> Dict[str, Any]:
        """Export status examples."""
        return {
            "response": {
                "success": True,
                "data": {
                    "export_id": str(uuid4()),
                    "presentation_id": self.example_presentation_id,
                    "format": "pptx",
                    "status": "completed",
                    "result": {
                        "download_url": f"https://storage.slidegenie.com/exports/{uuid4()}/presentation.pptx",
                        "file_size": 5242880,
                        "expires_at": (self.base_timestamp + timedelta(days=7)).isoformat(),
                        "checksum": "sha256:a1b2c3d4e5f6..."
                    },
                    "created_at": self.base_timestamp.isoformat(),
                    "completed_at": self.base_timestamp.isoformat()
                }
            }
        }

    # Template Examples
    def get_templates_list_example(self) -> Dict[str, Any]:
        """Templates list examples."""
        return {
            "response": {
                "success": True,
                "data": [
                    {
                        "id": str(uuid4()),
                        "name": "Academic Research",
                        "description": "Professional template for academic research presentations",
                        "category": "academic",
                        "is_public": True,
                        "is_default": True,
                        "preview": {
                            "thumbnail_url": "https://cdn.slidegenie.com/templates/academic-research/thumb.png",
                            "color_scheme": ["#1976d2", "#ffffff", "#f5f5f5", "#333333"],
                            "font_family": "Inter",
                            "layout_style": "Clean and professional with emphasis on content hierarchy"
                        },
                        "usage_count": 1250,
                        "rating": 4.8,
                        "created_at": self.base_timestamp.isoformat()
                    },
                    {
                        "id": str(uuid4()),
                        "name": "Conference Presentation",
                        "description": "Dynamic template for conference presentations",
                        "category": "conference",
                        "is_public": True,
                        "is_default": False,
                        "preview": {
                            "thumbnail_url": "https://cdn.slidegenie.com/templates/conference/thumb.png",
                            "color_scheme": ["#e91e63", "#ffffff", "#fce4ec", "#212121"],
                            "font_family": "Roboto",
                            "layout_style": "Modern and engaging with visual emphasis"
                        },
                        "usage_count": 892,
                        "rating": 4.6,
                        "created_at": self.base_timestamp.isoformat()
                    }
                ],
                "meta": {
                    "page": 1,
                    "per_page": 20,
                    "total": 2,
                    "pages": 1,
                    "has_next": False,
                    "has_prev": False
                }
            }
        }

    # User Examples
    def get_user_profile_example(self) -> Dict[str, Any]:
        """User profile examples."""
        return {
            "response": {
                "success": True,
                "data": {
                    "id": self.example_user_id,
                    "email": "john.doe@university.edu",
                    "first_name": "John",
                    "last_name": "Doe",
                    "institution": "University of Example",
                    "department": "Computer Science",
                    "role": "student",
                    "is_verified": True,
                    "is_active": True,
                    "preferences": {
                        "default_template": str(uuid4()),
                        "ai_model_preference": "claude-3-5-sonnet-20241022",
                        "export_format_preference": "pptx",
                        "collaboration_notifications": True,
                        "email_notifications": True
                    },
                    "created_at": self.base_timestamp.isoformat(),
                    "last_login": self.base_timestamp.isoformat(),
                    "usage_stats": {
                        "presentations_created": 15,
                        "slides_generated": 245,
                        "exports_completed": 28,
                        "storage_used_mb": 156.7,
                        "ai_tokens_used": 125000
                    }
                }
            }
        }

    # WebSocket Examples
    def get_websocket_progress_example(self) -> Dict[str, Any]:
        """WebSocket progress message examples."""
        return {
            "type": "progress",
            "data": {
                "job_id": self.example_job_id,
                "stage": "slide_generation",
                "progress": 65.0,
                "message": "Generating slide 8 of 12: Results and Analysis",
                "details": {
                    "current_slide": 8,
                    "total_slides": 12,
                    "slides_completed": 7,
                    "ai_model": "claude-3-5-sonnet-20241022",
                    "tokens_used": 8500
                },
                "estimated_completion": (self.base_timestamp + timedelta(minutes=2)).isoformat()
            },
            "timestamp": self.base_timestamp.isoformat(),
            "request_id": str(uuid4())[:8]
        }

    def get_websocket_collaboration_example(self) -> Dict[str, Any]:
        """WebSocket collaboration message examples."""
        return {
            "type": "collaboration",
            "data": {
                "presentation_id": self.example_presentation_id,
                "user_id": str(uuid4()),
                "action": "edit",
                "slide_id": "slide-3",
                "changes": {
                    "title": "Updated Title: Advanced Machine Learning Applications",
                    "content": {
                        "points": [
                            "Neural networks for image classification",
                            "Natural language processing for medical records",
                            "Predictive modeling for patient outcomes"
                        ]
                    }
                },
                "cursor_position": {
                    "slide_id": "slide-3",
                    "element": "title",
                    "position": 25
                }
            },
            "timestamp": self.base_timestamp.isoformat(),
            "request_id": str(uuid4())[:8]
        }

    # Webhook Examples
    def get_webhook_example(self, event_type: str) -> Dict[str, Any]:
        """Webhook event examples."""
        if event_type == "generation.complete":
            return {
                "event": "generation.complete",
                "data": {
                    "presentation_id": self.example_presentation_id,
                    "user_id": self.example_user_id,
                    "status": "completed",
                    "slides_count": 15,
                    "generation_time_ms": 42500,
                    "download_url": f"https://api.slidegenie.com/api/v1/presentations/{self.example_presentation_id}/download"
                },
                "timestamp": self.base_timestamp.isoformat(),
                "signature": "sha256=a1b2c3d4e5f6...",
                "delivery_id": str(uuid4()),
                "attempt": 1
            }
        elif event_type == "export.ready":
            return {
                "event": "export.ready",
                "data": {
                    "export_id": str(uuid4()),
                    "presentation_id": self.example_presentation_id,
                    "format": "pptx",
                    "download_url": f"https://storage.slidegenie.com/exports/{uuid4()}/presentation.pptx",
                    "expires_at": (self.base_timestamp + timedelta(days=7)).isoformat()
                },
                "timestamp": self.base_timestamp.isoformat(),
                "signature": "sha256=a1b2c3d4e5f6...",
                "delivery_id": str(uuid4()),
                "attempt": 1
            }

    # Error Examples
    def get_error_example(self, error_code: str) -> Dict[str, Any]:
        """Standard error response examples."""
        error_examples = {
            "INVALID_REQUEST": {
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "The request data is invalid or malformed",
                    "details": {
                        "invalid_fields": ["email", "password"]
                    },
                    "request_id": str(uuid4())[:8],
                    "timestamp": self.base_timestamp.isoformat()
                }
            },
            "UNAUTHORIZED": {
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Authentication required. Please provide a valid access token.",
                    "details": {
                        "auth_method": "bearer_token"
                    },
                    "request_id": str(uuid4())[:8],
                    "timestamp": self.base_timestamp.isoformat()
                }
            },
            "FORBIDDEN": {
                "error": {
                    "code": "FORBIDDEN",
                    "message": "You don't have permission to access this resource",
                    "details": {
                        "required_permissions": ["presentations:read"],
                        "user_permissions": ["presentations:create"]
                    },
                    "request_id": str(uuid4())[:8],
                    "timestamp": self.base_timestamp.isoformat()
                }
            },
            "NOT_FOUND": {
                "error": {
                    "code": "NOT_FOUND",
                    "message": "The requested resource was not found",
                    "details": {
                        "resource_type": "presentation",
                        "resource_id": self.example_presentation_id
                    },
                    "request_id": str(uuid4())[:8],
                    "timestamp": self.base_timestamp.isoformat()
                }
            },
            "INTERNAL_ERROR": {
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An internal server error occurred",
                    "request_id": str(uuid4())[:8],
                    "timestamp": self.base_timestamp.isoformat()
                }
            }
        }
        
        return error_examples.get(error_code, error_examples["INTERNAL_ERROR"])

    def get_validation_error_example(self) -> Dict[str, Any]:
        """Validation error examples."""
        return {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": {
                    "field_errors": [
                        {
                            "field": "email",
                            "message": "Invalid email format",
                            "code": "invalid_email"
                        },
                        {
                            "field": "password",
                            "message": "Password must be at least 8 characters long",
                            "code": "min_length"
                        },
                        {
                            "field": "institution",
                            "message": "Institution is required for academic users",
                            "code": "required"
                        }
                    ]
                },
                "request_id": str(uuid4())[:8],
                "timestamp": self.base_timestamp.isoformat()
            }
        }

    def get_rate_limit_error_example(self) -> Dict[str, Any]:
        """Rate limit error examples."""
        return {
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Rate limit exceeded. Please try again later.",
                "details": {
                    "limit": 100,
                    "remaining": 0,
                    "reset_at": (self.base_timestamp + timedelta(hours=1)).isoformat(),
                    "retry_after": 3600
                },
                "request_id": str(uuid4())[:8],
                "timestamp": self.base_timestamp.isoformat()
            }
        }

    # Health Check Examples
    def get_health_check_example(self) -> Dict[str, Any]:
        """Health check examples."""
        return {
            "response": {
                "status": "healthy",
                "version": "1.0.0",
                "environment": "production",
                "timestamp": self.base_timestamp.isoformat(),
                "components": [
                    {
                        "name": "database",
                        "status": "healthy",
                        "details": {
                            "connection_pool": "8/20 connections",
                            "response_time_ms": 15
                        }
                    },
                    {
                        "name": "redis",
                        "status": "healthy",
                        "details": {
                            "memory_usage": "45MB",
                            "response_time_ms": 2
                        }
                    },
                    {
                        "name": "ai_services",
                        "status": "healthy",
                        "details": {
                            "anthropic_api": "available",
                            "openai_api": "available",
                            "response_time_ms": 250
                        }
                    },
                    {
                        "name": "storage",
                        "status": "healthy",
                        "details": {
                            "s3_bucket": "accessible",
                            "free_space": "2.5TB"
                        }
                    }
                ]
            }
        }