"""
Template management endpoints for SlideGenie.

This module provides comprehensive template management functionality including:
- Template CRUD operations with admin controls
- Template filtering and search
- Template categories and academic field organization
- Template cloning and customization
- Preview generation
- Version control and usage tracking
- Integration with export generators
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from fastapi import (
    APIRouter, 
    Depends, 
    HTTPException, 
    Query, 
    Path, 
    BackgroundTasks,
    status,
    File,
    UploadFile
)
from sqlalchemy import and_, or_, func, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import (
    get_current_user, 
    get_current_superuser,
    get_current_user_optional
)
from app.domain.schemas.template import (
    TemplateCreate,
    TemplateUpdate,
    TemplateResponse,
    TemplateListResponse,
    TemplateCloneRequest,
    TemplatePreviewRequest,
    TemplatePreviewResponse,
    TemplateFilterRequest,
    TemplateSearchResponse,
    TemplateCategoriesResponse,
    TemplateCategory,
    TemplateUsageStats,
    TemplateValidationResponse,
    TemplateValidationError,
    TemplateExportRequest,
    TemplateExportResponse
)
from app.infrastructure.database.base import get_db
from app.infrastructure.database.models import Template, User, Institution
from app.repositories.template import TemplateRepository
from app.services.export.generators.beamer_generator import BeamerGenerator
from app.services.export.generators.pptx_generator import PPTXGenerator

logger = logging.getLogger(__name__)
router = APIRouter()


# Template Categories and Academic Fields
TEMPLATE_CATEGORIES = {
    "conference": {
        "display_name": "Conference Presentations",
        "description": "Templates for academic conference presentations",
        "subcategories": ["oral", "poster", "keynote", "workshop"]
    },
    "lecture": {
        "display_name": "Lectures",
        "description": "Templates for educational lectures and courses",
        "subcategories": ["undergraduate", "graduate", "seminar"]
    },
    "defense": {
        "display_name": "Thesis Defense",
        "description": "Templates for thesis and dissertation defenses",
        "subcategories": ["phd", "masters", "honors"]
    },
    "journal": {
        "display_name": "Journal Presentations",
        "description": "Templates for journal paper presentations",
        "subcategories": ["review", "research", "case_study"]
    },
    "proposal": {
        "display_name": "Research Proposals",
        "description": "Templates for research proposal presentations",
        "subcategories": ["grant", "funding", "project"]
    },
    "report": {
        "display_name": "Progress Reports",
        "description": "Templates for progress and status reports",
        "subcategories": ["quarterly", "annual", "milestone"]
    }
}

ACADEMIC_FIELDS = [
    "Computer Science", "Biology", "Physics", "Chemistry", "Mathematics",
    "Engineering", "Medicine", "Psychology", "Economics", "Business",
    "Education", "Literature", "History", "Philosophy", "Political Science",
    "Sociology", "Anthropology", "Geography", "Environmental Science",
    "Materials Science", "Neuroscience", "Bioinformatics", "Data Science"
]

CONFERENCE_SERIES = {
    "IEEE": ["IEEE Conference Template", "IEEE Journal Template"],
    "ACM": ["ACM Conference Template", "ACM SIGCHI Template", "ACM SIGGRAPH Template"],
    "Nature": ["Nature Journal Template", "Nature Conference Template"],
    "Science": ["Science Journal Template", "AAAS Template"],
    "Springer": ["Springer LNCS Template", "Springer Journal Template"],
    "Elsevier": ["Elsevier Journal Template", "Elsevier Conference Template"],
    "AAAI": ["AAAI Conference Template"],
    "ICML": ["ICML Conference Template"],
    "NeurIPS": ["NeurIPS Conference Template"],
    "ICLR": ["ICLR Conference Template"]
}


@router.get("/", response_model=TemplateListResponse)
async def list_templates(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by category"),
    academic_field: Optional[str] = Query(None, description="Filter by academic field"),
    conference_series: Optional[str] = Query(None, description="Filter by conference series"),
    is_official: Optional[bool] = Query(None, description="Filter by official status"),
    is_premium: Optional[bool] = Query(None, description="Filter premium templates"),
    search: Optional[str] = Query(None, description="Search in name and description"),
    sort_by: str = Query("usage_count", description="Sort field"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    include_inactive: bool = Query(False, description="Include inactive templates"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    List all available templates with filtering and pagination.
    
    Supports filtering by:
    - Category (conference, lecture, defense, etc.)
    - Academic field (Computer Science, Biology, etc.)
    - Conference series (IEEE, ACM, Nature, etc.)
    - Official status and premium status
    - Text search in name and description
    
    Returns paginated results with metadata.
    """
    try:
        # Build query conditions
        conditions = []
        
        if not include_inactive:
            conditions.append(Template.is_active == True)
        
        conditions.append(Template.deleted_at.is_(None))
        
        # Apply filters
        if category:
            if category not in TEMPLATE_CATEGORIES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid category. Must be one of: {', '.join(TEMPLATE_CATEGORIES.keys())}"
                )
            conditions.append(Template.category == category)
        
        if academic_field:
            if academic_field not in ACADEMIC_FIELDS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid academic field. Must be one of: {', '.join(ACADEMIC_FIELDS)}"
                )
            conditions.append(Template.academic_field == academic_field)
        
        if conference_series:
            conditions.append(Template.conference_series == conference_series)
        
        if is_official is not None:
            conditions.append(Template.is_official == is_official)
        
        if is_premium is not None:
            # Non-premium users can only see non-premium templates
            if is_premium and (not current_user or current_user.subscription_tier == "free"):
                conditions.append(Template.is_premium == False)
            else:
                conditions.append(Template.is_premium == is_premium)
        elif not current_user or current_user.subscription_tier == "free":
            # Default: hide premium templates for free users
            conditions.append(Template.is_premium == False)
        
        if search:
            search_term = f"%{search.lower()}%"
            conditions.append(
                or_(
                    func.lower(Template.name).like(search_term),
                    func.lower(Template.display_name).like(search_term),
                    func.lower(Template.description).like(search_term)
                )
            )
        
        # Count total results
        count_query = select(func.count(Template.id)).where(and_(*conditions))
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Build main query with sorting
        query = select(Template).where(and_(*conditions))
        
        # Apply sorting
        sort_field = getattr(Template, sort_by, Template.usage_count)
        if sort_order == "desc":
            query = query.order_by(sort_field.desc())
        else:
            query = query.order_by(sort_field.asc())
        
        # Add secondary sorting for consistency
        query = query.order_by(Template.name)
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        # Execute query
        result = await db.execute(query)
        templates = result.scalars().all()
        
        # Convert to response format
        template_responses = [
            TemplateResponse.from_orm(template) for template in templates
        ]
        
        has_next = offset + page_size < total
        has_prev = page > 1
        
        return TemplateListResponse(
            templates=template_responses,
            total=total,
            page=page,
            page_size=page_size,
            has_next=has_next,
            has_prev=has_prev
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing templates: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve templates"
        )


