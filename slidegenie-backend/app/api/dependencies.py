"""
Common API dependencies for the SlideGenie API.

This module provides reusable dependency functions for FastAPI endpoints including:
- Authentication and authorization
- Request validation
- Rate limiting
- Pagination
- Database sessions
- Redis connections
- File upload handling
"""

import re
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID

from fastapi import Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.exceptions import (
    AuthenticationException,
    AuthorizationException,
    FileTooLargeException,
    InvalidParameterException,
    RateLimitExceededException,
    UnsupportedFileTypeException,
    ValidationException,
)
from app.core.config import settings
from app.core.security import decode_token
from app.infrastructure.cache.redis import get_redis
from app.infrastructure.database.base import get_db
from app.infrastructure.database.models import User
from app.repositories.user import UserRepository

# Security
security = HTTPBearer(auto_error=False)


# Pagination Models

class PaginationParams(BaseModel):
    """Pagination parameters model."""
    
    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    size: int = Field(
        default=settings.DEFAULT_PAGE_SIZE,
        ge=1,
        le=settings.MAX_PAGE_SIZE,
        description=f"Page size (max: {settings.MAX_PAGE_SIZE})"
    )
    
    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.size
    
    @property
    def limit(self) -> int:
        """Get limit for database queries."""
        return self.size


class PaginationResponse(BaseModel):
    """Pagination response metadata."""
    
    page: int
    size: int
    total: int
    pages: int
    has_next: bool
    has_prev: bool


# Sorting Models

class SortParams(BaseModel):
    """Sorting parameters model."""
    
    sort_by: Optional[str] = Field(default=None, description="Field to sort by")
    sort_order: str = Field(default="asc", pattern="^(asc|desc)$", description="Sort order")
    
    @validator("sort_by")
    def validate_sort_by(cls, v):
        """Validate sort field."""
        if v is None:
            return v
        
        # Only allow alphanumeric characters and underscores
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", v):
            raise ValueError("Invalid sort field format")
        
        return v


# File Upload Models

class FileUploadParams(BaseModel):
    """File upload parameters."""
    
    max_size_mb: int = Field(default=settings.MAX_UPLOAD_SIZE_MB)
    allowed_extensions: List[str] = Field(default=settings.ALLOWED_UPLOAD_EXTENSIONS)
    allow_multiple: bool = Field(default=False)


# Authentication Dependencies

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP authorization credentials
        db: Database session
        
    Returns:
        Current authenticated user
        
    Raises:
        AuthenticationException: If authentication fails
    """
    if not credentials:
        raise AuthenticationException("Authentication credentials required")
    
    # Decode token
    payload = decode_token(credentials.credentials)
    if not payload:
        raise AuthenticationException("Invalid or expired token")
    
    # Check token type
    if payload.get("type") != "access":
        raise AuthenticationException("Invalid token type")
    
    # Get user
    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationException("Invalid token payload")
    
    user_repo = UserRepository(db)
    user = await user_repo.get(user_id)
    
    if not user:
        raise AuthenticationException("User not found")
    
    if not user.is_active:
        raise AuthorizationException("User account is inactive")
    
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Get current authenticated user from JWT token (optional).
    
    Args:
        credentials: HTTP authorization credentials (optional)
        db: Database session
        
    Returns:
        Current authenticated user or None
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except (AuthenticationException, AuthorizationException):
        return None


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current active user.
    
    Args:
        current_user: Current user from authentication
        
    Returns:
        Active user
        
    Raises:
        AuthorizationException: If user is not active
    """
    if not current_user.is_active:
        raise AuthorizationException("User account is inactive")
    
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current admin user.
    
    Args:
        current_user: Current user from authentication
        
    Returns:
        Admin user
        
    Raises:
        AuthorizationException: If user is not an admin
    """
    if current_user.role != "admin":
        raise AuthorizationException(
            "Administrator privileges required",
            required_permission="admin"
        )
    
    return current_user


async def get_current_premium_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current premium user.
    
    Args:
        current_user: Current user from authentication
        
    Returns:
        Premium user
        
    Raises:
        AuthorizationException: If user is not premium
    """
    if current_user.subscription_tier not in ["premium", "enterprise"]:
        raise AuthorizationException(
            "Premium subscription required",
            required_permission="premium"
        )
    
    return current_user


# Pagination Dependencies

async def get_pagination_params(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    size: int = Query(
        settings.DEFAULT_PAGE_SIZE,
        ge=1,
        le=settings.MAX_PAGE_SIZE,
        description=f"Page size (max: {settings.MAX_PAGE_SIZE})"
    ),
) -> PaginationParams:
    """
    Get pagination parameters from query parameters.
    
    Args:
        page: Page number
        size: Page size
        
    Returns:
        Pagination parameters
    """
    return PaginationParams(page=page, size=size)


