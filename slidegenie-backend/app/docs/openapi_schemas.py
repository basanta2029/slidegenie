"""
Custom OpenAPI schemas and examples for SlideGenie API.

This module defines reusable schemas, error responses, and data models
used throughout the OpenAPI documentation.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standardized error response schema."""
    
    class ErrorDetail(BaseModel):
        code: str = Field(..., description="Machine-readable error code")
        message: str = Field(..., description="Human-readable error message")
        details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
        request_id: Optional[str] = Field(None, description="Unique request identifier for debugging")
        timestamp: Optional[datetime] = Field(None, description="Error timestamp")
    
    error: ErrorDetail


class ValidationError(BaseModel):
    """Validation error response schema."""
    
    class ValidationDetail(BaseModel):
        field: str = Field(..., description="Field name that failed validation")
        message: str = Field(..., description="Validation error message")
        code: str = Field(..., description="Validation error code")
    
    class ValidationErrorDetail(BaseModel):
        code: str = Field("VALIDATION_ERROR", description="Error code")
        message: str = Field(..., description="General validation error message")
        details: Dict[str, Any] = Field(..., description="Validation details")
        field_errors: List[ValidationDetail] = Field(..., description="Field-specific errors")
    
    error: ValidationErrorDetail


class RateLimitError(BaseModel):
    """Rate limit error response schema."""
    
    class RateLimitDetail(BaseModel):
        code: str = Field("RATE_LIMIT_EXCEEDED", description="Error code")
        message: str = Field(..., description="Rate limit error message")
        details: Dict[str, Any] = Field(..., description="Rate limit details")
        limit: int = Field(..., description="Rate limit threshold")
        remaining: int = Field(..., description="Remaining requests")
        reset_at: datetime = Field(..., description="When rate limit resets")
    
    error: RateLimitDetail


class PaginationMeta(BaseModel):
    """Pagination metadata schema."""
    page: int = Field(..., ge=1, description="Current page number")
    per_page: int = Field(..., ge=1, le=100, description="Items per page")
    total: int = Field(..., ge=0, description="Total number of items")
    pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")
    next_page: Optional[int] = Field(None, description="Next page number")
    prev_page: Optional[int] = Field(None, description="Previous page number")


class PaginatedResponse(BaseModel):
    """Generic paginated response schema."""
    data: List[Dict[str, Any]] = Field(..., description="List of items")
    meta: PaginationMeta = Field(..., description="Pagination metadata")


class RateLimitHeaders(BaseModel):
    """Rate limiting headers schema."""
    x_ratelimit_limit: int = Field(..., alias="X-RateLimit-Limit", description="Request limit per time window")
    x_ratelimit_remaining: int = Field(..., alias="X-RateLimit-Remaining", description="Remaining requests")
    x_ratelimit_reset: int = Field(..., alias="X-RateLimit-Reset", description="Reset time (Unix timestamp)")
    x_ratelimit_retry_after: Optional[int] = Field(None, alias="X-RateLimit-Retry-After", description="Retry after seconds")


class HealthStatus(BaseModel):
    """Health check response schema."""
    status: str = Field(..., description="Overall system status")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Environment name")
    timestamp: datetime = Field(..., description="Health check timestamp")
    
    class ComponentStatus(BaseModel):
        name: str = Field(..., description="Component name")
        status: str = Field(..., description="Component status")
        details: Optional[Dict[str, Any]] = Field(None, description="Component details")
    
    components: Optional[List[ComponentStatus]] = Field(None, description="Individual component statuses")


class WebhookEvent(BaseModel):
    """Webhook event schema."""
    event: str = Field(..., description="Event type")
    data: Dict[str, Any] = Field(..., description="Event data")
    timestamp: datetime = Field(..., description="Event timestamp")
    signature: str = Field(..., description="HMAC signature for verification")
    delivery_id: str = Field(..., description="Unique delivery identifier")
    attempt: int = Field(1, description="Delivery attempt number")


class WebSocketMessage(BaseModel):
    """WebSocket message schema."""
    type: str = Field(..., description="Message type")
    data: Optional[Dict[str, Any]] = Field(None, description="Message payload")
    timestamp: datetime = Field(..., description="Message timestamp")
    request_id: Optional[str] = Field(None, description="Request correlation ID")


