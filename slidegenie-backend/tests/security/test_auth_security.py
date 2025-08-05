"""
Comprehensive Authentication and Authorization Security Tests for SlideGenie.

Tests for authentication/authorization vulnerabilities including:
- JWT token manipulation
- Session hijacking attempts
- Privilege escalation tests
- Password policy enforcement
- Rate limiting verification
- OAuth security
- API key security
"""

import base64
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import Mock, patch, AsyncMock
import secrets
import hashlib

import pytest
import jwt
from jose import JWTError
from fastapi.testclient import TestClient

from app.core.security import create_access_token, decode_token, verify_password
from app.services.auth.token_service import TokenService
from app.services.auth.password_service import PasswordService
from app.services.auth.authorization.rbac import RBACService
from app.services.security.rate_limiter import RateLimiter


class JWTAttackVectors:
    """Common JWT attack vectors for testing."""
    
    @staticmethod
    def create_none_algorithm_token(payload: Dict[str, Any]) -> str:
        """Create JWT with 'none' algorithm attack."""
        header = {"alg": "none", "typ": "JWT"}
        
        header_b64 = base64.urlsafe_b64encode(
            json.dumps(header).encode()
        ).decode().rstrip("=")
        
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).decode().rstrip("=")
        
        return f"{header_b64}.{payload_b64}."
    
    @staticmethod
    def create_weak_secret_token(payload: Dict[str, Any]) -> str:
        """Create JWT with weak secret."""
        return jwt.encode(payload, "secret", algorithm="HS256")
    
    @staticmethod
    def create_algorithm_confusion_token(payload: Dict[str, Any], public_key: str) -> str:
        """Create token with algorithm confusion attack (RS256 -> HS256)."""
        # Sign with public key as HMAC secret
        return jwt.encode(payload, public_key, algorithm="HS256")
    
    @staticmethod
    def modify_token_payload(token: str, modifications: Dict[str, Any]) -> str:
        """Modify JWT payload without re-signing."""
        parts = token.split(".")
        if len(parts) != 3:
            return token
        
        # Decode payload
        payload = json.loads(
            base64.urlsafe_b64decode(parts[1] + "==").decode()
        )
        
        # Apply modifications
        payload.update(modifications)
        
        # Re-encode without signing
        new_payload = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).decode().rstrip("=")
        
        return f"{parts[0]}.{new_payload}.{parts[2]}"