@router.get("/categories", response_model=TemplateCategoriesResponse)
async def get_template_categories(
    db: AsyncSession = Depends(get_db)
):
    """
    Get all available template categories with counts.
    
    Returns categories with template counts and descriptions.
    """
    try:
        # Get category counts from database
        category_counts = {}
        for category_key in TEMPLATE_CATEGORIES.keys():
            count_query = select(func.count(Template.id)).where(
                and_(
                    Template.category == category_key,
                    Template.is_active == True,
                    Template.deleted_at.is_(None)
                )
            )
            result = await db.execute(count_query)
            category_counts[category_key] = result.scalar()
        
        # Build response
        categories = []
        for key, info in TEMPLATE_CATEGORIES.items():
            categories.append(TemplateCategory(
                name=key,
                display_name=info["display_name"],
                description=info["description"],
                template_count=category_counts.get(key, 0)
            ))
        
        return TemplateCategoriesResponse(
            categories=categories,
            total=len(categories)
        )
        
    except Exception as e:
        logger.error(f"Error getting template categories: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve template categories"
        )


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: UUID = Path(..., description="Template ID"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Get template details and configuration by ID.
    
    Returns complete template information including configuration,
    preview slides, and metadata.
    """
    try:
        # Query template
        query = select(Template).where(
            and_(
                Template.id == template_id,
                Template.deleted_at.is_(None)
            )
        )
        result = await db.execute(query)
        template = result.scalar_one_or_none()
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        
        # Check if user can access premium template
        if template.is_premium and (not current_user or current_user.subscription_tier == "free"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Premium template access requires subscription"
            )
        
        # Check if template is active (unless user is admin or creator)
        if not template.is_active:
            if not current_user or (
                current_user.role != "admin" and 
                current_user.id != template.created_by_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Template not found"
                )
        
        # Increment usage count if accessed by non-owner
        if current_user and current_user.id != template.created_by_id:
            # Use background task to avoid slowing down response
            await db.execute(
                update(Template)
                .where(Template.id == template_id)
                .values(usage_count=Template.usage_count + 1)
            )
            await db.commit()
        
        return TemplateResponse.from_orm(template)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template {template_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve template"
        )


@router.post("/", response_model=TemplateResponse)
async def create_template(
    template_data: TemplateCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """
    Create a new template (admin only).
    
    Creates a new template with validation and preview generation.
    Only administrators can create official templates.
    """
    try:
        # Check if template name already exists
        existing_query = select(Template).where(
            and_(
                Template.name == template_data.name,
                Template.deleted_at.is_(None)
            )
        )
        existing_result = await db.execute(existing_query)
        if existing_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Template name already exists"
            )
        
        # Validate configuration
        validation_errors = await validate_template_config(template_data.config)
        if validation_errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Template configuration errors: {'; '.join(validation_errors)}"
            )
        
        # Create template
        template = Template(
            id=uuid4(),
            name=template_data.name,
            display_name=template_data.display_name,
            description=template_data.description,
            category=template_data.category,
            conference_series=template_data.conference_series,
            academic_field=template_data.academic_field,
            config=template_data.config.dict(),
            thumbnail_url=template_data.thumbnail_url,
            preview_slides=template_data.preview_slides,
            is_official=template_data.is_official,
            is_premium=template_data.is_premium,
            source=template_data.source,
            source_url=template_data.source_url,
            version=template_data.version,
            compatible_with=template_data.compatible_with,
            created_by_id=current_user.id,
            usage_count=0,
            is_active=True
        )
        
        db.add(template)
        await db.commit()
        await db.refresh(template)
        
        # Generate preview in background
        if not template_data.preview_slides:
            background_tasks.add_task(
                generate_template_preview,
                template.id,
                db
            )
        
        logger.info(f"Template {template.name} created by admin {current_user.id}")
        
        return TemplateResponse.from_orm(template)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating template: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create template"
        )


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: UUID = Path(..., description="Template ID"),
    template_data: TemplateUpdate = ...,
    background_tasks: BackgroundTasks = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """
    Update an existing template (admin only).
    
    Updates template configuration and metadata.
    Regenerates preview if configuration changes.
    """
    try:
        # Get existing template
        query = select(Template).where(
            and_(
                Template.id == template_id,
                Template.deleted_at.is_(None)
            )
        )
        result = await db.execute(query)
        template = result.scalar_one_or_none()
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        
        # Track if config changed for preview regeneration
        config_changed = False
        
        # Update fields
        update_data = {}
        if template_data.display_name is not None:
            update_data["display_name"] = template_data.display_name
        if template_data.description is not None:
            update_data["description"] = template_data.description
        if template_data.category is not None:
            update_data["category"] = template_data.category
        if template_data.conference_series is not None:
            update_data["conference_series"] = template_data.conference_series
        if template_data.academic_field is not None:
            update_data["academic_field"] = template_data.academic_field
        if template_data.config is not None:
            # Validate new configuration
            validation_errors = await validate_template_config(template_data.config)
            if validation_errors:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Template configuration errors: {'; '.join(validation_errors)}"
                )
            update_data["config"] = template_data.config.dict()
            config_changed = True
        if template_data.thumbnail_url is not None:
            update_data["thumbnail_url"] = template_data.thumbnail_url
        if template_data.preview_slides is not None:
            update_data["preview_slides"] = template_data.preview_slides
        if template_data.is_official is not None:
            update_data["is_official"] = template_data.is_official
        if template_data.is_premium is not None:
            update_data["is_premium"] = template_data.is_premium
        if template_data.is_active is not None:
            update_data["is_active"] = template_data.is_active
        if template_data.source_url is not None:
            update_data["source_url"] = template_data.source_url
        if template_data.version is not None:
            update_data["version"] = template_data.version
        if template_data.compatible_with is not None:
            update_data["compatible_with"] = template_data.compatible_with
        
        if update_data:
            update_data["updated_at"] = datetime.utcnow()
            
            await db.execute(
                update(Template)
                .where(Template.id == template_id)
                .values(**update_data)
            )
            await db.commit()
            
            # Refresh template
            await db.refresh(template)
        
        # Regenerate preview if config changed
        if config_changed:
            background_tasks.add_task(
                generate_template_preview,
                template.id,
                db
            )
        
        logger.info(f"Template {template.name} updated by admin {current_user.id}")
        
        return TemplateResponse.from_orm(template)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating template {template_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update template"
        )


@router.delete("/{template_id}")
async def delete_template(
    template_id: UUID = Path(..., description="Template ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """
    Delete a template (admin only).
    
    Soft deletes the template to maintain referential integrity.
    Templates in use by presentations cannot be deleted.
    """
    try:
        # Check if template exists
        query = select(Template).where(
            and_(
                Template.id == template_id,
                Template.deleted_at.is_(None)
            )
        )
        result = await db.execute(query)
        template = result.scalar_one_or_none()
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        
        # Check if template is in use
        from app.infrastructure.database.models import Presentation
        usage_query = select(func.count(Presentation.id)).where(
            and_(
                Presentation.template_id == template_id,
                Presentation.deleted_at.is_(None)
            )
        )
        usage_result = await db.execute(usage_query)
        usage_count = usage_result.scalar()
        
        if usage_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete template: currently used by {usage_count} presentations"
            )
        
        # Soft delete
        await db.execute(
            update(Template)
            .where(Template.id == template_id)
            .values(
                deleted_at=datetime.utcnow(),
                is_active=False
            )
        )
        await db.commit()
        
        logger.info(f"Template {template.name} deleted by admin {current_user.id}")
        
        return {"message": "Template deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting template {template_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete template"
        )


@router.post("/{template_id}/clone", response_model=TemplateResponse)
async def clone_template(
    template_id: UUID = Path(..., description="Template ID"),
    clone_data: TemplateCloneRequest = ...,
    background_tasks: BackgroundTasks = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Clone an existing template.
    
    Creates a copy of an existing template with optional modifications.
    Users can clone any public template or their own templates.
    """
    try:
        # Get source template
        query = select(Template).where(
            and_(
                Template.id == template_id,
                Template.deleted_at.is_(None),
                Template.is_active == True
            )
        )
        result = await db.execute(query)
        source_template = result.scalar_one_or_none()
        
        if not source_template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source template not found"
            )
        
        # Check if user can access premium template
        if source_template.is_premium and current_user.subscription_tier == "free":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Premium template cloning requires subscription"
            )
        
        # Check if clone name already exists for this user
        existing_query = select(Template).where(
            and_(
                Template.name == clone_data.name,
                Template.created_by_id == current_user.id,
                Template.deleted_at.is_(None)
            )
        )
        existing_result = await db.execute(existing_query)
        if existing_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Template name already exists in your templates"
            )
        
        # Create cloned template
        cloned_config = source_template.config.copy()
        if clone_data.modifications:
            # Apply modifications to config
            cloned_config.update(clone_data.modifications)
        
        cloned_template = Template(
            id=uuid4(),
            name=clone_data.name,
            display_name=clone_data.display_name or f"{source_template.display_name} (Copy)",
            description=clone_data.description or f"Cloned from {source_template.display_name}",
            category=source_template.category,
            conference_series=source_template.conference_series,
            academic_field=source_template.academic_field,
            config=cloned_config,
            thumbnail_url=source_template.thumbnail_url,
            preview_slides=source_template.preview_slides,
            is_official=False,  # Cloned templates are never official
            is_premium=False,   # Cloned templates are never premium
            source="user",
            source_url=None,
            version="1.0.0",
            compatible_with=source_template.compatible_with,
            created_by_id=current_user.id,
            usage_count=0,
            is_active=True
        )
        
        db.add(cloned_template)
        await db.commit()
        await db.refresh(cloned_template)
        
        # Generate new preview if modifications were made
        if clone_data.modifications:
            background_tasks.add_task(
                generate_template_preview,
                cloned_template.id,
                db
            )
        
        # Increment source template usage count
        await db.execute(
            update(Template)
            .where(Template.id == template_id)
            .values(usage_count=Template.usage_count + 1)
        )
        await db.commit()
        
        logger.info(f"Template {source_template.name} cloned as {cloned_template.name} by user {current_user.id}")
        
        return TemplateResponse.from_orm(cloned_template)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cloning template {template_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clone template"
        )


