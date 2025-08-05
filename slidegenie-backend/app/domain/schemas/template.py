"""
Template schemas for SlideGenie.
"""
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator


class TemplateCategory(BaseModel):
    """Template category schema."""
    name: str
    display_name: str
    description: Optional[str] = None
    template_count: int = 0


class TemplateConfig(BaseModel):
    """Template configuration schema."""
    layouts: Dict[str, Any] = Field(default_factory=dict)
    theme: Dict[str, Any] = Field(default_factory=dict)
    defaults: Dict[str, Any] = Field(default_factory=dict)
    requirements: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        schema_extra = {
            "example": {
                "layouts": {
                    "title": {"type": "title", "elements": ["title", "subtitle", "authors"]},
                    "content": {"type": "content", "elements": ["title", "body"]}
                },
                "theme": {
                    "colors": {"primary": "#003366", "secondary": "#0066CC"},
                    "fonts": {"main": "Times New Roman", "heading": "Arial"}
                },
                "defaults": {
                    "slide_count": 15,
                    "sections": ["Introduction", "Methods", "Results", "Conclusion"],
                    "bibliography_style": "ieee"
                },
                "requirements": {
                    "title_slide": True,
                    "outline_slide": True,
                    "references_slide": True
                }
            }
        }


class TemplatePreview(BaseModel):
    """Template preview schema."""
    slide_type: str
    title: str
    content: Dict[str, Any]
    thumbnail_url: Optional[str] = None


class TemplateCreate(BaseModel):
    """Schema for creating a new template."""
    name: str = Field(..., min_length=1, max_length=255)
    display_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    category: str = Field(..., max_length=100)
    conference_series: Optional[str] = Field(None, max_length=200)
    academic_field: Optional[str] = Field(None, max_length=200)
    config: TemplateConfig
    thumbnail_url: Optional[str] = Field(None, max_length=500)
    preview_slides: Optional[List[TemplatePreview]] = Field(default_factory=list)
    is_official: bool = False
    is_premium: bool = False
    source: str = Field(default="user", max_length=50)
    source_url: Optional[str] = Field(None, max_length=500)
    version: str = Field(default="1.0.0", max_length=20)
    compatible_with: Optional[List[str]] = Field(default_factory=list)

    @validator('name')
    def validate_name(cls, v):
        """Validate template name."""
        if not v.replace('-', '').replace('_', '').replace(' ', '').isalnum():
            raise ValueError('Template name must contain only letters, numbers, spaces, hyphens, and underscores')
        return v

    @validator('category')
    def validate_category(cls, v):
        """Validate template category."""
        valid_categories = [
            'conference', 'lecture', 'defense', 'poster', 'seminar', 
            'workshop', 'journal', 'thesis', 'proposal', 'report'
        ]
        if v not in valid_categories:
            raise ValueError(f'Category must be one of: {", ".join(valid_categories)}')
        return v


class TemplateUpdate(BaseModel):
    """Schema for updating an existing template."""
    display_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    category: Optional[str] = Field(None, max_length=100)
    conference_series: Optional[str] = Field(None, max_length=200)
    academic_field: Optional[str] = Field(None, max_length=200)
    config: Optional[TemplateConfig] = None
    thumbnail_url: Optional[str] = Field(None, max_length=500)
    preview_slides: Optional[List[TemplatePreview]] = None
    is_official: Optional[bool] = None
    is_premium: Optional[bool] = None
    is_active: Optional[bool] = None
    source_url: Optional[str] = Field(None, max_length=500)
    version: Optional[str] = Field(None, max_length=20)
    compatible_with: Optional[List[str]] = None

    @validator('category')
    def validate_category(cls, v):
        """Validate template category."""
        if v is None:
            return v
        valid_categories = [
            'conference', 'lecture', 'defense', 'poster', 'seminar', 
            'workshop', 'journal', 'thesis', 'proposal', 'report'
        ]
        if v not in valid_categories:
            raise ValueError(f'Category must be one of: {", ".join(valid_categories)}')
        return v