class ProgressMessage(WebSocketMessage):
    """Progress update WebSocket message."""
    type: str = Field("progress", description="Message type")
    
    class ProgressData(BaseModel):
        job_id: UUID = Field(..., description="Job identifier")
        stage: str = Field(..., description="Current processing stage")
        progress: float = Field(..., ge=0, le=100, description="Progress percentage")
        message: str = Field(..., description="Progress message")
        details: Optional[Dict[str, Any]] = Field(None, description="Additional progress details")
        estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
    
    data: ProgressData


class CollaborationMessage(WebSocketMessage):
    """Collaboration WebSocket message."""
    type: str = Field("collaboration", description="Message type")
    
    class CollaborationData(BaseModel):
        presentation_id: UUID = Field(..., description="Presentation ID")
        user_id: UUID = Field(..., description="User making the change")
        action: str = Field(..., description="Collaboration action type")
        slide_id: Optional[str] = Field(None, description="Affected slide ID")
        changes: Optional[Dict[str, Any]] = Field(None, description="Changes made")
        cursor_position: Optional[Dict[str, Any]] = Field(None, description="User cursor position")
        selection: Optional[Dict[str, Any]] = Field(None, description="User selection")
    
    data: CollaborationData


class FileUploadResponse(BaseModel):
    """File upload response schema."""
    file_id: UUID = Field(..., description="Uploaded file identifier")
    filename: str = Field(..., description="Original filename")
    size: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="MIME content type")
    upload_url: str = Field(..., description="File access URL")
    processing_status: str = Field(..., description="File processing status")
    
    class FileMetadata(BaseModel):
        pages: Optional[int] = Field(None, description="Number of pages (for documents)")
        word_count: Optional[int] = Field(None, description="Word count")
        language: Optional[str] = Field(None, description="Detected language")
        has_citations: Optional[bool] = Field(None, description="Whether citations were detected")
        academic_format: Optional[str] = Field(None, description="Detected academic format")
    
    metadata: Optional[FileMetadata] = Field(None, description="File metadata")
    created_at: datetime = Field(..., description="Upload timestamp")