@router.get("/{template_id}/preview", response_model=TemplatePreviewResponse)
async def generate_preview(
    template_id: UUID = Path(..., description="Template ID"),
    preview_request: TemplatePreviewRequest = TemplatePreviewRequest(),
    background_tasks: BackgroundTasks = ...,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Generate template preview images.
    
    Creates preview images for different slide types using the template.
    Returns URLs to generated preview images.
    """
    try:
        # Get template
        query = select(Template).where(
            and_(
                Template.id == template_id,
                Template.deleted_at.is_(None),
                Template.is_active == True
            )
        )
        result = await db.execute(query)
        template = result.scalar_one_or_none()
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        
        # Check premium access
        if template.is_premium and (not current_user or current_user.subscription_tier == "free"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Premium template preview requires subscription"
            )
        
        # Generate preview in background and return immediately
        preview_id = str(uuid4())
        background_tasks.add_task(
            generate_template_preview_async,
            template_id,
            preview_request,
            preview_id,
            db
        )
        
        # Return preview response with placeholder URLs
        preview_urls = []
        for slide_type in preview_request.slide_types:
            preview_urls.append(f"/api/v1/templates/previews/{preview_id}/{slide_type}.{preview_request.format}")
        
        return TemplatePreviewResponse(
            template_id=template_id,
            preview_urls=preview_urls,
            generated_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating template preview {template_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate template preview"
        )


# Helper functions


async def validate_template_config(config: Any) -> List[str]:
    """
    Validate template configuration.
    
    Args:
        config: Template configuration to validate
        
    Returns:
        List of validation error messages
    """
    errors = []
    
    if not isinstance(config, dict):
        errors.append("Configuration must be a valid JSON object")
        return errors
    
    # Check required sections
    required_sections = ["layouts", "theme", "defaults"]
    for section in required_sections:
        if section not in config:
            errors.append(f"Missing required configuration section: {section}")
    
    # Validate layouts
    if "layouts" in config:
        layouts = config["layouts"]
        if not isinstance(layouts, dict):
            errors.append("Layouts section must be an object")
        else:
            required_layouts = ["title", "content"]
            for layout in required_layouts:
                if layout not in layouts:
                    errors.append(f"Missing required layout: {layout}")
    
    # Validate theme
    if "theme" in config:
        theme = config["theme"]
        if not isinstance(theme, dict):
            errors.append("Theme section must be an object")
        else:
            if "colors" not in theme:
                errors.append("Theme must include colors configuration")
            if "fonts" not in theme:
                errors.append("Theme must include fonts configuration")
    
    return errors


async def generate_template_preview(template_id: UUID, db: AsyncSession):
    """
    Generate preview images for a template.
    
    Args:
        template_id: Template ID
        db: Database session
    """
    try:
        # This would integrate with actual preview generation service
        # For now, we'll just log the action
        logger.info(f"Generating preview for template {template_id}")
        
        # In a real implementation, this would:
        # 1. Create sample slides using the template
        # 2. Render them to images
        # 3. Store the images and update the template record
        
    except Exception as e:
        logger.error(f"Error generating preview for template {template_id}: {str(e)}")


async def generate_template_preview_async(
    template_id: UUID,
    preview_request: TemplatePreviewRequest,
    preview_id: str,
    db: AsyncSession
):
    """
    Asynchronously generate template preview images.
    
    Args:
        template_id: Template ID
        preview_request: Preview generation parameters
        preview_id: Unique preview generation ID
        db: Database session
    """
    try:
        # This would integrate with actual preview generation service
        logger.info(f"Generating async preview {preview_id} for template {template_id}")
        
        # In a real implementation, this would:
        # 1. Get the template configuration
        # 2. Apply any config overrides
        # 3. Generate sample content for each slide type
        # 4. Render using the appropriate generator (Beamer, PPTX, etc.)
        # 5. Convert to requested image format
        # 6. Store images and make them available via the preview URLs
        
    except Exception as e:
        logger.error(f"Error generating async preview {preview_id}: {str(e)}")


@router.get("/search", response_model=TemplateSearchResponse)
async def search_templates(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by category"),
    academic_field: Optional[str] = Query(None, description="Filter by academic field"),
    is_official: Optional[bool] = Query(None, description="Filter by official status"),
    min_rating: Optional[float] = Query(None, ge=0.0, le=5.0, description="Minimum rating"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Advanced template search with faceted results.
    
    Provides full-text search across template names, descriptions, and metadata
    with faceted filtering and suggestions.
    """
    try:
        # Build base search conditions
        conditions = [
            Template.is_active == True,
            Template.deleted_at.is_(None)
        ]
        
        # Hide premium templates for free users
        if not current_user or current_user.subscription_tier == "free":
            conditions.append(Template.is_premium == False)
        
        # Add search condition
        search_term = f"%{q.lower()}%"
        search_condition = or_(
            func.lower(Template.name).like(search_term),
            func.lower(Template.display_name).like(search_term),
            func.lower(Template.description).like(search_term),
            func.lower(Template.category).like(search_term),
            func.lower(Template.academic_field).like(search_term),
            func.lower(Template.conference_series).like(search_term)
        )
        conditions.append(search_condition)
        
        # Apply filters
        if category:
            conditions.append(Template.category == category)
        if academic_field:
            conditions.append(Template.academic_field == academic_field)
        if is_official is not None:
            conditions.append(Template.is_official == is_official)
        if min_rating is not None:
            conditions.append(Template.rating >= min_rating)
        
        # Count total results
        count_query = select(func.count(Template.id)).where(and_(*conditions))
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Get search results with pagination
        offset = (page - 1) * page_size
        query = (
            select(Template)
            .where(and_(*conditions))
            .order_by(Template.usage_count.desc(), Template.rating.desc())
            .offset(offset)
            .limit(page_size)
        )
        
        result = await db.execute(query)
        templates = result.scalars().all()
        
        # Generate facets for filtering
        facets = await generate_search_facets(q, db, current_user)
        
        # Generate search suggestions
        suggestions = await generate_search_suggestions(q, db)
        
        template_responses = [
            TemplateResponse.from_orm(template) for template in templates
        ]
        
        return TemplateSearchResponse(
            templates=template_responses,
            total=total,
            facets=facets,
            suggestions=suggestions
        )
        
    except Exception as e:
        logger.error(f"Error searching templates: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search templates"
        )


@router.get("/{template_id}/stats", response_model=TemplateUsageStats)
async def get_template_stats(
    template_id: UUID = Path(..., description="Template ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """
    Get template usage statistics (admin only).
    
    Returns detailed usage statistics including usage count, ratings,
    and popular configurations.
    """
    try:
        # Get template
        query = select(Template).where(
            and_(
                Template.id == template_id,
                Template.deleted_at.is_(None)
            )
        )
        result = await db.execute(query)
        template = result.scalar_one_or_none()
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        
        # Get recent usage data (last 30 days)
        from app.infrastructure.database.models import Presentation
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        recent_usage_query = (
            select(Presentation.created_at, Presentation.title, Presentation.owner_id)
            .where(
                and_(
                    Presentation.template_id == template_id,
                    Presentation.created_at >= thirty_days_ago,
                    Presentation.deleted_at.is_(None)
                )
            )
            .order_by(Presentation.created_at.desc())
            .limit(10)
        )
        
        recent_usage_result = await db.execute(recent_usage_query)
        recent_usage_data = []
        
        for row in recent_usage_result:
            recent_usage_data.append({
                "created_at": row.created_at.isoformat(),
                "title": row.title,
                "user_id": str(row.owner_id)
            })
        
        # Calculate average rating (placeholder - would need ratings table)
        average_rating = template.rating or 0.0
        
        # Get popular configurations (placeholder - would analyze presentation configs)
        popular_configurations = [
            {
                "config_key": "theme.colors.primary",
                "value": "#003366",
                "usage_count": 15
            },
            {
                "config_key": "layouts.content.type",
                "value": "two_column",
                "usage_count": 12
            }
        ]
        
        return TemplateUsageStats(
            template_id=template_id,
            usage_count=template.usage_count,
            average_rating=average_rating,
            recent_usage=recent_usage_data,
            popular_configurations=popular_configurations
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template stats {template_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve template statistics"
        )


@router.post("/{template_id}/validate", response_model=TemplateValidationResponse)
async def validate_template(
    template_id: UUID = Path(..., description="Template ID"),
    config_override: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Validate template configuration.
    
    Validates a template's configuration and provides suggestions
    for improvements or fixes.
    """
    try:
        # Get template
        query = select(Template).where(
            and_(
                Template.id == template_id,
                Template.deleted_at.is_(None)
            )
        )
        result = await db.execute(query)
        template = result.scalar_one_or_none()
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        
        # Use config override if provided, otherwise use template config
        config_to_validate = config_override or template.config
        
        # Validate configuration
        validation_errors = await validate_template_config(config_to_validate)
        validation_warnings = await get_template_warnings(config_to_validate)
        suggestions = await get_template_suggestions(config_to_validate)
        
        # Convert to validation error objects
        errors = [
            TemplateValidationError(
                field="config",
                error=error,
                suggestion=None
            ) for error in validation_errors
        ]
        
        warnings = [
            TemplateValidationError(
                field="config",
                error=warning,
                suggestion=None
            ) for warning in validation_warnings
        ]
        
        return TemplateValidationResponse(
            is_valid=len(validation_errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating template {template_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate template"
        )


@router.post("/{template_id}/export", response_model=TemplateExportResponse)
async def export_template(
    template_id: UUID = Path(..., description="Template ID"),
    export_request: TemplateExportRequest = ...,
    background_tasks: BackgroundTasks = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export template in various formats.
    
    Exports template configuration and assets in the requested format
    (JSON, YAML, Beamer, PPTX).
    """
    try:
        # Get template
        query = select(Template).where(
            and_(
                Template.id == template_id,
                Template.deleted_at.is_(None),
                Template.is_active == True
            )
        )
        result = await db.execute(query)
        template = result.scalar_one_or_none()
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        
        # Check premium access
        if template.is_premium and current_user.subscription_tier == "free":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Premium template export requires subscription"
            )
        
        # Generate export in background
        export_id = str(uuid4())
        background_tasks.add_task(
            generate_template_export,
            template_id,
            export_request,
            export_id,
            current_user.id
        )
        
        # Return export response
        export_url = f"/api/v1/templates/exports/{export_id}.{export_request.format}"
        
        return TemplateExportResponse(
            template_id=template_id,
            format=export_request.format,
            export_url=export_url,
            expires_at=datetime.utcnow() + timedelta(hours=24),
            file_size=None  # Will be updated when export completes
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting template {template_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export template"
        )


# Additional helper functions

async def generate_search_facets(
    query: str,
    db: AsyncSession,
    current_user: Optional[User]
) -> Dict[str, List[Dict[str, Any]]]:
    """Generate search facets for filtering."""
    try:
        facets = {}
        
        # Category facets
        category_query = (
            select(Template.category, func.count(Template.id))
            .where(
                and_(
                    Template.is_active == True,
                    Template.deleted_at.is_(None),
                    Template.is_premium == False if not current_user or current_user.subscription_tier == "free" else True
                )
            )
            .group_by(Template.category)
            .order_by(func.count(Template.id).desc())
        )
        
        result = await db.execute(category_query)
        categories = []
        for category, count in result:
            if category:
                categories.append({"name": category, "count": count})
        facets["categories"] = categories
        
        # Academic field facets
        field_query = (
            select(Template.academic_field, func.count(Template.id))
            .where(
                and_(
                    Template.is_active == True,
                    Template.deleted_at.is_(None),
                    Template.academic_field.isnot(None),
                    Template.is_premium == False if not current_user or current_user.subscription_tier == "free" else True
                )
            )
            .group_by(Template.academic_field)
            .order_by(func.count(Template.id).desc())
            .limit(10)
        )
        
        result = await db.execute(field_query)
        fields = []
        for field, count in result:
            fields.append({"name": field, "count": count})
        facets["academic_fields"] = fields
        
        # Conference series facets
        conference_query = (
            select(Template.conference_series, func.count(Template.id))
            .where(
                and_(
                    Template.is_active == True,
                    Template.deleted_at.is_(None),
                    Template.conference_series.isnot(None),
                    Template.is_premium == False if not current_user or current_user.subscription_tier == "free" else True
                )
            )
            .group_by(Template.conference_series)
            .order_by(func.count(Template.id).desc())
            .limit(10)
        )
        
        result = await db.execute(conference_query)
        conferences = []
        for conference, count in result:
            conferences.append({"name": conference, "count": count})
        facets["conference_series"] = conferences
        
        return facets
        
    except Exception as e:
        logger.error(f"Error generating search facets: {str(e)}")
        return {}


async def generate_search_suggestions(query: str, db: AsyncSession) -> List[str]:
    """Generate search suggestions based on query."""
    try:
        # Simple suggestion logic - in production would use more sophisticated NLP
        suggestions = []
        
        query_lower = query.lower()
        
        # Suggest categories
        for category in TEMPLATE_CATEGORIES.keys():
            if category.startswith(query_lower) and category not in suggestions:
                suggestions.append(category)
        
        # Suggest academic fields
        for field in ACADEMIC_FIELDS:
            if field.lower().startswith(query_lower) and field not in suggestions:
                suggestions.append(field)
        
        # Suggest conference series
        for series in CONFERENCE_SERIES.keys():
            if series.lower().startswith(query_lower) and series not in suggestions:
                suggestions.append(series)
        
        return suggestions[:5]  # Limit to 5 suggestions
        
    except Exception as e:
        logger.error(f"Error generating search suggestions: {str(e)}")
        return []


async def get_template_warnings(config: Dict[str, Any]) -> List[str]:
    """Get template configuration warnings."""
    warnings = []
    
    # Check for deprecated configuration keys
    deprecated_keys = ["old_layout_format", "legacy_theme"]
    for key in deprecated_keys:
        if key in config:
            warnings.append(f"Configuration key '{key}' is deprecated")
    
    # Check for missing optional but recommended sections
    if "requirements" not in config:
        warnings.append("Missing 'requirements' section - slide requirements not specified")
    
    if "defaults" in config:
        defaults = config["defaults"]
        if "slide_count" not in defaults:
            warnings.append("Default slide count not specified in configuration")
    
    return warnings


async def get_template_suggestions(config: Dict[str, Any]) -> List[str]:
    """Get template configuration improvement suggestions."""
    suggestions = []
    
    # Suggest adding preview slides if missing
    if "preview_slides" not in config:
        suggestions.append("Add preview slides to help users understand the template")
    
    # Suggest adding more layout options
    if "layouts" in config and len(config["layouts"]) < 3:
        suggestions.append("Consider adding more layout options for flexibility")
    
    # Suggest theme improvements
    if "theme" in config:
        theme = config["theme"]
        if "colors" in theme and len(theme["colors"]) < 3:
            suggestions.append("Add more color options for better customization")
    
    return suggestions


async def generate_template_export(
    template_id: UUID,
    export_request: TemplateExportRequest,
    export_id: str,
    user_id: UUID
):
    """Generate template export file in background."""
    try:
        logger.info(f"Generating template export {export_id} for template {template_id}")
        
        # In a real implementation, this would:
        # 1. Get the template and its configuration
        # 2. Generate the export in the requested format
        # 3. Store the file and make it available via the export URL
        # 4. Update the export record with file size and completion status
        
    except Exception as e:
        logger.error(f"Error generating template export {export_id}: {str(e)}")