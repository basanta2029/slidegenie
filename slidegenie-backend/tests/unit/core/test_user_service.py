"""Unit tests for user service."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any, List

from app.services.user import UserService
from app.domain.schemas.user import UserUpdate, UserPreferences
from tests.unit.utils.test_helpers import TestDataGenerator, MockFileStorage


class TestUserService:
    """Test suite for user service."""
    
    @pytest.fixture
    def user_service(self):
        """Create user service instance."""
        return UserService()
    
    @pytest.fixture
    def mock_user_repo(self):
        """Create mock user repository."""
        repo = AsyncMock()
        return repo
    
    @pytest.fixture
    def mock_file_storage(self):
        """Create mock file storage."""
        return MockFileStorage()
    
    @pytest.fixture
    def test_user(self):
        """Generate test user data."""
        return TestDataGenerator.generate_user()
    
    @pytest.fixture
    def test_users(self):
        """Generate multiple test users."""
        return [
            TestDataGenerator.generate_user(user_id=i, email=f"user{i}@example.com")
            for i in range(1, 6)
        ]
    
    @pytest.mark.asyncio
    async def test_get_user_by_id(self, user_service, mock_user_repo, test_user):
        """Test getting user by ID."""
        user_service.user_repository = mock_user_repo
        mock_user_repo.get.return_value = test_user
        
        result = await user_service.get_user(test_user['id'])
        
        assert result['id'] == test_user['id']
        assert result['email'] == test_user['email']
        mock_user_repo.get.assert_called_once_with(test_user['id'])
    
    @pytest.mark.asyncio
    async def test_get_user_not_found(self, user_service, mock_user_repo):
        """Test getting non-existent user."""
        user_service.user_repository = mock_user_repo
        mock_user_repo.get.return_value = None
        
        with pytest.raises(ValueError) as exc_info:
            await user_service.get_user(999)
        
        assert "not found" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_update_user_profile(self, user_service, mock_user_repo, test_user):
        """Test updating user profile."""
        user_service.user_repository = mock_user_repo
        
        mock_user_repo.get.return_value = test_user
        updated_user = {**test_user, "name": "Updated Name", "institution": "New University"}
        mock_user_repo.update.return_value = updated_user
        
        update_data = UserUpdate(
            name="Updated Name",
            institution="New University"
        )
        
        result = await user_service.update_profile(test_user['id'], update_data)
        
        assert result['name'] == "Updated Name"
        assert result['institution'] == "New University"
        
        # Verify update was called with correct data
        mock_user_repo.update.assert_called_once()
        update_call_data = mock_user_repo.update.call_args[0][1]
        assert update_call_data['name'] == "Updated Name"
        assert update_call_data['institution'] == "New University"
    
    @pytest.mark.asyncio
    async def test_update_user_preferences(self, user_service, mock_user_repo, test_user):
        """Test updating user preferences."""
        user_service.user_repository = mock_user_repo
        
        mock_user_repo.get.return_value = test_user
        
        preferences = UserPreferences(
            theme="dark",
            language="en",
            default_template="academic",
            slide_duration=30,
            enable_animations=True,
            email_notifications=True
        )
        
        updated_user = {**test_user, "preferences": preferences.dict()}
        mock_user_repo.update.return_value = updated_user
        
        result = await user_service.update_preferences(test_user['id'], preferences)
        
        assert result['preferences']['theme'] == "dark"
        assert result['preferences']['default_template'] == "academic"
        assert result['preferences']['slide_duration'] == 30
    
    @pytest.mark.asyncio
    async def test_upload_profile_picture(self, user_service, mock_user_repo, mock_file_storage, test_user):
        """Test profile picture upload."""
        user_service.user_repository = mock_user_repo
        user_service.file_storage = mock_file_storage
        
        mock_user_repo.get.return_value = test_user
        
        # Mock file upload
        file_content = b"fake_image_data"
        file_path = f"users/{test_user['id']}/profile.jpg"
        
        updated_user = {**test_user, "profile_picture": file_path}
        mock_user_repo.update.return_value = updated_user
        
        result = await user_service.upload_profile_picture(test_user['id'], file_content, "image/jpeg")
        
        assert result['profile_picture'] == file_path
        assert mock_file_storage.upload_count == 1
        assert file_path in mock_file_storage.files
    
    @pytest.mark.asyncio
    async def test_delete_user_account(self, user_service, mock_user_repo, test_user):
        """Test user account deletion."""
        user_service.user_repository = mock_user_repo
        
        mock_user_repo.get.return_value = test_user
        mock_user_repo.delete.return_value = True
        
        # Mock cascade deletion of related data
        with patch.object(user_service, '_delete_user_data', new_callable=AsyncMock) as mock_delete_data:
            result = await user_service.delete_account(test_user['id'])
        
        assert result['message'] == "Account successfully deleted"
        mock_user_repo.delete.assert_called_once_with(test_user['id'])
        mock_delete_data.assert_called_once_with(test_user['id'])
    
    @pytest.mark.asyncio
    async def test_get_user_statistics(self, user_service, mock_user_repo, test_user):
        """Test getting user statistics."""
        user_service.user_repository = mock_user_repo
        
        mock_user_repo.get.return_value = test_user
        
        # Mock statistics gathering
        with patch.object(user_service, '_gather_user_statistics', new_callable=AsyncMock) as mock_stats:
            mock_stats.return_value = {
                "total_presentations": 15,
                "total_slides": 234,
                "storage_used_mb": 125.5,
                "last_active": datetime.utcnow(),
                "favorite_template": "academic",
                "average_slides_per_presentation": 15.6
            }
            
            result = await user_service.get_statistics(test_user['id'])
        
        assert result['total_presentations'] == 15
        assert result['total_slides'] == 234
        assert result['storage_used_mb'] == 125.5
        assert 'last_active' in result
    
    @pytest.mark.asyncio
    async def test_list_users_with_pagination(self, user_service, mock_user_repo, test_users):
        """Test listing users with pagination."""
        user_service.user_repository = mock_user_repo
        
        # Mock paginated response
        mock_user_repo.list.return_value = {
            "items": test_users[:3],  # First 3 users
            "total": len(test_users),
            "page": 1,
            "size": 3
        }
        
        result = await user_service.list_users(page=1, size=3)
        
        assert len(result['items']) == 3
        assert result['total'] == 5
        assert result['page'] == 1
        
        mock_user_repo.list.assert_called_once_with(
            skip=0,
            limit=3,
            filters=None,
            sort_by=None
        )
    
    @pytest.mark.asyncio
    async def test_search_users(self, user_service, mock_user_repo, test_users):
        """Test user search functionality."""
        user_service.user_repository = mock_user_repo
        
        # Mock search results
        search_results = [u for u in test_users if "user1" in u['email']]
        mock_user_repo.search.return_value = search_results
        
        result = await user_service.search_users(query="user1")
        
        assert len(result) == 1
        assert result[0]['email'] == "user1@example.com"
        
        mock_user_repo.search.assert_called_once_with(
            query="user1",
            fields=['email', 'name', 'institution']
        )
    
    @pytest.mark.asyncio
    async def test_export_user_data(self, user_service, mock_user_repo, test_user):
        """Test user data export (GDPR compliance)."""
        user_service.user_repository = mock_user_repo
        
        mock_user_repo.get.return_value = test_user
        
        # Mock data collection
        with patch.object(user_service, '_collect_user_data', new_callable=AsyncMock) as mock_collect:
            mock_collect.return_value = {
                "profile": test_user,
                "presentations": [TestDataGenerator.generate_presentation()],
                "activity_logs": [],
                "preferences": {}
            }
            
            result = await user_service.export_user_data(test_user['id'])
        
        assert 'profile' in result
        assert 'presentations' in result
        assert result['profile']['email'] == test_user['email']
        assert len(result['presentations']) == 1
    
    @pytest.mark.asyncio
    async def test_verify_user_permissions(self, user_service, mock_user_repo, test_user):
        """Test user permission verification."""
        user_service.user_repository = mock_user_repo
        
        # Test admin user
        admin_user = {**test_user, "role": "admin"}
        mock_user_repo.get.return_value = admin_user
        
        has_permission = await user_service.check_permission(
            user_id=test_user['id'],
            permission="manage_users"
        )
        assert has_permission is True
        
        # Test regular user
        regular_user = {**test_user, "role": "user"}
        mock_user_repo.get.return_value = regular_user
        
        has_permission = await user_service.check_permission(
            user_id=test_user['id'],
            permission="manage_users"
        )
        assert has_permission is False
    
    @pytest.mark.asyncio
    async def test_update_last_login(self, user_service, mock_user_repo, test_user):
        """Test updating user's last login timestamp."""
        user_service.user_repository = mock_user_repo
        
        mock_user_repo.get.return_value = test_user
        
        now = datetime.utcnow()
        updated_user = {**test_user, "last_login": now}
        mock_user_repo.update.return_value = updated_user
        
        result = await user_service.update_last_login(test_user['id'])
        
        assert result['last_login'] == now
        
        # Verify update was called
        mock_user_repo.update.assert_called_once()
        update_data = mock_user_repo.update.call_args[0][1]
        assert 'last_login' in update_data
    
    @pytest.mark.asyncio
    async def test_get_user_quota(self, user_service, mock_user_repo, test_user):
        """Test getting user storage quota."""
        user_service.user_repository = mock_user_repo
        
        mock_user_repo.get.return_value = test_user
        
        # Mock quota calculation
        with patch.object(user_service, '_calculate_quota_usage', new_callable=AsyncMock) as mock_quota:
            mock_quota.return_value = {
                "used_mb": 256.7,
                "total_mb": 1024,
                "percentage_used": 25.1,
                "presentations_count": 12,
                "max_presentations": 100
            }
            
            result = await user_service.get_quota(test_user['id'])
        
        assert result['used_mb'] == 256.7
        assert result['total_mb'] == 1024
        assert result['percentage_used'] == 25.1
        assert result['presentations_count'] == 12
    
    @pytest.mark.asyncio
    async def test_bulk_update_users(self, user_service, mock_user_repo, test_users):
        """Test bulk update of multiple users."""
        user_service.user_repository = mock_user_repo
        
        user_ids = [u['id'] for u in test_users[:3]]
        update_data = {"institution": "New Institution"}
        
        mock_user_repo.bulk_update.return_value = 3
        
        result = await user_service.bulk_update(user_ids, update_data)
        
        assert result['updated_count'] == 3
        mock_user_repo.bulk_update.assert_called_once_with(user_ids, update_data)
    
    @pytest.mark.asyncio
    async def test_user_activity_tracking(self, user_service, mock_user_repo, test_user):
        """Test user activity tracking."""
        user_service.user_repository = mock_user_repo
        
        activity = {
            "action": "create_presentation",
            "details": {"presentation_id": 123, "title": "New Presentation"},
            "timestamp": datetime.utcnow()
        }
        
        with patch.object(user_service, '_log_activity', new_callable=AsyncMock) as mock_log:
            await user_service.track_activity(test_user['id'], activity)
        
        mock_log.assert_called_once_with(test_user['id'], activity)