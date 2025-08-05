"""
API versioning strategy and implementation for SlideGenie API.

This module provides comprehensive API versioning support including:
- Semantic versioning strategy
- Version-specific routing and deprecation
- Backward compatibility management
- Version negotiation and client support
"""
import re
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class APIVersionStatus(str, Enum):
    """API version status enumeration."""
    EXPERIMENTAL = "experimental"
    BETA = "beta"
    STABLE = "stable"
    DEPRECATED = "deprecated"
    SUNSET = "sunset"


class VersionCompatibility(str, Enum):
    """Version compatibility levels."""
    BACKWARD_COMPATIBLE = "backward_compatible"
    BREAKING_CHANGES = "breaking_changes"
    MAJOR_REWRITE = "major_rewrite"


class APIVersion(BaseModel):
    """API version information model."""
    version: str = Field(..., description="Version string (e.g., '1.0.0')")
    status: APIVersionStatus = Field(..., description="Version status")
    release_date: datetime = Field(..., description="Version release date")
    deprecation_date: Optional[datetime] = Field(None, description="Deprecation announcement date")
    sunset_date: Optional[datetime] = Field(None, description="End-of-life date")
    compatibility: VersionCompatibility = Field(..., description="Compatibility level with previous version")
    breaking_changes: List[str] = Field([], description="List of breaking changes")
    new_features: List[str] = Field([], description="List of new features")
    bug_fixes: List[str] = Field([], description="List of bug fixes")
    migration_guide_url: Optional[str] = Field(None, description="URL to migration guide")
    
    @validator("version")
    def validate_version_format(cls, v):
        """Validate semantic version format."""
        if not re.match(r"^\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?$", v):
            raise ValueError("Version must follow semantic versioning format (e.g., '1.0.0' or '1.0.0-beta.1')")
        return v
    
    @validator("sunset_date")
    def validate_sunset_after_deprecation(cls, v, values):
        """Ensure sunset date is after deprecation date."""
        if v and values.get("deprecation_date") and v <= values["deprecation_date"]:
            raise ValueError("Sunset date must be after deprecation date")
        return v


class VersionedEndpoint(BaseModel):
    """Versioned endpoint configuration."""
    path: str = Field(..., description="Endpoint path")
    methods: Set[str] = Field(..., description="Supported HTTP methods")
    introduced_in: str = Field(..., description="Version when endpoint was introduced")
    deprecated_in: Optional[str] = Field(None, description="Version when endpoint was deprecated")
    removed_in: Optional[str] = Field(None, description="Version when endpoint was removed")
    changes: Dict[str, List[str]] = Field({}, description="Changes by version")


class ClientRequirements(BaseModel):
    """Client requirements for API versions."""
    min_client_version: Optional[str] = Field(None, description="Minimum required client version")
    recommended_client_version: Optional[str] = Field(None, description="Recommended client version")
    sdk_support: Dict[str, str] = Field({}, description="SDK version support mapping")


