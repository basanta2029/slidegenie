"""
Standardized API exceptions for the SlideGenie API.

This module provides a comprehensive set of API-specific exceptions that follow
HTTP standards and provide consistent error responses across the application.
"""

from typing import Any, Dict, List, Optional, Union

from fastapi import HTTPException, status


class APIException(HTTPException):
    """
    Base API exception with enhanced error details.
    
    Extends FastAPI's HTTPException with additional fields for better
    error reporting and client handling.
    """
    
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize API exception.
        
        Args:
            status_code: HTTP status code
            detail: Human-readable error message
            error_code: Machine-readable error code
            context: Additional error context
            headers: HTTP headers to include in response
        """
        self.error_code = error_code or self._generate_error_code()
        self.context = context or {}
        
        # Format detail for HTTPException
        formatted_detail = {
            "error_code": self.error_code,
            "message": detail,
            "context": self.context,
        }
        
        super().__init__(
            status_code=status_code,
            detail=formatted_detail,
            headers=headers
        )
    
    def _generate_error_code(self) -> str:
        """Generate error code from class name."""
        class_name = self.__class__.__name__
        if class_name.endswith("Exception"):
            class_name = class_name[:-9]  # Remove "Exception"
        return class_name.lower().replace("api", "")


# Authentication and Authorization Exceptions

class AuthenticationException(APIException):
    """Authentication required or failed."""
    
    def __init__(
        self,
        detail: str = "Authentication required",
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            context=context,
            headers={"WWW-Authenticate": "Bearer"},
        )


class InvalidCredentialsException(AuthenticationException):
    """Invalid credentials provided."""
    
    def __init__(self, detail: str = "Invalid credentials"):
        super().__init__(detail=detail)


class TokenExpiredException(AuthenticationException):
    """Access token has expired."""
    
    def __init__(self, detail: str = "Token has expired"):
        super().__init__(detail=detail)


class InvalidTokenException(AuthenticationException):
    """Invalid or malformed token."""
    
    def __init__(self, detail: str = "Invalid token"):
        super().__init__(detail=detail)


class AuthorizationException(APIException):
    """Insufficient permissions."""
    
    def __init__(
        self,
        detail: str = "Insufficient permissions",
        required_permission: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        if required_permission:
            context = context or {}
            context["required_permission"] = required_permission
        
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            context=context,
        )


class InactiveUserException(APIException):
    """User account is inactive."""
    
    def __init__(self, detail: str = "User account is inactive"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


# Validation Exceptions

class ValidationException(APIException):
    """Request validation failed."""
    
    def __init__(
        self,
        detail: str,
        field: Optional[str] = None,
        validation_errors: Optional[List[Dict[str, Any]]] = None,
    ):
        context = {}
        if field:
            context["field"] = field
        if validation_errors:
            context["validation_errors"] = validation_errors
        
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            context=context,
        )


class InvalidParameterException(ValidationException):
    """Invalid parameter value."""
    
    def __init__(
        self,
        parameter: str,
        value: Any,
        expected: Optional[str] = None,
    ):
        detail = f"Invalid value for parameter '{parameter}': {value}"
        if expected:
            detail += f". Expected: {expected}"
        
        super().__init__(
            detail=detail,
            field=parameter,
        )


class MissingParameterException(ValidationException):
    """Required parameter is missing."""
    
    def __init__(self, parameter: str):
        super().__init__(
            detail=f"Missing required parameter: {parameter}",
            field=parameter,
        )


class InvalidFormatException(ValidationException):
    """Invalid data format."""
    
    def __init__(
        self,
        field: str,
        expected_format: str,
        received_value: Optional[str] = None,
    ):
        detail = f"Invalid format for field '{field}'. Expected: {expected_format}"
        if received_value:
            detail += f". Received: {received_value}"
        
        super().__init__(detail=detail, field=field)


# Resource Exceptions

class ResourceNotFoundException(APIException):
    """Resource not found."""
    
    def __init__(
        self,
        resource_type: str,
        resource_id: Union[str, int],
        detail: Optional[str] = None,
    ):
        if not detail:
            detail = f"{resource_type} with ID '{resource_id}' not found"
        
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            context={
                "resource_type": resource_type,
                "resource_id": str(resource_id),
            },
        )


class ResourceAlreadyExistsException(APIException):
    """Resource already exists."""
    
    def __init__(
        self,
        resource_type: str,
        identifier: str,
        detail: Optional[str] = None,
    ):
        if not detail:
            detail = f"{resource_type} with identifier '{identifier}' already exists"
        
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            context={
                "resource_type": resource_type,
                "identifier": identifier,
            },
        )


class ResourceConflictException(APIException):
    """Resource conflict."""
    
    def __init__(
        self,
        detail: str,
        conflicting_resource: Optional[str] = None,
    ):
        context = {}
        if conflicting_resource:
            context["conflicting_resource"] = conflicting_resource
        
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            context=context,
        )


# Rate Limiting and Quota Exceptions

class RateLimitExceededException(APIException):
    """Rate limit exceeded."""
    
    def __init__(
        self,
        detail: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        limit: Optional[int] = None,
        window: Optional[str] = None,
    ):
        context = {}
        if limit:
            context["limit"] = limit
        if window:
            context["window"] = window
        
        headers = {}
        if retry_after:
            headers["Retry-After"] = str(retry_after)
            context["retry_after"] = retry_after
        
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            context=context,
            headers=headers,
        )


class QuotaExceededException(APIException):
    """User quota exceeded."""
    
    def __init__(
        self,
        resource: str,
        current_usage: int,
        limit: int,
        detail: Optional[str] = None,
    ):
        if not detail:
            detail = f"Quota exceeded for {resource}: {current_usage}/{limit}"
        
        super().__init__(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=detail,
            context={
                "resource": resource,
                "current_usage": current_usage,
                "limit": limit,
            },
        )


# External Service Exceptions

class ExternalServiceException(APIException):
    """External service error."""
    
    def __init__(
        self,
        service_name: str,
        detail: str,
        service_error_code: Optional[str] = None,
        retry_after: Optional[int] = None,
    ):
        context = {
            "service_name": service_name,
        }
        if service_error_code:
            context["service_error_code"] = service_error_code
        
        headers = {}
        if retry_after:
            headers["Retry-After"] = str(retry_after)
            context["retry_after"] = retry_after
        
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"External service error ({service_name}): {detail}",
            context=context,
            headers=headers,
        )


class AIServiceException(ExternalServiceException):
    """AI service specific error."""
    
    def __init__(
        self,
        provider: str,
        detail: str,
        model: Optional[str] = None,
        usage_info: Optional[Dict[str, Any]] = None,
    ):
        context = {"provider": provider}
        if model:
            context["model"] = model
        if usage_info:
            context["usage"] = usage_info
        
        super().__init__(
            service_name=f"AI Provider ({provider})",
            detail=detail,
        )
        self.context.update(context)


# File and Upload Exceptions

class FileException(APIException):
    """File operation error."""
    
    def __init__(
        self,
        detail: str,
        filename: Optional[str] = None,
        operation: Optional[str] = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ):
        context = {}
        if filename:
            context["filename"] = filename
        if operation:
            context["operation"] = operation
        
        super().__init__(
            status_code=status_code,
            detail=detail,
            context=context,
        )


class FileTooLargeException(FileException):
    """File size exceeds limit."""
    
    def __init__(
        self,
        filename: str,
        size: int,
        max_size: int,
    ):
        super().__init__(
            detail=f"File '{filename}' is too large: {size} bytes (max: {max_size} bytes)",
            filename=filename,
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )
        self.context.update({
            "file_size": size,
            "max_size": max_size,
        })


class UnsupportedFileTypeException(FileException):
    """Unsupported file type."""
    
    def __init__(
        self,
        filename: str,
        file_type: str,
        supported_types: List[str],
    ):
        super().__init__(
            detail=f"Unsupported file type '{file_type}' for file '{filename}'",
            filename=filename,
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )
        self.context.update({
            "file_type": file_type,
            "supported_types": supported_types,
        })


class FileNotFoundExceptionAPI(FileException):
    """File not found."""
    
    def __init__(self, filename: str):
        super().__init__(
            detail=f"File '{filename}' not found",
            filename=filename,
            status_code=status.HTTP_404_NOT_FOUND,
        )


# Processing and Generation Exceptions

class ProcessingException(APIException):
    """Processing operation failed."""
    
    def __init__(
        self,
        detail: str,
        job_id: Optional[str] = None,
        stage: Optional[str] = None,
    ):
        context = {}
        if job_id:
            context["job_id"] = job_id
        if stage:
            context["processing_stage"] = stage
        
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            context=context,
        )


class GenerationException(ProcessingException):
    """Presentation generation failed."""
    
    def __init__(
        self,
        detail: str,
        job_id: Optional[str] = None,
        generation_type: Optional[str] = None,
    ):
        super().__init__(detail=detail, job_id=job_id)
        if generation_type:
            self.context["generation_type"] = generation_type


class ExportException(ProcessingException):
    """Export operation failed."""
    
    def __init__(
        self,
        detail: str,
        export_format: Optional[str] = None,
        presentation_id: Optional[str] = None,
    ):
        context = {}
        if export_format:
            context["export_format"] = export_format
        if presentation_id:
            context["presentation_id"] = presentation_id
        
        super().__init__(detail=detail)
        self.context.update(context)


# Version and API Exceptions

class UnsupportedVersionException(APIException):
    """Unsupported API version."""
    
    def __init__(
        self,
        requested_version: str,
        supported_versions: List[str],
    ):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"API version '{requested_version}' is not supported",
            context={
                "requested_version": requested_version,
                "supported_versions": supported_versions,
            },
        )


class DeprecatedEndpointException(APIException):
    """Endpoint is deprecated."""
    
    def __init__(
        self,
        endpoint: str,
        deprecation_date: str,
        replacement_endpoint: Optional[str] = None,
    ):
        detail = f"Endpoint '{endpoint}' was deprecated on {deprecation_date}"
        if replacement_endpoint:
            detail += f". Use '{replacement_endpoint}' instead"
        
        context = {
            "deprecated_endpoint": endpoint,
            "deprecation_date": deprecation_date,
        }
        if replacement_endpoint:
            context["replacement_endpoint"] = replacement_endpoint
        
        super().__init__(
            status_code=status.HTTP_410_GONE,
            detail=detail,
            context=context,
        )


# Maintenance and Health Exceptions

class MaintenanceException(APIException):
    """Service under maintenance."""
    
    def __init__(
        self,
        detail: str = "Service temporarily unavailable for maintenance",
        retry_after: Optional[int] = None,
    ):
        headers = {}
        context = {}
        
        if retry_after:
            headers["Retry-After"] = str(retry_after)
            context["retry_after"] = retry_after
        
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
            context=context,
            headers=headers,
        )


class HealthCheckException(APIException):
    """Health check failed."""
    
    def __init__(
        self,
        component: str,
        detail: str,
        health_status: Optional[Dict[str, Any]] = None,
    ):
        context = {"component": component}
        if health_status:
            context["health_status"] = health_status
        
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Health check failed for {component}: {detail}",
            context=context,
        )


# Utility functions for exception handling

def create_validation_exception(
    errors: List[Dict[str, Any]]
) -> ValidationException:
    """
    Create a validation exception from a list of validation errors.
    
    Args:
        errors: List of validation error details
        
    Returns:
        ValidationException with formatted error details
    """
    if len(errors) == 1:
        error = errors[0]
        return ValidationException(
            detail=error.get("msg", "Validation error"),
            field=error.get("loc", [])[-1] if error.get("loc") else None,
            validation_errors=errors,
        )
    
    return ValidationException(
        detail=f"Multiple validation errors ({len(errors)} errors)",
        validation_errors=errors,
    )


def handle_database_error(exc: Exception) -> APIException:
    """
    Convert database exceptions to appropriate API exceptions.
    
    Args:
        exc: Database exception
        
    Returns:
        Appropriate API exception
    """
    error_msg = str(exc).lower()
    
    # Check for common database errors
    if "unique constraint" in error_msg or "duplicate key" in error_msg:
        return ResourceAlreadyExistsException(
            resource_type="Resource",
            identifier="unknown",
            detail="A resource with this identifier already exists",
        )
    
    if "foreign key constraint" in error_msg:
        return ResourceConflictException(
            detail="Cannot perform operation due to related resources",
        )
    
    if "not found" in error_msg:
        return ResourceNotFoundException(
            resource_type="Resource",
            resource_id="unknown",
        )
    
    # Generic database error
    return APIException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Database operation failed",
        error_code="database_error",
    )