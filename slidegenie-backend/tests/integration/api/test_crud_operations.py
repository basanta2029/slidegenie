"""
Integration tests for CRUD operations on presentations.

Tests creation, reading, updating, and deletion of presentations
with database verification and permission checking.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.infrastructure.database.models import Presentation, Slide
from app.repositories.presentation import PresentationRepository


@pytest.mark.integration
@pytest.mark.asyncio
class TestPresentationCRUD:
    """Test CRUD operations for presentations."""
    
    async def test_create_presentation(
        self,
        authenticated_client: AsyncClient,
        test_presentation_data: dict,
        db_session: AsyncSession,
    ):
        """Test creating a new presentation."""
        # Create presentation
        response = await authenticated_client.post(
            "/api/v1/presentations",
            json={
                "title": test_presentation_data["title"],
                "description": test_presentation_data["description"],
                "slides": [
                    {
                        "type": "title",
                        "title": "Test Title Slide",
                        "content": {"subtitle": "Test Subtitle"},
                        "order": 1,
                    },
                    {
                        "type": "content",
                        "title": "Introduction",
                        "content": {"text": "This is the introduction."},
                        "order": 2,
                    },
                ],
                "settings": {
                    "theme": "professional",
                    "color_scheme": "blue",
                },
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify response
        assert "id" in data
        assert data["title"] == test_presentation_data["title"]
        assert len(data["slides"]) == 2
        
        # Verify in database
        result = await db_session.execute(
            select(Presentation).where(Presentation.id == data["id"])
        )
        presentation = result.scalar_one_or_none()
        
        assert presentation is not None
        assert presentation.title == test_presentation_data["title"]
        assert len(presentation.slides) == 2
    
    async def test_read_presentation(
        self,
        authenticated_client: AsyncClient,
        test_user,
        db_session: AsyncSession,
    ):
        """Test reading a presentation."""
        # Create presentation directly in database
        repo = PresentationRepository(db_session)
        presentation = await repo.create({
            "title": "Test Presentation",
            "user_id": test_user.id,
            "slides": [
                {
                    "type": "title",
                    "title": "Test",
                    "content": {},
                    "order": 1,
                }
            ],
        })
        
        # Read via API
        response = await authenticated_client.get(
            f"/api/v1/presentations/{presentation.id}"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == str(presentation.id)
        assert data["title"] == presentation.title
        assert len(data["slides"]) == 1
    
    async def test_update_presentation(
        self,
        authenticated_client: AsyncClient,
        test_user,
        db_session: AsyncSession,
    ):
        """Test updating a presentation."""
        # Create presentation
        repo = PresentationRepository(db_session)
        presentation = await repo.create({
            "title": "Original Title",
            "user_id": test_user.id,
            "slides": [],
        })
        
        # Update via API
        update_data = {
            "title": "Updated Title",
            "description": "New description",
            "slides": [
                {
                    "type": "content",
                    "title": "New Slide",
                    "content": {"text": "New content"},
                    "order": 1,
                }
            ],
        }
        
        response = await authenticated_client.put(
            f"/api/v1/presentations/{presentation.id}",
            json=update_data,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["title"] == "Updated Title"
        assert data["description"] == "New description"
        assert len(data["slides"]) == 1
        
        # Verify in database
        await db_session.refresh(presentation)
        assert presentation.title == "Updated Title"
        assert presentation.description == "New description"
    
    async def test_delete_presentation(
        self,
        authenticated_client: AsyncClient,
        test_user,
        db_session: AsyncSession,
    ):
        """Test deleting a presentation."""
        # Create presentation
        repo = PresentationRepository(db_session)
        presentation = await repo.create({
            "title": "To Be Deleted",
            "user_id": test_user.id,
            "slides": [],
        })
        presentation_id = presentation.id
        
        # Delete via API
        response = await authenticated_client.delete(
            f"/api/v1/presentations/{presentation_id}"
        )
        
        assert response.status_code == 204
        
        # Verify deleted from database
        result = await db_session.execute(
            select(Presentation).where(Presentation.id == presentation_id)
        )
        assert result.scalar_one_or_none() is None
    
    async def test_list_user_presentations(
        self,
        authenticated_client: AsyncClient,
        test_user,
        db_session: AsyncSession,
    ):
        """Test listing user's presentations with pagination."""
        # Create multiple presentations
        repo = PresentationRepository(db_session)
        for i in range(15):
            await repo.create({
                "title": f"Presentation {i}",
                "user_id": test_user.id,
                "slides": [],
            })
        
        # Test pagination
        response = await authenticated_client.get(
            "/api/v1/presentations",
            params={"limit": 10, "offset": 0},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["items"]) == 10
        assert data["total"] == 15
        assert data["limit"] == 10
        assert data["offset"] == 0
        
        # Test second page
        response = await authenticated_client.get(
            "/api/v1/presentations",
            params={"limit": 10, "offset": 10},
        )
        
        data = response.json()
        assert len(data["items"]) == 5
    
    async def test_search_presentations(
        self,
        authenticated_client: AsyncClient,
        test_user,
        db_session: AsyncSession,
    ):
        """Test searching presentations."""
        # Create presentations with different titles
        repo = PresentationRepository(db_session)
        await repo.create({
            "title": "Machine Learning Basics",
            "user_id": test_user.id,
            "slides": [],
        })
        await repo.create({
            "title": "Deep Learning Advanced",
            "user_id": test_user.id,
            "slides": [],
        })
        await repo.create({
            "title": "Data Science Introduction",
            "user_id": test_user.id,
            "slides": [],
        })
        
        # Search for "learning"
        response = await authenticated_client.get(
            "/api/v1/presentations",
            params={"search": "learning"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["items"]) == 2
        assert all("Learning" in item["title"] for item in data["items"])
    
    async def test_permission_checks(
        self,
        authenticated_client: AsyncClient,
        client: AsyncClient,
        test_user,
        db_session: AsyncSession,
    ):
        """Test permission checks for presentation access."""
        # Create presentation as test_user
        repo = PresentationRepository(db_session)
        presentation = await repo.create({
            "title": "Private Presentation",
            "user_id": test_user.id,
            "slides": [],
        })
        
        # Try to access without authentication
        response = await client.get(
            f"/api/v1/presentations/{presentation.id}"
        )
        assert response.status_code == 401
        
        # Create another user and try to access
        from app.infrastructure.database.models import User
        from app.core.security import get_password_hash
        
        other_user = User(
            email="other@university.edu",
            password_hash=get_password_hash("OtherP@ss123!"),
            full_name="Other User",
            institution="University",
            role="student",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other_user)
        await db_session.commit()
        
        # Create client for other user
        from app.services.auth.token_service import TokenService
        token_service = TokenService()
        other_tokens = await token_service.create_token_pair(
            user_id=other_user.id,
            email=other_user.email,
            roles=[other_user.role],
            institution=other_user.institution,
        )
        
        other_client = AsyncClient(app=client.app, base_url=str(client.base_url))
        other_client.headers["Authorization"] = f"Bearer {other_tokens.access_token}"
        
        # Try to access another user's presentation
        response = await other_client.get(
            f"/api/v1/presentations/{presentation.id}"
        )
        assert response.status_code == 403
        
        # Try to update another user's presentation
        response = await other_client.put(
            f"/api/v1/presentations/{presentation.id}",
            json={"title": "Hacked Title"},
        )
        assert response.status_code == 403
        
        # Try to delete another user's presentation
        response = await other_client.delete(
            f"/api/v1/presentations/{presentation.id}"
        )
        assert response.status_code == 403
    
    async def test_bulk_operations(
        self,
        authenticated_client: AsyncClient,
        test_user,
        db_session: AsyncSession,
    ):
        """Test bulk operations on presentations."""
        # Create multiple presentations
        repo = PresentationRepository(db_session)
        presentation_ids = []
        
        for i in range(5):
            pres = await repo.create({
                "title": f"Bulk Test {i}",
                "user_id": test_user.id,
                "slides": [],
            })
            presentation_ids.append(str(pres.id))
        
        # Bulk delete
        response = await authenticated_client.post(
            "/api/v1/presentations/bulk/delete",
            json={"ids": presentation_ids[:3]},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] == 3
        
        # Verify only 2 remain
        response = await authenticated_client.get("/api/v1/presentations")
        data = response.json()
        assert len(data["items"]) == 2
    
    async def test_presentation_duplication(
        self,
        authenticated_client: AsyncClient,
        test_user,
        db_session: AsyncSession,
    ):
        """Test duplicating a presentation."""
        # Create original presentation
        repo = PresentationRepository(db_session)
        original = await repo.create({
            "title": "Original Presentation",
            "description": "Original description",
            "user_id": test_user.id,
            "slides": [
                {
                    "type": "title",
                    "title": "Title Slide",
                    "content": {"subtitle": "Original"},
                    "order": 1,
                },
                {
                    "type": "content",
                    "title": "Content Slide",
                    "content": {"text": "Original content"},
                    "order": 2,
                },
            ],
            "settings": {
                "theme": "academic",
                "color_scheme": "blue",
            },
        })
        
        # Duplicate via API
        response = await authenticated_client.post(
            f"/api/v1/presentations/{original.id}/duplicate"
        )
        
        assert response.status_code == 201
        duplicate = response.json()
        
        # Verify duplicate
        assert duplicate["id"] != str(original.id)
        assert duplicate["title"] == "Original Presentation (Copy)"
        assert duplicate["description"] == original.description
        assert len(duplicate["slides"]) == 2
        assert duplicate["settings"]["theme"] == "academic"
        
        # Verify both exist in database
        count = await db_session.scalar(
            select(func.count()).select_from(Presentation)
        )
        assert count == 2