class TemplateResponse(BaseModel):
    """Schema for template response."""
    id: UUID
    name: str
    display_name: str
    description: Optional[str]
    category: str
    conference_series: Optional[str]
    academic_field: Optional[str]
    config: Dict[str, Any]
    thumbnail_url: Optional[str]
    preview_slides: Optional[List[Dict[str, Any]]]
    is_official: bool
    is_premium: bool
    is_active: bool
    usage_count: int
    rating: Optional[float]
    source: str
    source_url: Optional[str]
    version: str
    compatible_with: Optional[List[str]]
    created_at: datetime
    updated_at: datetime
    created_by_id: Optional[UUID]

    class Config:
        from_attributes = True


class TemplateListResponse(BaseModel):
    """Schema for template list response."""
    templates: List[TemplateResponse]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


class TemplateCloneRequest(BaseModel):
    """Schema for cloning a template."""
    name: str = Field(..., min_length=1, max_length=255)
    display_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    modifications: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @validator('name')
    def validate_name(cls, v):
        """Validate template name."""
        if not v.replace('-', '').replace('_', '').replace(' ', '').isalnum():
            raise ValueError('Template name must contain only letters, numbers, spaces, hyphens, and underscores')
        return v


class TemplatePreviewRequest(BaseModel):
    """Schema for template preview generation."""
    config_override: Optional[Dict[str, Any]] = Field(default_factory=dict)
    slide_types: Optional[List[str]] = Field(default_factory=lambda: ["title", "content"])
    format: str = Field(default="png", pattern="^(png|jpg|pdf)$")
    width: Optional[int] = Field(default=1920, ge=400, le=4000)
    height: Optional[int] = Field(default=1080, ge=300, le=3000)


class TemplatePreviewResponse(BaseModel):
    """Schema for template preview response."""
    template_id: UUID
    preview_urls: List[str]
    generated_at: datetime
    expires_at: datetime


class TemplateFilterRequest(BaseModel):
    """Schema for template filtering."""
    category: Optional[str] = None
    academic_field: Optional[str] = None
    conference_series: Optional[str] = None
    is_official: Optional[bool] = None
    is_premium: Optional[bool] = None
    search: Optional[str] = None
    created_by: Optional[UUID] = None
    institution_id: Optional[UUID] = None
    min_rating: Optional[float] = Field(None, ge=0.0, le=5.0)
    tags: Optional[List[str]] = Field(default_factory=list)


class TemplateSearchResponse(BaseModel):
    """Schema for template search response."""
    templates: List[TemplateResponse]
    total: int
    facets: Dict[str, List[Dict[str, Union[str, int]]]]
    suggestions: Optional[List[str]] = None


class TemplateCategoriesResponse(BaseModel):
    """Schema for template categories response."""
    categories: List[TemplateCategory]
    total: int


class TemplateUsageStats(BaseModel):
    """Schema for template usage statistics."""
    template_id: UUID
    usage_count: int
    average_rating: Optional[float]
    recent_usage: List[Dict[str, Any]]
    popular_configurations: List[Dict[str, Any]]


class TemplateValidationError(BaseModel):
    """Schema for template validation errors."""
    field: str
    error: str
    suggestion: Optional[str] = None


class TemplateValidationResponse(BaseModel):
    """Schema for template validation response."""
    is_valid: bool
    errors: List[TemplateValidationError]
    warnings: List[TemplateValidationError]
    suggestions: List[str]


class TemplateExportRequest(BaseModel):
    """Schema for template export request."""
    format: str = Field(..., pattern="^(json|yaml|beamer|pptx)$")
    include_preview: bool = False
    include_metadata: bool = True


class TemplateExportResponse(BaseModel):
    """Schema for template export response."""
    template_id: UUID
    format: str
    export_url: str
    expires_at: datetime
    file_size: Optional[int] = None