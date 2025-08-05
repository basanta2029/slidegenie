"""
Integration tests for Role-Based Access Control and API Key authentication.

Tests permission enforcement, role management, and API key functionality.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import User
from app.services.auth.authorization.rbac import RoleType


@pytest.mark.integration
@pytest.mark.asyncio
class TestRoleBasedAccessControl:
    """Test RBAC implementation and permission enforcement."""
    
    async def test_role_based_endpoint_access(
        self,
        authenticated_client: AsyncClient,
        admin_client: AsyncClient,
        test_user: User,
        admin_user: User,
    ):
        """Test role-based access to different endpoints."""
        # Regular user shouldn't access admin endpoints
        response = await authenticated_client.get("/api/v1/admin/users")
        assert response.status_code == 403
        
        response = await authenticated_client.get("/api/v1/admin/analytics")
        assert response.status_code == 403
        
        # Admin should access admin endpoints
        response = await admin_client.get("/api/v1/admin/users")
        assert response.status_code == 200
        
        response = await admin_client.get("/api/v1/admin/analytics")
        assert response.status_code == 200
        
        # Both should access regular endpoints
        response = await authenticated_client.get("/api/v1/presentations")
        assert response.status_code == 200
        
        response = await admin_client.get("/api/v1/presentations")
        assert response.status_code == 200
    
    async def test_template_management_permissions(
        self,
        authenticated_client: AsyncClient,
        admin_client: AsyncClient,
    ):
        """Test template management requires admin role."""
        template_data = {
            "name": "Test Template",
            "description": "Test template description",
            "category": "academic",
            "slides": [],
            "is_public": True,
        }
        
        # Regular user cannot create templates
        response = await authenticated_client.post(
            "/api/v1/templates",
            json=template_data,
        )
        assert response.status_code == 403
        
        # Admin can create templates
        response = await admin_client.post(
            "/api/v1/templates",
            json=template_data,
        )
        assert response.status_code == 201
        template_id = response.json()["id"]
        
        # Regular user can read public templates
        response = await authenticated_client.get(
            f"/api/v1/templates/{template_id}"
        )
        assert response.status_code == 200
        
        # Regular user cannot update templates
        response = await authenticated_client.put(
            f"/api/v1/templates/{template_id}",
            json={"name": "Updated Template"},
        )
        assert response.status_code == 403
        
        # Admin can update templates
        response = await admin_client.put(
            f"/api/v1/templates/{template_id}",
            json={"name": "Updated Template"},
        )
        assert response.status_code == 200
    
    async def test_faculty_department_access(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        token_service,
    ):
        """Test faculty-specific department access."""
        # Create faculty user
        from app.core.security import get_password_hash
        
        faculty_user = User(
            email="professor@university.edu",
            password_hash=get_password_hash("ProfessorP@ss123!"),
            full_name="Professor Smith",
            institution="University",
            role="faculty",
            department="Computer Science",
            is_active=True,
            is_verified=True,
        )
        db_session.add(faculty_user)
        await db_session.commit()
        
        # Create faculty token
        faculty_tokens = await token_service.create_token_pair(
            user_id=faculty_user.id,
            email=faculty_user.email,
            roles=[faculty_user.role],
            institution=faculty_user.institution,
        )
        
        faculty_client = AsyncClient(app=client.app, base_url=str(client.base_url))
        faculty_client.headers["Authorization"] = f"Bearer {faculty_tokens.access_token}"
        
        # Faculty can access department analytics
        response = await faculty_client.get(
            "/api/v1/analytics/department",
            params={"department": "Computer Science"},
        )
        assert response.status_code == 200
        
        # Faculty can manage department collaborations
        response = await faculty_client.post(
            "/api/v1/collaborations/invite",
            json={
                "email": "colleague@university.edu",
                "role": "viewer",
                "department_wide": True,
            },
        )
        assert response.status_code in [200, 201]
        
        # Regular user cannot access department features
        student_client = client
        student_client.headers["Authorization"] = f"Bearer {faculty_tokens.access_token}"
        
        response = await student_client.get("/api/v1/analytics/department")
        assert response.status_code == 403
    
    async def test_dynamic_permission_checking(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test dynamic permission checking for resources."""
        # Create a presentation
        response = await authenticated_client.post(
            "/api/v1/presentations",
            json={
                "title": "Permission Test",
                "slides": [],
            },
        )
        presentation_id = response.json()["id"]
        
        # Owner has full permissions
        response = await authenticated_client.get(
            f"/api/v1/presentations/{presentation_id}/permissions"
        )
        assert response.status_code == 200
        permissions = response.json()
        
        assert permissions["can_read"] is True
        assert permissions["can_update"] is True
        assert permissions["can_delete"] is True
        assert permissions["can_share"] is True
        
        # Create another user
        other_user = User(
            email="other@university.edu",
            password_hash="hash",
            full_name="Other User",
            institution="University",
            role="student",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other_user)
        await db_session.commit()
        
        # Other user has no permissions
        from app.services.auth.token_service import TokenService
        token_service = TokenService()
        other_tokens = await token_service.create_token_pair(
            user_id=other_user.id,
            email=other_user.email,
            roles=[other_user.role],
            institution=other_user.institution,
        )
        
        other_client = AsyncClient(app=authenticated_client.app, base_url=str(authenticated_client.base_url))
        other_client.headers["Authorization"] = f"Bearer {other_tokens.access_token}"
        
        response = await other_client.get(
            f"/api/v1/presentations/{presentation_id}/permissions"
        )
        assert response.status_code == 403
    
    async def test_role_elevation_prevention(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
    ):
        """Test prevention of unauthorized role elevation."""
        # Try to update own role
        response = await authenticated_client.put(
            "/api/v1/users/me",
            json={
                "role": "admin",
            },
        )
        
        # Should either be forbidden or role should be ignored
        if response.status_code == 200:
            data = response.json()
            assert data["role"] != "admin"
        else:
            assert response.status_code == 403
        
        # Try to add admin permissions
        response = await authenticated_client.post(
            "/api/v1/users/me/roles",
            json={
                "roles": ["admin", "superuser"],
            },
        )
        assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