class APIVersionManager:
    """
    Manages API versioning, deprecation, and compatibility.
    """
    
    def __init__(self):
        self.versions: Dict[str, APIVersion] = {}
        self.endpoints: Dict[str, List[VersionedEndpoint]] = {}
        self.default_version = "1.0.0"
        self.supported_versions = {"1.0.0"}
        self.deprecated_versions = set()
        self.sunset_versions = set()
        
        # Initialize with current API versions
        self._initialize_versions()
    
    def _initialize_versions(self):
        """Initialize API version definitions."""
        # Version 1.0.0 - Initial stable release
        self.add_version(APIVersion(
            version="1.0.0",
            status=APIVersionStatus.STABLE,
            release_date=datetime(2024, 1, 1),
            compatibility=VersionCompatibility.BACKWARD_COMPATIBLE,
            new_features=[
                "Complete REST API for presentation management",
                "AI-powered slide generation",
                "Multiple export formats (PPTX, PDF, Beamer)",
                "Real-time collaboration via WebSocket",
                "Academic email validation",
                "OAuth integration with Google and Microsoft"
            ]
        ))
        
        # Version 1.1.0 - Feature enhancements
        self.add_version(APIVersion(
            version="1.1.0",
            status=APIVersionStatus.BETA,
            release_date=datetime(2024, 6, 1),
            compatibility=VersionCompatibility.BACKWARD_COMPATIBLE,
            new_features=[
                "Advanced citation management",
                "Template customization API",
                "Bulk operations for presentations",
                "Enhanced analytics and reporting",
                "LaTeX equation rendering improvements"
            ],
            bug_fixes=[
                "Fixed file upload timeout issues",
                "Improved WebSocket connection stability",
                "Better error handling for AI service failures"
            ]
        ))
        
        # Version 2.0.0 - Major rewrite (planned)
        self.add_version(APIVersion(
            version="2.0.0",
            status=APIVersionStatus.EXPERIMENTAL,
            release_date=datetime(2024, 12, 1),
            compatibility=VersionCompatibility.BREAKING_CHANGES,
            breaking_changes=[
                "Redesigned authentication flow with API keys",
                "New presentation data model with improved relationships",
                "Consolidated endpoint structure",
                "Updated response formats with consistent schemas"
            ],
            new_features=[
                "GraphQL API alongside REST",
                "Advanced AI model selection",
                "Multi-language support",
                "Enhanced collaboration features",
                "Improved rate limiting with quotas"
            ],
            migration_guide_url="https://docs.slidegenie.com/migration/v1-to-v2"
        ))
    
    def add_version(self, version: APIVersion):
        """Add a new API version."""
        self.versions[version.version] = version
        if version.status in [APIVersionStatus.STABLE, APIVersionStatus.BETA]:
            self.supported_versions.add(version.version)
        elif version.status == APIVersionStatus.DEPRECATED:
            self.deprecated_versions.add(version.version)
        elif version.status == APIVersionStatus.SUNSET:
            self.sunset_versions.add(version.version)
    
    def get_version(self, version: str) -> Optional[APIVersion]:
        """Get version information."""
        return self.versions.get(version)
    
    def get_supported_versions(self) -> List[str]:
        """Get list of supported versions."""
        return sorted(self.supported_versions, key=self._parse_version, reverse=True)
    
    def get_latest_version(self) -> str:
        """Get the latest stable version."""
        stable_versions = [
            v for v, info in self.versions.items()
            if info.status == APIVersionStatus.STABLE
        ]
        return max(stable_versions, key=self._parse_version) if stable_versions else self.default_version
    
    def is_version_supported(self, version: str) -> bool:
        """Check if a version is supported."""
        return version in self.supported_versions
    
    def is_version_deprecated(self, version: str) -> bool:
        """Check if a version is deprecated."""
        return version in self.deprecated_versions
    
    def is_version_sunset(self, version: str) -> bool:
        """Check if a version is sunset (end-of-life)."""
        return version in self.sunset_versions
    
    def _parse_version(self, version: str) -> Tuple[int, int, int]:
        """Parse version string for comparison."""
        try:
            major, minor, patch = version.split("-")[0].split(".")
            return (int(major), int(minor), int(patch))
        except (ValueError, IndexError):
            return (0, 0, 0)
    
    def deprecate_version(self, version: str, sunset_date: Optional[datetime] = None):
        """Mark a version as deprecated."""
        if version in self.versions:
            version_info = self.versions[version]
            version_info.status = APIVersionStatus.DEPRECATED
            version_info.deprecation_date = datetime.utcnow()
            if sunset_date:
                version_info.sunset_date = sunset_date
            
            self.deprecated_versions.add(version)
            self.supported_versions.discard(version)
            
            logger.warning(f"API version {version} has been deprecated", 
                         deprecation_date=version_info.deprecation_date,
                         sunset_date=sunset_date)
    
    def sunset_version(self, version: str):
        """Mark a version as sunset (end-of-life)."""
        if version in self.versions:
            version_info = self.versions[version]
            version_info.status = APIVersionStatus.SUNSET
            version_info.sunset_date = datetime.utcnow()
            
            self.sunset_versions.add(version)
            self.deprecated_versions.discard(version)
            self.supported_versions.discard(version)
            
            logger.error(f"API version {version} has reached end-of-life", 
                        sunset_date=version_info.sunset_date)