class GenerationJobResponse(BaseModel):
    """Generation job response schema."""
    job_id: UUID = Field(..., description="Generation job identifier")
    status: str = Field(..., description="Job status")
    presentation_id: Optional[UUID] = Field(None, description="Generated presentation ID")
    
    class GenerationProgress(BaseModel):
        stage: str = Field(..., description="Current processing stage")
        progress: float = Field(..., ge=0, le=100, description="Progress percentage")
        message: str = Field(..., description="Current status message")
        estimated_completion: Optional[datetime] = Field(None, description="Estimated completion")
    
    progress: Optional[GenerationProgress] = Field(None, description="Current progress")
    
    class GenerationResult(BaseModel):
        slides_generated: int = Field(..., description="Number of slides generated")
        processing_time_ms: int = Field(..., description="Total processing time")
        ai_model_used: str = Field(..., description="AI model used for generation")
        tokens_consumed: int = Field(..., description="AI tokens consumed")
        quality_score: Optional[float] = Field(None, description="Generated content quality score")
    
    result: Optional[GenerationResult] = Field(None, description="Generation results")
    created_at: datetime = Field(..., description="Job creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    expires_at: Optional[datetime] = Field(None, description="Job expiration time")


class ExportJobResponse(BaseModel):
    """Export job response schema."""
    export_id: UUID = Field(..., description="Export job identifier")
    presentation_id: UUID = Field(..., description="Source presentation ID")
    format: str = Field(..., description="Export format")
    status: str = Field(..., description="Export status")
    
    class ExportResult(BaseModel):
        download_url: str = Field(..., description="Download URL for exported file")
        file_size: int = Field(..., description="Exported file size in bytes")
        expires_at: datetime = Field(..., description="Download URL expiration")
        checksum: str = Field(..., description="File checksum for integrity verification")
    
    result: Optional[ExportResult] = Field(None, description="Export results")
    created_at: datetime = Field(..., description="Export job creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Export completion timestamp")


class PresentationSummary(BaseModel):
    """Presentation summary schema for list responses."""
    id: UUID = Field(..., description="Presentation identifier")
    title: str = Field(..., description="Presentation title")
    description: Optional[str] = Field(None, description="Presentation description")
    status: str = Field(..., description="Presentation status")
    slides_count: int = Field(..., description="Number of slides")
    template_id: Optional[UUID] = Field(None, description="Template used")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    tags: List[str] = Field([], description="Presentation tags")
    
    class PresentationStats(BaseModel):
        views: int = Field(0, description="Number of views")
        exports: int = Field(0, description="Number of exports")
        collaborators: int = Field(0, description="Number of collaborators")
        last_accessed: Optional[datetime] = Field(None, description="Last access timestamp")
    
    stats: Optional[PresentationStats] = Field(None, description="Presentation statistics")


class UserProfile(BaseModel):
    """User profile schema."""
    id: UUID = Field(..., description="User identifier")
    email: str = Field(..., description="User email address")
    first_name: str = Field(..., description="User first name")
    last_name: str = Field(..., description="User last name")
    institution: Optional[str] = Field(None, description="Academic institution")
    department: Optional[str] = Field(None, description="Department or field of study")
    role: str = Field(..., description="User role")
    is_verified: bool = Field(..., description="Email verification status")
    is_active: bool = Field(..., description="Account active status")
    
    class UserPreferences(BaseModel):
        default_template: Optional[UUID] = Field(None, description="Default presentation template")
        ai_model_preference: Optional[str] = Field(None, description="Preferred AI model")
        export_format_preference: Optional[str] = Field(None, description="Preferred export format")
        collaboration_notifications: bool = Field(True, description="Collaboration notifications enabled")
        email_notifications: bool = Field(True, description="Email notifications enabled")
    
    preferences: Optional[UserPreferences] = Field(None, description="User preferences")
    created_at: datetime = Field(..., description="Account creation timestamp")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")


class TemplateSummary(BaseModel):
    """Template summary schema."""
    id: UUID = Field(..., description="Template identifier")
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    category: str = Field(..., description="Template category")
    is_public: bool = Field(..., description="Whether template is publicly available")
    is_default: bool = Field(..., description="Whether this is a default template")
    
    class TemplatePreview(BaseModel):
        thumbnail_url: str = Field(..., description="Template thumbnail image URL")
        color_scheme: List[str] = Field(..., description="Template color palette")
        font_family: str = Field(..., description="Primary font family")
        layout_style: str = Field(..., description="Layout style description")
    
    preview: TemplatePreview = Field(..., description="Template preview information")
    usage_count: int = Field(0, description="Number of times used")
    rating: Optional[float] = Field(None, description="Average user rating")
    created_at: datetime = Field(..., description="Template creation timestamp")


class APIKeyInfo(BaseModel):
    """API key information schema."""
    id: UUID = Field(..., description="API key identifier")
    name: str = Field(..., description="API key name/description")
    key_preview: str = Field(..., description="Masked API key (showing only last 4 characters)")
    permissions: List[str] = Field(..., description="API key permissions")
    rate_limit: int = Field(..., description="Requests per hour limit")
    created_at: datetime = Field(..., description="API key creation timestamp")
    last_used: Optional[datetime] = Field(None, description="Last usage timestamp")
    expires_at: Optional[datetime] = Field(None, description="API key expiration")
    is_active: bool = Field(..., description="Whether API key is active")


# Common response schemas for different HTTP status codes
class HTTPSuccessResponse(BaseModel):
    """HTTP 2xx success response."""
    success: bool = Field(True, description="Operation success status")
    message: Optional[str] = Field(None, description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")


class HTTPCreatedResponse(BaseModel):
    """HTTP 201 created response."""
    success: bool = Field(True, description="Creation success status")
    message: str = Field(..., description="Creation success message")
    data: Dict[str, Any] = Field(..., description="Created resource data")
    resource_id: Union[str, UUID] = Field(..., description="Created resource identifier")


class HTTPAcceptedResponse(BaseModel):
    """HTTP 202 accepted response for async operations."""
    success: bool = Field(True, description="Request acceptance status")
    message: str = Field(..., description="Acceptance message")
    job_id: UUID = Field(..., description="Background job identifier")
    status_url: str = Field(..., description="URL to check operation status")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")


class HTTPNoContentResponse(BaseModel):
    """HTTP 204 no content response."""
    pass  # No content for 204 responses