async def get_sort_params(
    sort_by: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort order"),
) -> SortParams:
    """
    Get sorting parameters from query parameters.
    
    Args:
        sort_by: Field to sort by
        sort_order: Sort order (asc/desc)
        
    Returns:
        Sorting parameters
    """
    return SortParams(sort_by=sort_by, sort_order=sort_order)


# File Upload Dependencies

async def validate_file_upload(
    file: UploadFile = File(...),
    params: FileUploadParams = Depends(),
) -> UploadFile:
    """
    Validate uploaded file.
    
    Args:
        file: Uploaded file
        params: File upload parameters
        
    Returns:
        Validated file
        
    Raises:
        FileTooLargeException: If file is too large
        UnsupportedFileTypeException: If file type is not supported
    """
    # Check file size
    if file.size and file.size > params.max_size_mb * 1024 * 1024:
        raise FileTooLargeException(
            filename=file.filename or "unknown",
            size=file.size,
            max_size=params.max_size_mb * 1024 * 1024,
        )
    
    # Check file extension
    if file.filename:
        file_ext = "." + file.filename.split(".")[-1].lower()
        if file_ext not in params.allowed_extensions:
            raise UnsupportedFileTypeException(
                filename=file.filename,
                file_type=file_ext,
                supported_types=params.allowed_extensions,
            )
    
    return file


async def validate_multiple_file_upload(
    files: List[UploadFile] = File(...),
    params: FileUploadParams = Depends(),
) -> List[UploadFile]:
    """
    Validate multiple uploaded files.
    
    Args:
        files: List of uploaded files
        params: File upload parameters
        
    Returns:
        List of validated files
        
    Raises:
        ValidationException: If multiple files not allowed
        FileTooLargeException: If any file is too large
        UnsupportedFileTypeException: If any file type is not supported
    """
    if not params.allow_multiple and len(files) > 1:
        raise ValidationException("Multiple file upload not allowed")
    
    validated_files = []
    for file in files:
        validated_file = await validate_file_upload(file, params)
        validated_files.append(validated_file)
    
    return validated_files


# Database Dependencies

async def get_database_session() -> AsyncSession:
    """
    Get database session.
    
    Returns:
        Database session
    """
    async for session in get_db():
        yield session


# Redis Dependencies

async def get_redis_connection():
    """
    Get Redis connection.
    
    Returns:
        Redis connection
    """
    return await get_redis()


# Request Validation Dependencies

async def validate_uuid(
    resource_id: str,
    parameter_name: str = "id",
) -> UUID:
    """
    Validate UUID parameter.
    
    Args:
        resource_id: Resource ID to validate
        parameter_name: Parameter name for error messages
        
    Returns:
        Validated UUID
        
    Raises:
        InvalidParameterException: If UUID is invalid
    """
    try:
        return UUID(resource_id)
    except ValueError:
        raise InvalidParameterException(
            parameter=parameter_name,
            value=resource_id,
            expected="Valid UUID format",
        )


async def validate_presentation_id(
    presentation_id: str,
) -> UUID:
    """
    Validate presentation ID parameter.
    
    Args:
        presentation_id: Presentation ID to validate
        
    Returns:
        Validated UUID
    """
    return await validate_uuid(presentation_id, "presentation_id")


async def validate_user_id(
    user_id: str,
) -> UUID:
    """
    Validate user ID parameter.
    
    Args:
        user_id: User ID to validate
        
    Returns:
        Validated UUID
    """
    return await validate_uuid(user_id, "user_id")


async def validate_template_id(
    template_id: str,
) -> UUID:
    """
    Validate template ID parameter.
    
    Args:
        template_id: Template ID to validate
        
    Returns:
        Validated UUID
    """
    return await validate_uuid(template_id, "template_id")


# Rate Limiting Dependencies

async def check_rate_limit(
    request: Request,
    limit_key: str = "default",
    requests_per_minute: int = 60,
) -> None:
    """
    Check rate limit for request.
    
    Args:
        request: FastAPI request object
        limit_key: Rate limit key
        requests_per_minute: Allowed requests per minute
        
    Raises:
        RateLimitExceededException: If rate limit exceeded
    """
    try:
        redis_client = await get_redis()
        if not redis_client:
            return  # Skip rate limiting if Redis unavailable
        
        # Get client identifier
        client_ip = request.client.host if request.client else "unknown"
        user_id = getattr(request.state, "user_id", None)
        
        # Create rate limit key
        identifier = user_id or client_ip
        key = f"rate_limit:{limit_key}:{identifier}"
        
        # Check current count
        current = await redis_client.get(key)
        if current and int(current) >= requests_per_minute:
            ttl = await redis_client.ttl(key)
            raise RateLimitExceededException(
                retry_after=ttl if ttl > 0 else 60,
                limit=requests_per_minute,
                window="1 minute",
            )
        
        # Increment counter
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, 60)  # 1 minute window
        await pipe.execute()
        
    except RateLimitExceededException:
        raise
    except Exception:
        # Don't block requests if rate limiting fails
        pass


