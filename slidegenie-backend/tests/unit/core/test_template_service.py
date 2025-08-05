"""Unit tests for template service."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import Dict, Any, List
import json

from app.services.template_service import TemplateService
from app.domain.schemas.template import TemplateCreate, TemplateUpdate
from tests.unit.utils.test_helpers import TestDataGenerator, MockFileStorage


class TestTemplateService:
    """Test suite for template service."""
    
    @pytest.fixture
    def template_service(self):
        """Create template service instance."""
        return TemplateService()
    
    @pytest.fixture
    def mock_template_repo(self):
        """Create mock template repository."""
        repo = AsyncMock()
        return repo
    
    @pytest.fixture
    def mock_file_storage(self):
        """Create mock file storage."""
        return MockFileStorage()
    
    @pytest.fixture
    def test_template(self):
        """Generate test template data."""
        return {
            "id": 1,
            "name": "Academic Research",
            "description": "Professional template for academic presentations",
            "category": "academic",
            "is_public": True,
            "created_by": 1,
            "thumbnail_url": "https://storage.example.com/templates/1/thumbnail.png",
            "config": {
                "theme": {
                    "primary_color": "#003366",
                    "secondary_color": "#0066CC",
                    "font_family": "Arial",
                    "font_size": 14
                },
                "layouts": {
                    "title": {"background": "gradient", "text_align": "center"},
                    "content": {"bullet_style": "circle", "spacing": 1.5},
                    "two_column": {"column_gap": 20}
                },
                "animations": {
                    "slide_transition": "fade",
                    "element_animation": "appear"
                }
            },
            "tags": ["academic", "research", "professional"],
            "usage_count": 150,
            "rating": 4.5,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    
    @pytest.fixture
    def test_templates(self):
        """Generate multiple test templates."""
        categories = ["academic", "business", "creative", "minimal"]
        templates = []
        
        for i in range(1, 9):
            template = {
                "id": i,
                "name": f"Template {i}",
                "category": categories[(i-1) % len(categories)],
                "is_public": i % 2 == 0,
                "usage_count": i * 10,
                "rating": 3.5 + (i % 3) * 0.5,
                "created_at": datetime.utcnow()
            }
            templates.append(template)
        
        return templates
    
    @pytest.mark.asyncio
    async def test_create_template(self, template_service, mock_template_repo, test_template):
        """Test template creation."""
        template_service.template_repository = mock_template_repo
        
        mock_template_repo.create.return_value = test_template
        
        template_data = TemplateCreate(
            name="Academic Research",
            description="Professional template for academic presentations",
            category="academic",
            config=test_template['config'],
            tags=["academic", "research", "professional"]
        )
        
        result = await template_service.create_template(
            template_data,
            user_id=1
        )
        
        assert result['name'] == "Academic Research"
        assert result['category'] == "academic"
        assert result['created_by'] == 1
        
        # Verify repository call
        mock_template_repo.create.assert_called_once()
        create_data = mock_template_repo.create.call_args[0][0]
        assert create_data['name'] == "Academic Research"
        assert create_data['created_by'] == 1
    
    @pytest.mark.asyncio
    async def test_get_template_by_id(self, template_service, mock_template_repo, test_template):
        """Test getting template by ID."""
        template_service.template_repository = mock_template_repo
        
        mock_template_repo.get.return_value = test_template
        
        result = await template_service.get_template(1)
        
        assert result['id'] == 1
        assert result['name'] == "Academic Research"
        mock_template_repo.get.assert_called_once_with(1)
    
    @pytest.mark.asyncio
    async def test_update_template(self, template_service, mock_template_repo, test_template):
        """Test template update."""
        template_service.template_repository = mock_template_repo
        
        mock_template_repo.get.return_value = test_template
        updated_template = {
            **test_template,
            "name": "Updated Academic Template",
            "description": "Updated description"
        }
        mock_template_repo.update.return_value = updated_template
        
        update_data = TemplateUpdate(
            name="Updated Academic Template",
            description="Updated description"
        )
        
        result = await template_service.update_template(
            template_id=1,
            update_data=update_data,
            user_id=1
        )
        
        assert result['name'] == "Updated Academic Template"
        assert result['description'] == "Updated description"
        
        # Verify ownership check
        assert mock_template_repo.get.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_delete_template(self, template_service, mock_template_repo, test_template):
        """Test template deletion."""
        template_service.template_repository = mock_template_repo
        
        mock_template_repo.get.return_value = test_template
        mock_template_repo.delete.return_value = True
        
        result = await template_service.delete_template(
            template_id=1,
            user_id=1
        )
        
        assert result['message'] == "Template successfully deleted"
        mock_template_repo.delete.assert_called_once_with(1)
    
    @pytest.mark.asyncio
    async def test_list_templates_with_filters(self, template_service, mock_template_repo, test_templates):
        """Test listing templates with filters."""
        template_service.template_repository = mock_template_repo
        
        # Filter for academic templates
        academic_templates = [t for t in test_templates if t['category'] == 'academic']
        
        mock_template_repo.list.return_value = {
            "items": academic_templates,
            "total": len(academic_templates),
            "page": 1,
            "size": 10
        }
        
        result = await template_service.list_templates(
            category="academic",
            is_public=True,
            page=1,
            size=10
        )
        
        assert len(result['items']) == len(academic_templates)
        assert all(t['category'] == 'academic' for t in result['items'])
        
        # Verify repository call
        mock_template_repo.list.assert_called_once()
        call_args = mock_template_repo.list.call_args[1]
        assert call_args['filters']['category'] == 'academic'
        assert call_args['filters']['is_public'] is True
    
    @pytest.mark.asyncio
    async def test_search_templates(self, template_service, mock_template_repo, test_templates):
        """Test template search functionality."""
        template_service.template_repository = mock_template_repo
        
        # Mock search results
        search_results = [t for t in test_templates if 'academic' in t.get('tags', [])]
        mock_template_repo.search.return_value = search_results
        
        result = await template_service.search_templates(
            query="academic research",
            limit=5
        )
        
        assert len(result) > 0
        mock_template_repo.search.assert_called_once_with(
            query="academic research",
            fields=['name', 'description', 'tags'],
            limit=5
        )
    
    @pytest.mark.asyncio
    async def test_get_popular_templates(self, template_service, mock_template_repo, test_templates):
        """Test getting popular templates."""
        template_service.template_repository = mock_template_repo
        
        # Sort by usage count
        popular = sorted(test_templates, key=lambda t: t['usage_count'], reverse=True)[:5]
        
        mock_template_repo.list.return_value = {
            "items": popular,
            "total": len(popular)
        }
        
        result = await template_service.get_popular_templates(limit=5)
        
        assert len(result) == 5
        assert result[0]['usage_count'] >= result[-1]['usage_count']
        
        # Verify repository call
        mock_template_repo.list.assert_called_once()
        call_args = mock_template_repo.list.call_args[1]
        assert call_args['sort_by'] == 'usage_count'
        assert call_args['order'] == 'desc'
    
    @pytest.mark.asyncio
    async def test_clone_template(self, template_service, mock_template_repo, test_template):
        """Test template cloning."""
        template_service.template_repository = mock_template_repo
        
        mock_template_repo.get.return_value = test_template
        
        # Create cloned template
        cloned = {
            **test_template,
            "id": 100,
            "name": "Academic Research (Copy)",
            "is_public": False,
            "created_by": 2,
            "usage_count": 0,
            "rating": 0
        }
        mock_template_repo.create.return_value = cloned
        
        result = await template_service.clone_template(
            template_id=1,
            user_id=2,
            new_name="Academic Research (Copy)"
        )
        
        assert result['id'] != test_template['id']
        assert result['name'] == "Academic Research (Copy)"
        assert result['created_by'] == 2
        assert result['is_public'] is False
        assert result['usage_count'] == 0
    
    @pytest.mark.asyncio
    async def test_upload_template_thumbnail(self, template_service, mock_template_repo, mock_file_storage, test_template):
        """Test template thumbnail upload."""
        template_service.template_repository = mock_template_repo
        template_service.file_storage = mock_file_storage
        
        mock_template_repo.get.return_value = test_template
        
        # Mock thumbnail upload
        thumbnail_data = b"fake_thumbnail_image"
        thumbnail_path = f"templates/{test_template['id']}/thumbnail.png"
        
        updated_template = {**test_template, "thumbnail_url": f"https://storage.example.com/{thumbnail_path}"}
        mock_template_repo.update.return_value = updated_template
        
        result = await template_service.upload_thumbnail(
            template_id=1,
            thumbnail_data=thumbnail_data,
            user_id=1
        )
        
        assert result['thumbnail_url'] == f"https://storage.example.com/{thumbnail_path}"
        assert mock_file_storage.upload_count == 1
        assert thumbnail_path in mock_file_storage.files
    
    @pytest.mark.asyncio
    async def test_rate_template(self, template_service, mock_template_repo, test_template):
        """Test template rating."""
        template_service.template_repository = mock_template_repo
        
        mock_template_repo.get.return_value = test_template
        
        # Mock rating storage
        with patch.object(template_service, '_update_template_rating', new_callable=AsyncMock) as mock_update_rating:
            mock_update_rating.return_value = {**test_template, "rating": 4.6}
            
            result = await template_service.rate_template(
                template_id=1,
                user_id=2,
                rating=5
            )
        
        assert result['rating'] == 4.6
        mock_update_rating.assert_called_once_with(1, 2, 5)
    
    @pytest.mark.asyncio
    async def test_get_template_preview(self, template_service, mock_template_repo, test_template):
        """Test template preview generation."""
        template_service.template_repository = mock_template_repo
        
        mock_template_repo.get.return_value = test_template
        
        # Mock preview generation
        with patch.object(template_service, '_generate_preview', new_callable=AsyncMock) as mock_preview:
            mock_preview.return_value = {
                "slides": [
                    {"type": "title", "preview_url": "https://preview.example.com/slide1.png"},
                    {"type": "content", "preview_url": "https://preview.example.com/slide2.png"}
                ]
            }
            
            result = await template_service.get_preview(1)
        
        assert 'slides' in result
        assert len(result['slides']) == 2
        assert all('preview_url' in slide for slide in result['slides'])
    
    @pytest.mark.asyncio
    async def test_export_template(self, template_service, mock_template_repo, test_template):
        """Test template export."""
        template_service.template_repository = mock_template_repo
        
        mock_template_repo.get.return_value = test_template
        
        result = await template_service.export_template(
            template_id=1,
            format="json"
        )
        
        assert result['format'] == "json"
        assert 'data' in result
        
        # Verify exported data
        exported_data = json.loads(result['data'])
        assert exported_data['name'] == test_template['name']
        assert exported_data['config'] == test_template['config']
    
    @pytest.mark.asyncio
    async def test_import_template(self, template_service, mock_template_repo):
        """Test template import."""
        template_service.template_repository = mock_template_repo
        
        # Template data to import
        import_data = {
            "name": "Imported Template",
            "category": "business",
            "config": {
                "theme": {"primary_color": "#FF0000"},
                "layouts": {"title": {"background": "solid"}}
            }
        }
        
        imported_template = {
            "id": 200,
            **import_data,
            "created_by": 3,
            "created_at": datetime.utcnow()
        }
        
        mock_template_repo.create.return_value = imported_template
        
        result = await template_service.import_template(
            template_data=json.dumps(import_data),
            user_id=3
        )
        
        assert result['name'] == "Imported Template"
        assert result['created_by'] == 3
        
        # Verify validation was performed
        create_args = mock_template_repo.create.call_args[0][0]
        assert create_args['name'] == "Imported Template"
    
    @pytest.mark.asyncio
    async def test_get_user_templates(self, template_service, mock_template_repo, test_templates):
        """Test getting templates created by a specific user."""
        template_service.template_repository = mock_template_repo
        
        user_templates = [t for t in test_templates if t.get('created_by') == 1]
        
        mock_template_repo.list.return_value = {
            "items": user_templates,
            "total": len(user_templates)
        }
        
        result = await template_service.get_user_templates(user_id=1)
        
        assert len(result) > 0
        assert all(t.get('created_by') == 1 for t in result)
        
        # Verify repository call
        mock_template_repo.list.assert_called_once()
        call_args = mock_template_repo.list.call_args[1]
        assert call_args['filters']['created_by'] == 1