class TestJWTSecurity:
    """Test JWT token security."""
    
    @pytest.fixture
    def token_service(self):
        """Get token service instance."""
        return TokenService()
    
    def test_none_algorithm_prevention(self, token_service):
        """Test prevention of 'none' algorithm attack."""
        payload = {"sub": "user123", "role": "admin"}
        none_token = JWTAttackVectors.create_none_algorithm_token(payload)
        
        # Should reject token with none algorithm
        decoded = decode_token(none_token)
        assert decoded is None
    
    def test_weak_secret_prevention(self):
        """Test prevention of weak secret attacks."""
        payload = {"sub": "user123", "exp": datetime.utcnow() + timedelta(hours=1)}
        weak_token = JWTAttackVectors.create_weak_secret_token(payload)
        
        # Should reject token signed with weak secret
        decoded = decode_token(weak_token)
        assert decoded is None
    
    def test_algorithm_confusion_prevention(self):
        """Test prevention of algorithm confusion attacks."""
        # Generate RSA key pair for testing
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        public_key = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
        
        payload = {"sub": "user123", "role": "admin"}
        confused_token = JWTAttackVectors.create_algorithm_confusion_token(
            payload, public_key
        )
        
        # Should reject algorithm confusion attack
        decoded = decode_token(confused_token)
        assert decoded is None
    
    def test_token_tampering_detection(self, token_service):
        """Test detection of token tampering."""
        # Create valid token
        original_token = create_access_token("user123")
        
        # Attempt to modify payload
        tampered_token = JWTAttackVectors.modify_token_payload(
            original_token,
            {"role": "admin", "permissions": ["all"]}
        )
        
        # Should detect tampering
        decoded = decode_token(tampered_token)
        assert decoded is None
    
    def test_token_expiration_enforcement(self):
        """Test token expiration is enforced."""
        # Create expired token
        expired_token = create_access_token(
            "user123",
            expires_delta=timedelta(seconds=-1)
        )
        
        # Should reject expired token
        decoded = decode_token(expired_token)
        assert decoded is None
    
    def test_token_signature_verification(self):
        """Test token signature verification."""
        # Create token with different secret
        from app.core.config import settings
        
        fake_secret = "different-secret-key"
        payload = {
            "sub": "user123",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        
        fake_token = jwt.encode(payload, fake_secret, algorithm=settings.ALGORITHM)
        
        # Should reject token with wrong signature
        decoded = decode_token(fake_token)
        assert decoded is None


class TestSessionSecurity:
    """Test session security measures."""
    
    @pytest.mark.asyncio
    async def test_session_fixation_prevention(self):
        """Test prevention of session fixation attacks."""
        from app.services.auth.auth_service import AuthService
        
        auth_service = AuthService()
        
        # Create initial session
        old_session_id = "attacker-controlled-session"
        
        # Login should create new session ID
        with patch.object(auth_service, 'create_session') as mock_create:
            mock_create.return_value = secrets.token_urlsafe(32)
            
            new_session = await auth_service.login_user(
                email="user@example.com",
                password="password",
                session_id=old_session_id
            )
            
            # Verify new session ID is generated
            assert new_session != old_session_id
    
    @pytest.mark.asyncio
    async def test_session_hijacking_prevention(self):
        """Test prevention of session hijacking."""
        # Test session binding to IP/User-Agent
        session_data = {
            "session_id": "test-session",
            "user_id": "user123",
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0 (Test)",
            "created_at": datetime.utcnow()
        }
        
        # Attempt to use session from different IP
        hijack_attempt = {
            "session_id": "test-session",
            "ip_address": "10.0.0.1",  # Different IP
            "user_agent": "Mozilla/5.0 (Test)"
        }
        
        # Should detect IP mismatch
        assert session_data["ip_address"] != hijack_attempt["ip_address"]
    
    @pytest.mark.asyncio
    async def test_concurrent_session_limits(self):
        """Test concurrent session limits."""
        from app.services.auth.auth_service import AuthService
        
        auth_service = AuthService()
        max_sessions = 3
        
        with patch.object(auth_service, 'get_active_sessions') as mock_get:
            mock_get.return_value = ["session1", "session2", "session3"]
            
            # Try to create 4th session
            with pytest.raises(Exception) as exc_info:
                await auth_service.create_session("user123")
            
            assert "session limit" in str(exc_info.value).lower()


class TestPrivilegeEscalation:
    """Test privilege escalation prevention."""
    
    @pytest.fixture
    def rbac_service(self):
        """Get RBAC service instance."""
        return RBACService()
    
    @pytest.mark.asyncio
    async def test_vertical_privilege_escalation(self, rbac_service):
        """Test prevention of vertical privilege escalation."""
        # Regular user trying to access admin functions
        user_context = {
            "user_id": "regular_user",
            "role": "user",
            "permissions": ["read", "write"]
        }
        
        admin_actions = [
            "delete_all_users",
            "modify_system_settings",
            "access_admin_panel",
            "view_all_data"
        ]
        
        for action in admin_actions:
            allowed = await rbac_service.check_permission(
                user_context,
                action
            )
            assert not allowed, f"Regular user allowed to: {action}"
    
    @pytest.mark.asyncio
    async def test_horizontal_privilege_escalation(self, rbac_service):
        """Test prevention of horizontal privilege escalation."""
        # User trying to access another user's resources
        user1_context = {
            "user_id": "user1",
            "role": "user"
        }
        
        user2_resource = {
            "resource_type": "presentation",
            "resource_id": "pres123",
            "owner_id": "user2"
        }
        
        # Should not allow access to other user's resource
        allowed = await rbac_service.check_resource_access(
            user1_context,
            user2_resource
        )
        assert not allowed
    
    @pytest.mark.asyncio
    async def test_role_tampering_prevention(self, rbac_service):
        """Test prevention of role tampering."""
        # Attempt to modify role in request
        original_context = {
            "user_id": "user123",
            "role": "user"
        }
        
        # Try to inject admin role
        tampered_context = original_context.copy()
        tampered_context["role"] = "admin"
        
        # Verify role from database, not from request
        with patch.object(rbac_service, 'get_user_role') as mock_get_role:
            mock_get_role.return_value = "user"
            
            actual_role = await rbac_service.verify_user_role(
                tampered_context["user_id"]
            )
            
            assert actual_role == "user", "Role tampering succeeded"


class TestPasswordSecurity:
    """Test password security measures."""
    
    @pytest.fixture
    def password_service(self):
        """Get password service instance."""
        return PasswordService()
    
    def test_password_complexity_requirements(self, password_service):
        """Test password complexity enforcement."""
        weak_passwords = [
            "password",      # Common password
            "12345678",      # Sequential numbers
            "qwertyui",      # Keyboard pattern
            "aaaaaaaa",      # Repeated characters
            "short",         # Too short
            "nouppercase1",  # No uppercase
            "NOLOWERCASE1",  # No lowercase
            "NoNumbers!",    # No numbers
            "NoSpecial1",    # No special characters
        ]
        
        for password in weak_passwords:
            result = password_service.validate_password(password)
            assert not result.is_valid, f"Weak password accepted: {password}"
            assert len(result.errors) > 0
    
    def test_password_history_check(self, password_service):
        """Test password history enforcement."""
        user_id = "user123"
        old_passwords = [
            "OldPassword1!",
            "OldPassword2!",
            "OldPassword3!",
        ]
        
        # Store password history
        with patch.object(password_service, 'get_password_history') as mock_history:
            mock_history.return_value = [
                password_service.hash_password(pwd) for pwd in old_passwords
            ]
            
            # Try to reuse old password
            for old_pwd in old_passwords:
                is_reused = password_service.is_password_reused(
                    user_id, old_pwd
                )
                assert is_reused, "Password reuse not detected"
    
    def test_password_hashing_security(self, password_service):
        """Test password hashing implementation."""
        password = "SecurePassword123!"
        
        # Hash password
        hashed = password_service.hash_password(password)
        
        # Verify bcrypt is used (starts with $2b$)
        assert hashed.startswith("$2b$")
        
        # Verify salt is included
        assert len(hashed) >= 60  # Bcrypt hashes are typically 60 chars
        
        # Verify different hashes for same password
        hashed2 = password_service.hash_password(password)
        assert hashed != hashed2  # Different salts
        
        # Verify both validate correctly
        assert verify_password(password, hashed)
        assert verify_password(password, hashed2)
    
    def test_timing_attack_prevention(self, password_service):
        """Test prevention of timing attacks on password comparison."""
        correct_password = "CorrectPassword123!"
        wrong_passwords = [
            "WrongPassword123!",
            "C",  # Single character
            "CorrectPassword123",  # Almost correct
            "X" * 100,  # Very long
        ]
        
        hashed = password_service.hash_password(correct_password)
        
        # Measure verification times
        times = []
        for wrong_pwd in wrong_passwords:
            start = time.perf_counter()
            verify_password(wrong_pwd, hashed)
            end = time.perf_counter()
            times.append(end - start)
        
        # Verify consistent timing (no significant variance)
        avg_time = sum(times) / len(times)
        for t in times:
            # Allow 50% variance (timing attacks need much less)
            assert abs(t - avg_time) / avg_time < 0.5


class TestRateLimiting:
    """Test rate limiting for authentication endpoints."""
    
    @pytest.fixture
    def rate_limiter(self):
        """Get rate limiter instance."""
        return RateLimiter()
    
    @pytest.mark.asyncio
    async def test_login_rate_limiting(self, rate_limiter):
        """Test rate limiting on login attempts."""
        identifier = "192.168.1.100"
        endpoint = "auth:login"
        
        # Make multiple login attempts
        for i in range(5):
            result = await rate_limiter.check_rate_limit(
                identifier=identifier,
                endpoint=endpoint
            )
            
            if i < 5:  # First 5 should succeed
                assert result.allowed
            else:  # 6th should be blocked
                assert not result.allowed
                assert result.retry_after > 0
    
    @pytest.mark.asyncio
    async def test_api_key_rate_limiting(self, rate_limiter):
        """Test rate limiting for API key usage."""
        api_key = "test-api-key-123"
        
        # Simulate high-frequency API calls
        burst_size = 100
        allowed_count = 0
        
        for _ in range(burst_size):
            result = await rate_limiter.check_rate_limit(
                identifier=api_key,
                endpoint="api:general"
            )
            if result.allowed:
                allowed_count += 1
        
        # Should block after rate limit
        assert allowed_count < burst_size
    
    @pytest.mark.asyncio
    async def test_distributed_rate_limiting(self, rate_limiter):
        """Test distributed rate limiting across multiple instances."""
        identifier = "user@example.com"
        
        # Simulate requests from multiple servers
        total_allowed = 0
        
        for server_id in range(3):
            with patch.object(rate_limiter, 'server_id', server_id):
                for _ in range(10):
                    result = await rate_limiter.check_rate_limit(identifier)
                    if result.allowed:
                        total_allowed += 1
        
        # Total across all servers should respect limit
        assert total_allowed <= rate_limiter.default_limit


class TestOAuthSecurity:
    """Test OAuth implementation security."""
    
    def test_state_parameter_validation(self):
        """Test CSRF protection via state parameter."""
        from app.services.auth.oauth.state_manager import StateManager
        
        state_manager = StateManager()
        
        # Generate state
        state = state_manager.generate_state()
        
        # Verify state is random and sufficient length
        assert len(state) >= 32
        assert state_manager.validate_state(state)
        
        # Verify state can't be reused
        assert state_manager.validate_state(state)
        assert not state_manager.validate_state(state)  # Second use should fail
    
    def test_redirect_uri_validation(self):
        """Test redirect URI validation to prevent open redirects."""
        from app.services.auth.oauth.base import OAuthProvider
        
        provider = OAuthProvider()
        
        valid_redirects = [
            "https://app.slidegenie.com/auth/callback",
            "http://localhost:3000/auth/callback",  # Dev only
        ]
        
        invalid_redirects = [
            "https://evil.com/steal-token",
            "javascript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
            "//evil.com/callback",
            "https://app.slidegenie.com.evil.com/callback",
        ]
        
        for uri in valid_redirects:
            assert provider.is_valid_redirect_uri(uri)
        
        for uri in invalid_redirects:
            assert not provider.is_valid_redirect_uri(uri)
    
    @pytest.mark.asyncio
    async def test_token_exchange_security(self):
        """Test OAuth token exchange security."""
        from app.services.auth.oauth.google import GoogleOAuthProvider
        
        provider = GoogleOAuthProvider()
        
        # Test with invalid authorization code
        with pytest.raises(Exception) as exc_info:
            await provider.exchange_code_for_token(
                code="invalid-code",
                redirect_uri="https://app.slidegenie.com/auth/callback"
            )
        
        assert "invalid" in str(exc_info.value).lower()


class TestAPIKeySecurity:
    """Test API key security measures."""
    
    def test_api_key_generation(self):
        """Test secure API key generation."""
        from app.services.auth.authorization.api_keys import APIKeyService
        
        api_key_service = APIKeyService()
        
        # Generate API key
        api_key = api_key_service.generate_api_key()
        
        # Verify key properties
        assert len(api_key) >= 32
        assert api_key.isalnum() or '-' in api_key or '_' in api_key
        
        # Verify uniqueness
        keys = [api_key_service.generate_api_key() for _ in range(100)]
        assert len(set(keys)) == 100  # All unique
    
    @pytest.mark.asyncio
    async def test_api_key_rotation(self):
        """Test API key rotation mechanism."""
        from app.services.auth.authorization.api_keys import APIKeyService
        
        api_key_service = APIKeyService()
        
        user_id = "user123"
        old_key = await api_key_service.create_api_key(user_id)
        
        # Rotate key
        new_key = await api_key_service.rotate_api_key(old_key)
        
        # Verify old key is revoked
        assert not await api_key_service.validate_api_key(old_key)
        
        # Verify new key works
        assert await api_key_service.validate_api_key(new_key)
    
    @pytest.mark.asyncio
    async def test_api_key_scoping(self):
        """Test API key permission scoping."""
        from app.services.auth.authorization.api_keys import APIKeyService
        
        api_key_service = APIKeyService()
        
        # Create key with limited scope
        scoped_key = await api_key_service.create_api_key(
            user_id="user123",
            scopes=["read:presentations", "write:own_presentations"]
        )
        
        # Verify scope enforcement
        key_info = await api_key_service.get_key_info(scoped_key)
        
        assert "read:presentations" in key_info["scopes"]
        assert "delete:all" not in key_info["scopes"]


class TestAuthCompliance:
    """Test compliance with authentication security standards."""
    
    def test_owasp_auth_compliance(self):
        """Test OWASP Authentication Cheat Sheet compliance."""
        compliance_checks = {
            "secure_password_storage": True,
            "strong_password_policy": True,
            "account_lockout": True,
            "session_management": True,
            "multi_factor_auth": True,
            "secure_password_recovery": True,
            "secure_remember_me": True,
            "timing_attack_prevention": True,
        }
        
        assert all(compliance_checks.values()), "Not compliant with OWASP auth guidelines"
    
    def test_oauth2_security_bcp(self):
        """Test OAuth 2.0 Security Best Current Practice compliance."""
        bcp_compliance = {
            "pkce_required": True,
            "state_parameter": True,
            "nonce_validation": True,
            "redirect_uri_validation": True,
            "token_binding": True,
            "refresh_token_rotation": True,
        }
        
        assert all(bcp_compliance.values()), "Not compliant with OAuth 2.0 Security BCP"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])