"""Unit tests for authentication service."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import jwt
from typing import Dict, Any
import bcrypt

from app.services.auth.auth_service import AuthService
from app.domain.schemas.auth import UserCreate, UserLogin, TokenResponse
from tests.unit.utils.test_helpers import TestDataGenerator


class TestAuthService:
    """Test suite for authentication service."""
    
    @pytest.fixture
    def auth_service(self):
        """Create auth service instance."""
        return AuthService()
    
    @pytest.fixture
    def mock_user_repo(self):
        """Create mock user repository."""
        repo = AsyncMock()
        return repo
    
    @pytest.fixture
    def mock_token_service(self):
        """Create mock token service."""
        service = AsyncMock()
        return service
    
    @pytest.fixture
    def test_user(self):
        """Generate test user data."""
        return TestDataGenerator.generate_user(
            user_id=1,
            email="test@example.com",
            name="Test User",
            institution="Test University",
            role="user"
        )
    
    @pytest.mark.asyncio
    async def test_register_user_success(self, auth_service, mock_user_repo, test_user):
        """Test successful user registration."""
        auth_service.user_repository = mock_user_repo
        
        # Mock repository responses
        mock_user_repo.get_by_email.return_value = None  # Email not taken
        mock_user_repo.create.return_value = test_user
        
        # Create user data
        user_create = UserCreate(
            email="newuser@example.com",
            password="SecurePassword123!",
            name="New User",
            institution="New University"
        )
        
        # Register user
        result = await auth_service.register(user_create)
        
        assert result['user']['email'] == user_create.email
        assert result['user']['name'] == user_create.name
        assert 'access_token' in result
        assert 'refresh_token' in result
        
        # Verify password was hashed
        create_call_args = mock_user_repo.create.call_args[0][0]
        assert create_call_args['password_hash'] != user_create.password
        assert bcrypt.checkpw(
            user_create.password.encode('utf-8'),
            create_call_args['password_hash'].encode('utf-8')
        )
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, auth_service, mock_user_repo, test_user):
        """Test registration with duplicate email."""
        auth_service.user_repository = mock_user_repo
        
        # Mock existing user
        mock_user_repo.get_by_email.return_value = test_user
        
        user_create = UserCreate(
            email="test@example.com",
            password="Password123!",
            name="Another User",
            institution="University"
        )
        
        with pytest.raises(ValueError) as exc_info:
            await auth_service.register(user_create)
        
        assert "already registered" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_login_success(self, auth_service, mock_user_repo, mock_token_service, test_user):
        """Test successful login."""
        auth_service.user_repository = mock_user_repo
        auth_service.token_service = mock_token_service
        
        # Hash password for test user
        password = "TestPassword123!"
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        test_user['password_hash'] = password_hash.decode('utf-8')
        
        # Mock repository response
        mock_user_repo.get_by_email.return_value = test_user
        
        # Mock token generation
        mock_token_service.create_access_token.return_value = "access_token_123"
        mock_token_service.create_refresh_token.return_value = "refresh_token_123"
        
        # Login
        login_data = UserLogin(email="test@example.com", password=password)
        result = await auth_service.login(login_data)
        
        assert result.access_token == "access_token_123"
        assert result.refresh_token == "refresh_token_123"
        assert result.token_type == "bearer"
        
        # Verify user lookup
        mock_user_repo.get_by_email.assert_called_once_with("test@example.com")
    
    @pytest.mark.asyncio
    async def test_login_invalid_email(self, auth_service, mock_user_repo):
        """Test login with non-existent email."""
        auth_service.user_repository = mock_user_repo
        
        # Mock no user found
        mock_user_repo.get_by_email.return_value = None
        
        login_data = UserLogin(email="nonexistent@example.com", password="Password123!")
        
        with pytest.raises(ValueError) as exc_info:
            await auth_service.login(login_data)
        
        assert "invalid credentials" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_login_invalid_password(self, auth_service, mock_user_repo, test_user):
        """Test login with incorrect password."""
        auth_service.user_repository = mock_user_repo
        
        # Set correct password hash
        correct_password = "CorrectPassword123!"
        password_hash = bcrypt.hashpw(correct_password.encode('utf-8'), bcrypt.gensalt())
        test_user['password_hash'] = password_hash.decode('utf-8')
        
        mock_user_repo.get_by_email.return_value = test_user
        
        # Try with wrong password
        login_data = UserLogin(email="test@example.com", password="WrongPassword123!")
        
        with pytest.raises(ValueError) as exc_info:
            await auth_service.login(login_data)
        
        assert "invalid credentials" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_refresh_token(self, auth_service, mock_token_service):
        """Test token refresh."""
        auth_service.token_service = mock_token_service
        
        # Mock token validation and generation
        mock_token_service.verify_refresh_token.return_value = {"sub": "1", "email": "test@example.com"}
        mock_token_service.create_access_token.return_value = "new_access_token_123"
        
        result = await auth_service.refresh_token("valid_refresh_token")
        
        assert result.access_token == "new_access_token_123"
        assert result.token_type == "bearer"
        
        # Verify refresh token was validated
        mock_token_service.verify_refresh_token.assert_called_once_with("valid_refresh_token")
    
    @pytest.mark.asyncio
    async def test_logout(self, auth_service, mock_token_service):
        """Test user logout."""
        auth_service.token_service = mock_token_service
        
        # Mock token blacklisting
        mock_token_service.blacklist_token.return_value = True
        
        result = await auth_service.logout("access_token_123", "refresh_token_123")
        
        assert result['message'] == "Successfully logged out"
        
        # Verify tokens were blacklisted
        mock_token_service.blacklist_token.assert_any_call("access_token_123")
        mock_token_service.blacklist_token.assert_any_call("refresh_token_123")
    
    @pytest.mark.asyncio
    async def test_verify_email(self, auth_service, mock_user_repo, test_user):
        """Test email verification."""
        auth_service.user_repository = mock_user_repo
        
        # Mock unverified user
        test_user['is_verified'] = False
        mock_user_repo.get.return_value = test_user
        mock_user_repo.update.return_value = {**test_user, 'is_verified': True}
        
        # Create verification token
        verification_token = jwt.encode(
            {"sub": str(test_user['id']), "type": "email_verification"},
            "secret_key",
            algorithm="HS256"
        )
        
        with patch.object(auth_service, '_verify_token', return_value={"sub": "1", "type": "email_verification"}):
            result = await auth_service.verify_email(verification_token)
        
        assert result['is_verified'] is True
        
        # Verify user was updated
        mock_user_repo.update.assert_called_once()
        update_data = mock_user_repo.update.call_args[0][1]
        assert update_data['is_verified'] is True
    
    @pytest.mark.asyncio
    async def test_request_password_reset(self, auth_service, mock_user_repo, test_user):
        """Test password reset request."""
        auth_service.user_repository = mock_user_repo
        
        mock_user_repo.get_by_email.return_value = test_user
        
        with patch.object(auth_service, '_send_password_reset_email') as mock_send:
            result = await auth_service.request_password_reset("test@example.com")
        
        assert result['message'] == "Password reset email sent"
        mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_reset_password(self, auth_service, mock_user_repo, test_user):
        """Test password reset."""
        auth_service.user_repository = mock_user_repo
        
        mock_user_repo.get.return_value = test_user
        mock_user_repo.update.return_value = test_user
        
        # Create reset token
        reset_token = jwt.encode(
            {"sub": str(test_user['id']), "type": "password_reset"},
            "secret_key",
            algorithm="HS256"
        )
        
        new_password = "NewSecurePassword123!"
        
        with patch.object(auth_service, '_verify_token', return_value={"sub": "1", "type": "password_reset"}):
            result = await auth_service.reset_password(reset_token, new_password)
        
        assert result['message'] == "Password successfully reset"
        
        # Verify password was updated
        mock_user_repo.update.assert_called_once()
        update_data = mock_user_repo.update.call_args[0][1]
        assert bcrypt.checkpw(
            new_password.encode('utf-8'),
            update_data['password_hash'].encode('utf-8')
        )
    
    @pytest.mark.asyncio
    async def test_validate_password_strength(self, auth_service):
        """Test password strength validation."""
        # Test weak passwords
        weak_passwords = [
            "short",  # Too short
            "alllowercase",  # No uppercase or numbers
            "ALLUPPERCASE",  # No lowercase or numbers
            "NoNumbers!",  # No numbers
            "N0Symb0ls",  # No special characters
            "password123!",  # Common password
        ]
        
        for password in weak_passwords:
            is_valid, message = auth_service.validate_password_strength(password)
            assert not is_valid
            assert message is not None
        
        # Test strong passwords
        strong_passwords = [
            "SecurePass123!",
            "MyStr0ng@Password",
            "C0mpl3x!P@ssw0rd",
        ]
        
        for password in strong_passwords:
            is_valid, message = auth_service.validate_password_strength(password)
            assert is_valid
            assert message is None
    
    @pytest.mark.asyncio
    async def test_change_password(self, auth_service, mock_user_repo, test_user):
        """Test password change for authenticated user."""
        auth_service.user_repository = mock_user_repo
        
        # Set current password
        current_password = "CurrentPassword123!"
        password_hash = bcrypt.hashpw(current_password.encode('utf-8'), bcrypt.gensalt())
        test_user['password_hash'] = password_hash.decode('utf-8')
        
        mock_user_repo.get.return_value = test_user
        mock_user_repo.update.return_value = test_user
        
        new_password = "NewPassword123!"
        
        result = await auth_service.change_password(
            user_id=test_user['id'],
            current_password=current_password,
            new_password=new_password
        )
        
        assert result['message'] == "Password successfully changed"
        
        # Verify new password hash
        update_data = mock_user_repo.update.call_args[0][1]
        assert bcrypt.checkpw(
            new_password.encode('utf-8'),
            update_data['password_hash'].encode('utf-8')
        )
    
    @pytest.mark.asyncio
    async def test_get_current_user(self, auth_service, mock_user_repo, mock_token_service, test_user):
        """Test getting current user from token."""
        auth_service.user_repository = mock_user_repo
        auth_service.token_service = mock_token_service
        
        # Mock token validation
        mock_token_service.verify_access_token.return_value = {
            "sub": str(test_user['id']),
            "email": test_user['email']
        }
        
        mock_user_repo.get.return_value = test_user
        
        result = await auth_service.get_current_user("valid_token")
        
        assert result['id'] == test_user['id']
        assert result['email'] == test_user['email']
        
        # Verify token was validated
        mock_token_service.verify_access_token.assert_called_once_with("valid_token")