# Content Type Dependencies

async def validate_json_content_type(request: Request) -> None:
    """
    Validate that request has JSON content type.
    
    Args:
        request: FastAPI request object
        
    Raises:
        ValidationException: If content type is not JSON
    """
    content_type = request.headers.get("content-type", "")
    if not content_type.startswith("application/json"):
        raise ValidationException(
            "Content-Type must be application/json",
            field="content-type",
        )


# API Version Dependencies

async def get_api_version(request: Request) -> str:
    """
    Get API version from request.
    
    Args:
        request: FastAPI request object
        
    Returns:
        API version
    """
    return getattr(request.state, "api_version", "v1")


# Query Parameters Dependencies

async def get_search_params(
    q: Optional[str] = Query(None, description="Search query"),
    fields: Optional[str] = Query(None, description="Comma-separated fields to search"),
) -> Dict[str, Any]:
    """
    Get search parameters from query string.
    
    Args:
        q: Search query
        fields: Fields to search in
        
    Returns:
        Search parameters dictionary
    """
    params = {}
    
    if q:
        params["query"] = q.strip()
    
    if fields:
        field_list = [field.strip() for field in fields.split(",") if field.strip()]
        params["fields"] = field_list
    
    return params


async def get_filter_params(
    status: Optional[str] = Query(None, description="Filter by status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    created_after: Optional[str] = Query(None, description="Filter by creation date (ISO format)"),
    created_before: Optional[str] = Query(None, description="Filter by creation date (ISO format)"),
) -> Dict[str, Any]:
    """
    Get filter parameters from query string.
    
    Args:
        status: Status filter
        category: Category filter
        created_after: Created after date
        created_before: Created before date
        
    Returns:
        Filter parameters dictionary
    """
    filters = {}
    
    if status:
        filters["status"] = status
    
    if category:
        filters["category"] = category
    
    if created_after:
        try:
            from datetime import datetime
            filters["created_after"] = datetime.fromisoformat(created_after.replace("Z", "+00:00"))
        except ValueError:
            raise InvalidParameterException(
                parameter="created_after",
                value=created_after,
                expected="ISO format datetime",
            )
    
    if created_before:
        try:
            from datetime import datetime
            filters["created_before"] = datetime.fromisoformat(created_before.replace("Z", "+00:00"))
        except ValueError:
            raise InvalidParameterException(
                parameter="created_before",
                value=created_before,
                expected="ISO format datetime",
            )
    
    return filters


# Response Utilities

def create_pagination_metadata(
    page: int,
    size: int,
    total: int,
) -> PaginationResponse:
    """
    Create pagination metadata for responses.
    
    Args:
        page: Current page
        size: Page size
        total: Total number of items
        
    Returns:
        Pagination metadata
    """
    pages = (total + size - 1) // size  # Ceiling division
    
    return PaginationResponse(
        page=page,
        size=size,
        total=total,
        pages=pages,
        has_next=page < pages,
        has_prev=page > 1,
    )


def create_paginated_response(
    items: List[Any],
    pagination: PaginationParams,
    total: int,
) -> Dict[str, Any]:
    """
    Create paginated response with metadata.
    
    Args:
        items: List of items for current page
        pagination: Pagination parameters
        total: Total number of items
        
    Returns:
        Paginated response dictionary
    """
    metadata = create_pagination_metadata(pagination.page, pagination.size, total)
    
    return {
        "items": items,
        "pagination": metadata.dict(),
    }


# Validation Helpers

def validate_email(email: str) -> str:
    """
    Validate email format.
    
    Args:
        email: Email address to validate
        
    Returns:
        Validated email address
        
    Raises:
        ValidationException: If email format is invalid
    """
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        raise ValidationException(
            "Invalid email format",
            field="email",
        )
    
    return email.lower()


def validate_password_strength(password: str) -> str:
    """
    Validate password strength.
    
    Args:
        password: Password to validate
        
    Returns:
        Validated password
        
    Raises:
        ValidationException: If password is too weak
    """
    if len(password) < 8:
        raise ValidationException(
            "Password must be at least 8 characters long",
            field="password",
        )
    
    if not re.search(r'[A-Z]', password):
        raise ValidationException(
            "Password must contain at least one uppercase letter",
            field="password",
        )
    
    if not re.search(r'[a-z]', password):
        raise ValidationException(
            "Password must contain at least one lowercase letter",
            field="password",
        )
    
    if not re.search(r'\d', password):
        raise ValidationException(
            "Password must contain at least one digit",
            field="password",
        )
    
    return password