class VersionNegotiator:
    """
    Handles API version negotiation and client compatibility.
    """
    
    def __init__(self, version_manager: APIVersionManager):
        self.version_manager = version_manager
    
    def negotiate_version(
        self,
        requested_version: Optional[str] = None,
        accept_header: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[str, List[str]]:
        """
        Negotiate API version based on client request.
        
        Args:
            requested_version: Explicitly requested version
            accept_header: HTTP Accept header for content negotiation
            user_agent: Client User-Agent header
            
        Returns:
            Tuple of (selected_version, warnings)
        """
        warnings = []
        
        # 1. Check explicitly requested version
        if requested_version:
            if self.version_manager.is_version_sunset(requested_version):
                raise HTTPException(
                    status_code=status.HTTP_410_GONE,
                    detail=f"API version {requested_version} is no longer supported"
                )
            
            if self.version_manager.is_version_deprecated(requested_version):
                version_info = self.version_manager.get_version(requested_version)
                warnings.append(f"API version {requested_version} is deprecated")
                if version_info and version_info.sunset_date:
                    warnings.append(f"Version will be sunset on {version_info.sunset_date.date()}")
            
            if self.version_manager.is_version_supported(requested_version):
                return requested_version, warnings
        
        # 2. Parse Accept header for version preferences
        if accept_header:
            version_from_accept = self._parse_accept_header(accept_header)
            if version_from_accept and self.version_manager.is_version_supported(version_from_accept):
                return version_from_accept, warnings
        
        # 3. Detect client from User-Agent and provide appropriate version
        if user_agent:
            client_version = self._detect_client_version(user_agent)
            if client_version:
                recommended = self._get_recommended_version_for_client(client_version)
                if recommended:
                    return recommended, warnings
        
        # 4. Return latest stable version as default
        latest = self.version_manager.get_latest_version()
        return latest, warnings
    
    def _parse_accept_header(self, accept_header: str) -> Optional[str]:
        """Parse version from Accept header."""
        # Example: application/vnd.slidegenie.v1+json
        pattern = r"application/vnd\.slidegenie\.v(\d+(?:\.\d+)?(?:\.\d+)?)"
        match = re.search(pattern, accept_header)
        if match:
            version_part = match.group(1)
            # Convert v1 to 1.0.0, v1.1 to 1.1.0, etc.
            parts = version_part.split(".")
            while len(parts) < 3:
                parts.append("0")
            return ".".join(parts)
        return None
    
    def _detect_client_version(self, user_agent: str) -> Optional[str]:
        """Detect client type and version from User-Agent."""
        # Example: SlideGenie-Python-SDK/1.2.0
        patterns = [
            r"SlideGenie-Python-SDK/(\d+\.\d+\.\d+)",
            r"SlideGenie-JS-SDK/(\d+\.\d+\.\d+)",
            r"SlideGenie-CLI/(\d+\.\d+\.\d+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, user_agent)
            if match:
                return match.group(1)
        
        return None
    
    def _get_recommended_version_for_client(self, client_version: str) -> Optional[str]:
        """Get recommended API version for client version."""
        # Client SDK to API version mapping
        client_to_api_mapping = {
            "1.0.0": "1.0.0",
            "1.1.0": "1.0.0",
            "1.2.0": "1.1.0",
            "2.0.0": "2.0.0"
        }
        
        api_version = client_to_api_mapping.get(client_version)
        if api_version and self.version_manager.is_version_supported(api_version):
            return api_version
        
        return None


# Global version manager instance
version_manager = APIVersionManager()
version_negotiator = VersionNegotiator(version_manager)


def get_api_version(
    request: Request,
    x_api_version: Optional[str] = Header(None, alias="X-API-Version"),
    accept: Optional[str] = Header(None),
    user_agent: Optional[str] = Header(None, alias="User-Agent")
) -> str:
    """
    Dependency to get negotiated API version.
    
    Args:
        request: FastAPI request object
        x_api_version: Explicit version header
        accept: Accept header for content negotiation
        user_agent: Client User-Agent header
        
    Returns:
        Negotiated API version string
    """
    try:
        version, warnings = version_negotiator.negotiate_version(
            requested_version=x_api_version,
            accept_header=accept,
            user_agent=user_agent
        )
        
        # Add warnings to response headers (will be added by middleware)
        if warnings:
            request.state.api_warnings = warnings
        
        # Add version info to request state
        request.state.api_version = version
        request.state.version_info = version_manager.get_version(version)
        
        return version
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during version negotiation: {str(e)}")
        # Fall back to default version
        return version_manager.get_latest_version()


def create_versioned_router(
    version: str,
    prefix: str = "",
    tags: Optional[List[str]] = None,
    deprecated: bool = False
) -> APIRouter:
    """
    Create a versioned API router.
    
    Args:
        version: API version (e.g., "1.0.0")
        prefix: URL prefix for the router
        tags: OpenAPI tags
        deprecated: Whether this version is deprecated
        
    Returns:
        Configured APIRouter instance
    """
    router = APIRouter(
        prefix=prefix,
        tags=tags or [],
        deprecated=deprecated
    )
    
    # Add version-specific middleware or dependencies here
    
    return router


def version_deprecation_middleware(request: Request, call_next):
    """
    Middleware to handle version deprecation warnings.
    """
    async def middleware(request: Request, call_next):
        response = await call_next(request)
        
        # Add deprecation warnings to response headers
        if hasattr(request.state, 'api_warnings'):
            for i, warning in enumerate(request.state.api_warnings):
                response.headers[f"Warning-{i+1}"] = warning
        
        # Add version information to response headers
        if hasattr(request.state, 'api_version'):
            response.headers["X-API-Version"] = request.state.api_version
        
        # Add deprecation headers for deprecated versions
        if hasattr(request.state, 'version_info'):
            version_info = request.state.version_info
            if version_info and version_info.status == APIVersionStatus.DEPRECATED:
                response.headers["Deprecation"] = "true"
                if version_info.sunset_date:
                    response.headers["Sunset"] = version_info.sunset_date.strftime("%a, %d %b %Y %H:%M:%S GMT")
        
        return response
    
    return middleware


# API version information endpoint
def get_version_info_routes() -> APIRouter:
    """Create routes for API version information."""
    router = APIRouter(tags=["version-info"])
    
    @router.get("/versions")
    async def list_api_versions():
        """
        List all API versions and their status.
        
        Returns:
            List of API versions with metadata
        """
        versions = []
        for version_str, version_info in version_manager.versions.items():
            versions.append({
                "version": version_str,
                "status": version_info.status.value,
                "release_date": version_info.release_date.isoformat(),
                "deprecation_date": version_info.deprecation_date.isoformat() if version_info.deprecation_date else None,
                "sunset_date": version_info.sunset_date.isoformat() if version_info.sunset_date else None,
                "compatibility": version_info.compatibility.value,
                "breaking_changes": version_info.breaking_changes,
                "new_features": version_info.new_features,
                "migration_guide_url": version_info.migration_guide_url
            })
        
        return {
            "versions": sorted(versions, key=lambda x: version_manager._parse_version(x["version"]), reverse=True),
            "default_version": version_manager.default_version,
            "latest_stable": version_manager.get_latest_version(),
            "supported_versions": version_manager.get_supported_versions()
        }
    
    @router.get("/versions/{version}")
    async def get_version_details(version: str):
        """
        Get detailed information about a specific API version.
        
        Args:
            version: API version string
            
        Returns:
            Detailed version information
        """
        version_info = version_manager.get_version(version)
        if not version_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API version {version} not found"
            )
        
        return {
            "version": version,
            "status": version_info.status.value,
            "release_date": version_info.release_date.isoformat(),
            "deprecation_date": version_info.deprecation_date.isoformat() if version_info.deprecation_date else None,
            "sunset_date": version_info.sunset_date.isoformat() if version_info.sunset_date else None,
            "compatibility": version_info.compatibility.value,
            "breaking_changes": version_info.breaking_changes,
            "new_features": version_info.new_features,
            "bug_fixes": version_info.bug_fixes,
            "migration_guide_url": version_info.migration_guide_url,
            "is_supported": version_manager.is_version_supported(version),
            "is_deprecated": version_manager.is_version_deprecated(version),
            "is_sunset": version_manager.is_version_sunset(version)
        }
    
    return router