class TestAPIKeyAuthentication:
    """Test API key generation and authentication."""
    
    async def test_api_key_lifecycle(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test complete API key lifecycle."""
        # Create API key
        response = await authenticated_client.post(
            "/api/v1/auth/api-keys",
            json={
                "name": "Test API Key",
                "description": "Key for integration testing",
                "scopes": ["read:presentations", "write:presentations"],
                "expires_in_days": 30,
            },
        )
        
        assert response.status_code == 201
        key_data = response.json()
        
        assert "key" in key_data
        assert "key_id" in key_data
        assert key_data["name"] == "Test API Key"
        assert key_data["prefix"].startswith("sk_")
        
        api_key = key_data["key"]
        key_id = key_data["key_id"]
        
        # Use API key for authentication
        api_client = AsyncClient(
            app=authenticated_client.app,
            base_url=str(authenticated_client.base_url),
            headers={"X-API-Key": api_key},
        )
        
        # Test API key works
        response = await api_client.get("/api/v1/presentations")
        assert response.status_code == 200
        
        # List API keys
        response = await authenticated_client.get("/api/v1/auth/api-keys")
        assert response.status_code == 200
        keys = response.json()
        
        assert len(keys) > 0
        assert any(k["key_id"] == key_id for k in keys)
        
        # Revoke API key
        response = await authenticated_client.delete(
            f"/api/v1/auth/api-keys/{key_id}"
        )
        assert response.status_code == 204
        
        # Verify key no longer works
        response = await api_client.get("/api/v1/presentations")
        assert response.status_code == 401
    
    async def test_api_key_scope_enforcement(
        self,
        authenticated_client: AsyncClient,
    ):
        """Test API key scope restrictions."""
        # Create read-only API key
        response = await authenticated_client.post(
            "/api/v1/auth/api-keys",
            json={
                "name": "Read Only Key",
                "scopes": ["read:presentations"],
            },
        )
        
        read_key = response.json()["key"]
        
        # Create write API key
        response = await authenticated_client.post(
            "/api/v1/auth/api-keys",
            json={
                "name": "Write Key",
                "scopes": ["read:presentations", "write:presentations"],
            },
        )
        
        write_key = response.json()["key"]
        
        # Test read-only key
        read_client = AsyncClient(
            app=authenticated_client.app,
            base_url=str(authenticated_client.base_url),
            headers={"X-API-Key": read_key},
        )
        
        # Can read
        response = await read_client.get("/api/v1/presentations")
        assert response.status_code == 200
        
        # Cannot write
        response = await read_client.post(
            "/api/v1/presentations",
            json={"title": "Test", "slides": []},
        )
        assert response.status_code == 403
        
        # Test write key
        write_client = AsyncClient(
            app=authenticated_client.app,
            base_url=str(authenticated_client.base_url),
            headers={"X-API-Key": write_key},
        )
        
        # Can read and write
        response = await write_client.get("/api/v1/presentations")
        assert response.status_code == 200
        
        response = await write_client.post(
            "/api/v1/presentations",
            json={"title": "Test", "slides": []},
        )
        assert response.status_code == 201
    
    async def test_api_key_rate_limiting(
        self,
        authenticated_client: AsyncClient,
    ):
        """Test API key specific rate limiting."""
        # Create API key with custom rate limit
        response = await authenticated_client.post(
            "/api/v1/auth/api-keys",
            json={
                "name": "Limited Key",
                "scopes": ["read:presentations"],
                "rate_limit": 10,  # 10 requests per minute
            },
        )
        
        api_key = response.json()["key"]
        
        api_client = AsyncClient(
            app=authenticated_client.app,
            base_url=str(authenticated_client.base_url),
            headers={"X-API-Key": api_key},
        )
        
        # Make requests up to limit
        for i in range(12):
            response = await api_client.get("/api/v1/presentations")
            
            if i < 10:
                assert response.status_code == 200
            else:
                # Should be rate limited
                assert response.status_code == 429
                assert "rate limit" in response.json()["detail"].lower()
    
    async def test_api_key_expiration(
        self,
        authenticated_client: AsyncClient,
        mocker,
    ):
        """Test API key expiration handling."""
        # Create short-lived API key
        response = await authenticated_client.post(
            "/api/v1/auth/api-keys",
            json={
                "name": "Short Lived Key",
                "scopes": ["read:presentations"],
                "expires_in_days": 0.01,  # ~15 minutes
            },
        )
        
        api_key = response.json()["key"]
        expires_at = response.json()["expires_at"]
        
        # Verify expiration date is set
        assert expires_at is not None
        
        # Key should work initially
        api_client = AsyncClient(
            app=authenticated_client.app,
            base_url=str(authenticated_client.base_url),
            headers={"X-API-Key": api_key},
        )
        
        response = await api_client.get("/api/v1/presentations")
        assert response.status_code == 200
        
        # Note: Testing actual expiration would require time manipulation
    
    async def test_api_key_usage_tracking(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test API key usage statistics."""
        # Create API key
        response = await authenticated_client.post(
            "/api/v1/auth/api-keys",
            json={
                "name": "Tracked Key",
                "scopes": ["read:presentations"],
                "track_usage": True,
            },
        )
        
        api_key = response.json()["key"]
        key_id = response.json()["key_id"]
        
        api_client = AsyncClient(
            app=authenticated_client.app,
            base_url=str(authenticated_client.base_url),
            headers={"X-API-Key": api_key},
        )
        
        # Make several requests
        for _ in range(5):
            await api_client.get("/api/v1/presentations")
        
        # Get usage statistics
        response = await authenticated_client.get(
            f"/api/v1/auth/api-keys/{key_id}/usage"
        )
        
        assert response.status_code == 200
        usage = response.json()
        
        assert usage["total_requests"] >= 5
        assert "last_used_at" in usage
        assert "requests_by_endpoint" in usage