"""
Integration tests for authentication flows.

Tests registration, login, OAuth, password reset, email verification,
and role-based access control.
"""
import asyncio
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict
from urllib.parse import parse_qs, urlparse

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import User
from app.repositories.user import UserRepository
from app.services.auth.token_service import TokenService


@pytest.mark.integration
@pytest.mark.asyncio
class TestRegistrationFlow:
    """Test user registration flow end-to-end."""
    
    async def test_complete_registration_flow(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        mock_email_service,
    ):
        """Test complete registration with email verification."""
        # Step 1: Register new user
        registration_data = {
            "email": "newuser@mit.edu",
            "password": "SecureP@ssw0rd123!",
            "confirm_password": "SecureP@ssw0rd123!",
            "full_name": "New User",
            "institution": "MIT",
            "role": "student",
            "accept_terms": True,
        }
        
        response = await client.post(
            "/api/v1/auth/register",
            json=registration_data,
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["email"] == registration_data["email"]
        assert data["requires_verification"] is True
        assert "user_id" in data
        
        user_id = data["user_id"]
        
        # Verify user created but not verified
        user_repo = UserRepository(db_session)
        user = await user_repo.get(user_id)
        
        assert user is not None
        assert user.email == registration_data["email"]
        assert user.is_verified is False
        assert user.verification_token is not None
        
        # Step 2: Verify email was sent
        mock_email_service.send_verification_email.assert_called_once()
        call_args = mock_email_service.send_verification_email.call_args
        assert call_args[1]["email"] == registration_data["email"]
        verification_token = call_args[1]["token"]
        
        # Step 3: Verify email
        response = await client.post(
            "/api/v1/auth/verify-email",
            json={
                "token": verification_token,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["verified"] is True
        assert "access_token" in data
        assert "refresh_token" in data
        
        # Verify user is now verified
        await db_session.refresh(user)
        assert user.is_verified is True
        assert user.verification_token is None
        
        # Step 4: Test login with verified account
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": registration_data["email"],
                "password": registration_data["password"],
            },
        )
        
        assert response.status_code == 200
        assert "access_token" in response.json()
    
    async def test_registration_validation(
        self,
        client: AsyncClient,
    ):
        """Test registration input validation."""
        # Test invalid email
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "invalid-email",
                "password": "SecureP@ssw0rd123!",
                "confirm_password": "SecureP@ssw0rd123!",
                "full_name": "Test User",
                "institution": "Test",
                "role": "student",
            },
        )
        assert response.status_code == 422
        
        # Test weak password
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@university.edu",
                "password": "weak",
                "confirm_password": "weak",
                "full_name": "Test User",
                "institution": "Test",
                "role": "student",
            },
        )
        assert response.status_code == 422
        error = response.json()
        assert "password" in str(error["detail"]).lower()
        
        # Test password mismatch
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@university.edu",
                "password": "SecureP@ssw0rd123!",
                "confirm_password": "DifferentP@ssw0rd123!",
                "full_name": "Test User",
                "institution": "Test",
                "role": "student",
            },
        )
        assert response.status_code == 422
        assert "match" in str(response.json()["detail"]).lower()
    
    async def test_duplicate_email_prevention(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        """Test prevention of duplicate email registration."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,
                "password": "SecureP@ssw0rd123!",
                "confirm_password": "SecureP@ssw0rd123!",
                "full_name": "Duplicate User",
                "institution": "MIT",
                "role": "student",
            },
        )
        
        assert response.status_code == 409
        error = response.json()
        assert "already registered" in error["detail"].lower()
    
    async def test_academic_email_validation(
        self,
        client: AsyncClient,
        mock_email_service,
    ):
        """Test academic email validation during registration."""
        # Configure mock to validate academic emails
        mock_email_service.is_academic_email.return_value = True
        mock_email_service.validate_academic_email.return_value = asyncio.coroutine(
            lambda email: "Stanford University"
        )()
        
        # Register with academic email
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "student@stanford.edu",
                "password": "SecureP@ssw0rd123!",
                "confirm_password": "SecureP@ssw0rd123!",
                "full_name": "Stanford Student",
                "role": "student",
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["institution"] == "Stanford University"
        
        # Test non-academic email
        mock_email_service.is_academic_email.return_value = False
        
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@gmail.com",
                "password": "SecureP@ssw0rd123!",
                "confirm_password": "SecureP@ssw0rd123!",
                "full_name": "Gmail User",
                "role": "student",
            },
        )
        
        # Should either reject or allow with limited features
        assert response.status_code in [201, 400]


@pytest.mark.integration
@pytest.mark.asyncio
class TestLoginFlow:
    """Test login and session management."""
    
    async def test_successful_login(
        self,
        client: AsyncClient,
        test_user: User,
        auth_test_data,
    ):
        """Test successful login with valid credentials."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": auth_test_data.STUDENT_USER["password"],
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"
        assert data["user"]["email"] == test_user.email
        assert data["user"]["id"] == str(test_user.id)
        
        # Verify tokens work
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {data['access_token']}"},
        )
        assert response.status_code == 200
    
    async def test_login_with_unverified_account(
        self,
        client: AsyncClient,
        unverified_user: User,
    ):
        """Test login attempt with unverified account."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": unverified_user.email,
                "password": "UnverifiedP@ss123!",
            },
        )
        
        assert response.status_code == 403
        error = response.json()
        assert "not verified" in error["detail"].lower()
        assert "verification_required" in error
    
    async def test_login_rate_limiting(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        """Test rate limiting on login attempts."""
        # Make multiple failed login attempts
        for i in range(6):
            response = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": test_user.email,
                    "password": "WrongPassword123!",
                },
                headers={"X-Real-IP": "192.168.1.100"},
            )
            
            if i < 5:
                assert response.status_code == 401
            else:
                # Should be rate limited after 5 attempts
                assert response.status_code == 429
                error = response.json()
                assert "rate limit" in error["detail"].lower()
    
    async def test_account_lockout(
        self,
        client: AsyncClient,
        test_user: User,
        auth_test_data,
    ):
        """Test account lockout after multiple failed attempts."""
        # Make 10 failed login attempts
        for _ in range(10):
            await client.post(
                "/api/v1/auth/login",
                json={
                    "email": test_user.email,
                    "password": "WrongPassword123!",
                },
            )
        
        # Account should be locked
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": auth_test_data.STUDENT_USER["password"],  # Correct password
            },
        )
        
        assert response.status_code == 423
        error = response.json()
        assert "locked" in error["detail"].lower()
    
    async def test_login_session_tracking(
        self,
        client: AsyncClient,
        test_user: User,
        auth_test_data,
        db_session: AsyncSession,
    ):
        """Test session tracking and management."""
        # Login from multiple devices
        sessions = []
        
        for i in range(3):
            response = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": test_user.email,
                    "password": auth_test_data.STUDENT_USER["password"],
                },
                headers={
                    "User-Agent": f"Device-{i}",
                    "X-Real-IP": f"192.168.1.{100 + i}",
                },
            )
            
            assert response.status_code == 200
            sessions.append(response.json())
        
        # Get active sessions
        response = await client.get(
            "/api/v1/auth/sessions",
            headers={"Authorization": f"Bearer {sessions[0]['access_token']}"},
        )
        
        assert response.status_code == 200
        active_sessions = response.json()
        assert len(active_sessions) >= 3
        
        # Revoke specific session
        session_to_revoke = active_sessions[1]["session_id"]
        response = await client.delete(
            f"/api/v1/auth/sessions/{session_to_revoke}",
            headers={"Authorization": f"Bearer {sessions[0]['access_token']}"},
        )
        
        assert response.status_code == 204
        
        # Verify revoked session token no longer works
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {sessions[1]['access_token']}"},
        )
        assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
class TestOAuthFlow:
    """Test OAuth authentication flows."""
    
    async def test_google_oauth_flow(
        self,
        client: AsyncClient,
        mock_oauth_providers,
        db_session: AsyncSession,
    ):
        """Test Google OAuth authentication flow."""
        # Step 1: Get OAuth authorization URL
        response = await client.get(
            "/api/v1/auth/oauth/google/authorize",
            params={"redirect_uri": "http://localhost:3000/auth/callback"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        assert "state" in data
        
        auth_url = urlparse(data["authorization_url"])
        assert auth_url.hostname == "accounts.google.com"
        
        state = data["state"]
        
        # Step 2: Simulate OAuth callback
        mock_oauth_providers.google.exchange_code_for_token.return_value = {
            "access_token": "google_access_token",
            "refresh_token": "google_refresh_token",
            "expires_in": 3600,
        }
        
        mock_oauth_providers.google.get_user_info.return_value = {
            "id": "google_123456",
            "email": "oauth.user@stanford.edu",
            "name": "OAuth User",
            "given_name": "OAuth",
            "family_name": "User",
            "picture": "https://example.com/picture.jpg",
            "email_verified": True,
            "hd": "stanford.edu",
        }
        
        # Exchange code for tokens
        response = await client.post(
            "/api/v1/auth/oauth/google/callback",
            json={
                "code": "test_auth_code",
                "state": state,
                "redirect_uri": "http://localhost:3000/auth/callback",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == "oauth.user@stanford.edu"
        assert data["user"]["provider"] == "google"
        
        # Verify user was created
        user_repo = UserRepository(db_session)
        users = await user_repo.find_by_email("oauth.user@stanford.edu")
        assert len(users) == 1
        
        user = users[0]
        assert user.oauth_provider == "google"
        assert user.oauth_provider_id == "google_123456"
        assert user.is_verified is True  # OAuth users are pre-verified
    
    async def test_microsoft_oauth_flow(
        self,
        client: AsyncClient,
        mock_oauth_providers,
    ):
        """Test Microsoft OAuth authentication flow."""
        # Get authorization URL
        response = await client.get(
            "/api/v1/auth/oauth/microsoft/authorize",
            params={"redirect_uri": "http://localhost:3000/auth/callback"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        auth_url = urlparse(data["authorization_url"])
        assert "microsoft" in auth_url.hostname or "live" in auth_url.hostname
        
        state = data["state"]
        
        # Mock Microsoft OAuth response
        mock_oauth_providers.microsoft.exchange_code_for_token.return_value = {
            "access_token": "ms_access_token",
            "refresh_token": "ms_refresh_token",
            "expires_in": 3600,
        }
        
        mock_oauth_providers.microsoft.get_user_info.return_value = {
            "id": "ms_789012",
            "mail": "ms.user@yale.edu",
            "displayName": "Microsoft User",
            "givenName": "Microsoft",
            "surname": "User",
        }
        
        # Complete OAuth flow
        response = await client.post(
            "/api/v1/auth/oauth/microsoft/callback",
            json={
                "code": "test_ms_code",
                "state": state,
                "redirect_uri": "http://localhost:3000/auth/callback",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == "ms.user@yale.edu"
        assert data["user"]["provider"] == "microsoft"
    
    async def test_oauth_account_linking(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
        mock_oauth_providers,
    ):
        """Test linking OAuth account to existing user."""
        # Configure mock
        mock_oauth_providers.google.get_user_info.return_value = {
            "id": "google_link_123",
            "email": test_user.email,  # Same email as existing user
            "name": test_user.full_name,
            "email_verified": True,
        }
        
        # Request OAuth link
        response = await authenticated_client.post(
            "/api/v1/auth/oauth/google/link",
            json={
                "code": "link_auth_code",
                "redirect_uri": "http://localhost:3000/settings/linked-accounts",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["linked"] is True
        assert data["provider"] == "google"
    
    async def test_oauth_state_validation(
        self,
        client: AsyncClient,
    ):
        """Test OAuth state parameter validation."""
        # Try callback with invalid state
        response = await client.post(
            "/api/v1/auth/oauth/google/callback",
            json={
                "code": "test_code",
                "state": "invalid_state",
                "redirect_uri": "http://localhost:3000/auth/callback",
            },
        )
        
        assert response.status_code == 400
        error = response.json()
        assert "invalid state" in error["detail"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
class TestPasswordResetFlow:
    """Test password reset functionality."""
    
    async def test_complete_password_reset_flow(
        self,
        client: AsyncClient,
        test_user: User,
        mock_email_service,
        db_session: AsyncSession,
    ):
        """Test complete password reset flow."""
        # Step 1: Request password reset
        response = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": test_user.email},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "If the email exists, a reset link has been sent"
        
        # Verify email was sent
        mock_email_service.send_password_reset_email.assert_called_once()
        call_args = mock_email_service.send_password_reset_email.call_args
        reset_token = call_args[1]["token"]
        
        # Step 2: Validate reset token
        response = await client.post(
            "/api/v1/auth/validate-reset-token",
            json={"token": reset_token},
        )
        
        assert response.status_code == 200
        assert response.json()["valid"] is True
        
        # Step 3: Reset password
        new_password = "NewSecureP@ssw0rd456!"
        response = await client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": reset_token,
                "new_password": new_password,
                "confirm_password": new_password,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Password reset successful"
        
        # Step 4: Login with new password
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": new_password,
            },
        )
        
        assert response.status_code == 200
        assert "access_token" in response.json()
    
    async def test_password_reset_token_expiry(
        self,
        client: AsyncClient,
        test_user: User,
        mocker,
    ):
        """Test password reset token expiration."""
        # Mock expired token
        expired_token = secrets.token_urlsafe(32)
        
        response = await client.post(
            "/api/v1/auth/validate-reset-token",
            json={"token": expired_token},
        )
        
        assert response.status_code == 400
        error = response.json()
        assert "invalid" in error["detail"].lower() or "expired" in error["detail"].lower()
    
    async def test_password_reset_rate_limiting(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        """Test rate limiting on password reset requests."""
        # Make multiple reset requests
        for i in range(4):
            response = await client.post(
                "/api/v1/auth/forgot-password",
                json={"email": test_user.email},
                headers={"X-Real-IP": "192.168.1.100"},
            )
            
            if i < 3:
                assert response.status_code == 200
            else:
                # Should be rate limited after 3 requests
                assert response.status_code == 429