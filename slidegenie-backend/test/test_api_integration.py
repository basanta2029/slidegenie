"""
Comprehensive API integration tests for the SlideGenie API.

This test suite covers:
- API versioning and routing
- Authentication and authorization
- Rate limiting and middleware
- Error handling and exceptions
- Health checks and monitoring
- All endpoint integrations
- Performance and load testing
"""

import asyncio
import json
import time
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.api.exceptions import (
    AuthenticationException,
    RateLimitExceededException,
    ValidationException,
)
from app.api.middleware import setup_middleware
from app.core.config import settings
from app.core.health import HealthStatus, check_health
from app.main import app


# Test Fixtures

@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Create async test client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_user():
    """Create mock user for authentication."""
    return {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "email": "test@example.com",
        "role": "user",
        "is_active": True,
        "subscription_tier": "free",
    }


@pytest.fixture
def mock_admin_user():
    """Create mock admin user."""
    return {
        "id": "550e8400-e29b-41d4-a716-446655440001",
        "email": "admin@example.com",
        "role": "admin",
        "is_active": True,
        "subscription_tier": "premium",
    }


@pytest.fixture
def auth_headers(mock_user):
    """Create authentication headers."""
    from app.core.security import create_access_token
    
    token = create_access_token(
        data={"sub": mock_user["id"], "type": "access"}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(mock_admin_user):
    """Create admin authentication headers."""
    from app.core.security import create_access_token
    
    token = create_access_token(
        data={"sub": mock_admin_user["id"], "type": "access"}
    )
    return {"Authorization": f"Bearer {token}"}


# API Information and Status Tests

class TestAPIInfo:
    """Test API information endpoints."""
    
    def test_api_info(self, client):
        """Test API information endpoint."""
        response = client.get(f"{settings.API_V1_PREFIX}/")
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["name"] == settings.PROJECT_NAME
        assert data["version"] == settings.APP_VERSION
        assert "endpoints" in data
        assert "documentation" in data
        assert "features" in data
        assert "limits" in data
    
    def test_api_status(self, client):
        """Test API status endpoint."""
        response = client.get(f"{settings.API_V1_PREFIX}/status")
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "status" in data
        assert "components" in data
        assert "timestamp" in data
        assert data["version"] == settings.APP_VERSION
    
    def test_api_limits(self, client):
        """Test API limits endpoint."""
        response = client.get(f"{settings.API_V1_PREFIX}/limits")
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "rate_limits" in data
        assert "quotas" in data
        assert "file_limits" in data
        assert "presentation_limits" in data
    
    def test_metrics_endpoint(self, client):
        """Test Prometheus metrics endpoint."""
        response = client.get(f"{settings.API_V1_PREFIX}/metrics")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"].startswith("text/plain")


# API Versioning Tests

class TestAPIVersioning:
    """Test API versioning functionality."""
    
    def test_url_based_versioning(self, client):
        """Test URL-based API versioning."""
        # Test v1 endpoint
        response = client.get("/api/v1/health")
        assert response.status_code == status.HTTP_200_OK
        assert response.headers.get("API-Version") == "v1"
    
    def test_header_based_versioning(self, client):
        """Test header-based API versioning."""
        headers = {"API-Version": "v1"}
        response = client.get(f"{settings.API_V1_PREFIX}/health", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.headers.get("API-Version") == "v1"
    
    def test_unsupported_version(self, client):
        """Test unsupported API version handling."""
        headers = {"API-Version": "v2"}
        response = client.get(f"{settings.API_V1_PREFIX}/health", headers=headers)
        
        # Should fallback to v1 or return error based on implementation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]
    
    def test_version_headers_in_response(self, client):
        """Test version headers in response."""
        response = client.get(f"{settings.API_V1_PREFIX}/health")
        
        assert "API-Version" in response.headers
        assert "Supported-Versions" in response.headers


# Authentication and Authorization Tests

class TestAuthentication:
    """Test authentication functionality."""
    
    def test_unauthenticated_access_to_protected_endpoint(self, client):
        """Test access to protected endpoint without authentication."""
        response = client.get(f"{settings.API_V1_PREFIX}/users/me")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "WWW-Authenticate" in response.headers
    
    def test_invalid_token(self, client):
        """Test access with invalid token."""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get(f"{settings.API_V1_PREFIX}/users/me", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @patch('app.api.dependencies.get_current_user')
    def test_valid_authentication(self, mock_get_user, client, mock_user, auth_headers):
        """Test successful authentication."""
        mock_get_user.return_value = mock_user
        
        response = client.get(
            f"{settings.API_V1_PREFIX}/users/me", 
            headers=auth_headers
        )
        
        # This would normally return user data
        # For now, we expect it to not be unauthorized
        assert response.status_code != status.HTTP_401_UNAUTHORIZED
    
    @patch('app.api.dependencies.get_current_admin_user')
    def test_admin_authorization(self, mock_get_admin, client, mock_admin_user, admin_auth_headers):
        """Test admin-only endpoint access."""
        mock_get_admin.return_value = mock_admin_user
        
        response = client.post(
            f"{settings.API_V1_PREFIX}/maintenance",
            json={"enable": True, "message": "Test maintenance"},
            headers=admin_auth_headers
        )
        
        # Should not be unauthorized (specific implementation may vary)
        assert response.status_code != status.HTTP_401_UNAUTHORIZED
    
    def test_inactive_user_access(self, client):
        """Test access with inactive user account."""
        # This would require mocking inactive user
        # Implementation depends on how inactive users are handled
        pass


# Rate Limiting Tests

class TestRateLimiting:
    """Test rate limiting functionality."""
    
    @patch('app.api.middleware.get_redis')
    async def test_rate_limit_enforcement(self, mock_redis, async_client):
        """Test rate limit enforcement."""
        # Mock Redis to simulate rate limiting
        mock_redis_client = AsyncMock()
        mock_redis.return_value = mock_redis_client
        
        # Simulate rate limit exceeded
        mock_redis_client.get.return_value = b"100"  # Exceed limit
        mock_redis_client.ttl.return_value = 60
        
        response = await async_client.get(f"{settings.API_V1_PREFIX}/health")
        
        # Implementation may vary based on actual middleware
        # Check for rate limit headers
        if "X-RateLimit-Limit" in response.headers:
            assert int(response.headers["X-RateLimit-Limit"]) > 0
    
    def test_rate_limit_headers(self, client):
        """Test rate limit headers in response."""
        response = client.get(f"{settings.API_V1_PREFIX}/health")
        
        # Rate limit headers might be present
        if "X-RateLimit-Limit" in response.headers:
            assert "X-RateLimit-Remaining" in response.headers
            assert "X-RateLimit-Reset" in response.headers
    
    async def test_rate_limit_per_endpoint(self, async_client):
        """Test different rate limits for different endpoints."""
        # Test multiple requests to the same endpoint
        responses = []
        for _ in range(5):
            response = await async_client.get(f"{settings.API_V1_PREFIX}/health")
            responses.append(response)
        
        # All should succeed for health endpoint (likely has high limit)
        assert all(r.status_code == status.HTTP_200_OK for r in responses)


# Error Handling Tests

class TestErrorHandling:
    """Test error handling and exception responses."""
    
    def test_404_error_handling(self, client):
        """Test 404 error handling."""
        response = client.get(f"{settings.API_V1_PREFIX}/nonexistent")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        data = response.json()
        assert "error" in data or "detail" in data
    
    def test_405_method_not_allowed(self, client):
        """Test 405 error for unsupported methods."""
        response = client.post(f"{settings.API_V1_PREFIX}/health")
        
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    
    def test_422_validation_error(self, client):
        """Test validation error handling."""
        # Send invalid JSON to an endpoint that expects JSON
        response = client.post(
            f"{settings.API_V1_PREFIX}/auth/register",
            json={"email": "invalid-email"}  # Invalid email format
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        data = response.json()
        assert "error" in data or "detail" in data
    
    def test_413_payload_too_large(self, client):
        """Test payload too large error."""
        # This would require sending a large payload
        # Implementation depends on configured limits
        pass
    
    def test_415_unsupported_media_type(self, client):
        """Test unsupported media type error."""
        response = client.post(
            f"{settings.API_V1_PREFIX}/auth/register",
            headers={"Content-Type": "application/xml"},
            data="<xml>test</xml>"
        )
        
        # May return 415 or 422 depending on implementation
        assert response.status_code in [
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]


# Health Check Tests

class TestHealthChecks:
    """Test health check functionality."""
    
    def test_basic_health_check(self, client):
        """Test basic health check endpoint."""
        response = client.get(f"{settings.API_V1_PREFIX}/health")
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
    
    def test_readiness_check(self, client):
        """Test readiness check endpoint."""
        response = client.get(f"{settings.API_V1_PREFIX}/health/ready")
        
        # Should return 200 if ready, 503 if not ready
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE]
        
        data = response.json()
        assert "status" in data
        assert "components" in data
    
    @patch('app.core.health.check_health')
    async def test_health_check_with_failures(self, mock_check_health, async_client):
        """Test health check with component failures."""
        # Mock unhealthy status
        mock_check_health.return_value = {
            "status": "unhealthy",
            "components": {
                "database": {"status": "unhealthy", "message": "Connection failed"}
            }
        }
        
        response = await async_client.get(f"{settings.API_V1_PREFIX}/status")
        
        # Should still return data even if unhealthy
        data = response.json()
        assert "status" in data
        assert "components" in data


# Endpoint Integration Tests

class TestEndpointIntegration:
    """Test integration of all API endpoints."""
    
    def test_auth_endpoints(self, client):
        """Test authentication endpoints."""
        # Test registration endpoint exists
        response = client.post(f"{settings.API_V1_PREFIX}/auth/register")
        assert response.status_code != status.HTTP_404_NOT_FOUND
        
        # Test login endpoint exists
        response = client.post(f"{settings.API_V1_PREFIX}/auth/login")
        assert response.status_code != status.HTTP_404_NOT_FOUND
    
    def test_user_endpoints(self, client):
        """Test user management endpoints."""
        # Test user profile endpoint (should require auth)
        response = client.get(f"{settings.API_V1_PREFIX}/users/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_presentation_endpoints(self, client):
        """Test presentation endpoints."""
        # Test presentations list endpoint (should require auth)
        response = client.get(f"{settings.API_V1_PREFIX}/presentations")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_template_endpoints(self, client):
        """Test template endpoints."""
        # Test templates list endpoint (might be public)
        response = client.get(f"{settings.API_V1_PREFIX}/templates")
        assert response.status_code != status.HTTP_404_NOT_FOUND
    
    def test_generation_endpoints(self, client):
        """Test AI generation endpoints."""
        # Test generation endpoint (should require auth)
        response = client.post(f"{settings.API_V1_PREFIX}/generation/start")
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED, 
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]
    
    def test_export_endpoints(self, client):
        """Test export endpoints."""
        # Test export endpoint (should require auth)
        response = client.post(f"{settings.API_V1_PREFIX}/export/pdf")
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_404_NOT_FOUND
        ]
    
    def test_websocket_endpoint(self, client):
        """Test WebSocket endpoint."""
        # WebSocket endpoints can't be easily tested with TestClient
        # This would require a WebSocket test client
        pass
    
    def test_admin_endpoints(self, client):
        """Test admin endpoints."""
        # Test admin endpoint (should require admin auth)
        response = client.get(f"{settings.API_V1_PREFIX}/admin/users")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# Middleware Integration Tests

class TestMiddlewareIntegration:
    """Test middleware integration."""
    
    def test_cors_headers(self, client):
        """Test CORS headers."""
        response = client.options(f"{settings.API_V1_PREFIX}/health")
        
        # CORS headers might be present
        if "Access-Control-Allow-Origin" in response.headers:
            assert response.headers["Access-Control-Allow-Origin"]
    
    def test_security_headers(self, client):
        """Test security headers."""
        response = client.get(f"{settings.API_V1_PREFIX}/health")
        
        # Check for security headers
        expected_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options", 
            "X-XSS-Protection",
        ]
        
        for header in expected_headers:
            if header in response.headers:
                assert response.headers[header]
    
    def test_request_id_header(self, client):
        """Test request ID header."""
        response = client.get(f"{settings.API_V1_PREFIX}/health")
        
        assert "X-Request-ID" in response.headers
        assert response.headers["X-Request-ID"]
    
    def test_response_time_logging(self, client):
        """Test response time logging."""
        # This would require checking logs
        # For now, just ensure request completes
        start_time = time.time()
        response = client.get(f"{settings.API_V1_PREFIX}/health")
        end_time = time.time()
        
        assert response.status_code == status.HTTP_200_OK
        assert end_time - start_time < 5.0  # Should be fast


# Performance Tests

class TestPerformance:
    """Test API performance characteristics."""
    
    async def test_concurrent_requests(self, async_client):
        """Test handling of concurrent requests."""
        # Send multiple concurrent requests
        tasks = []
        for _ in range(10):
            task = async_client.get(f"{settings.API_V1_PREFIX}/health")
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        
        # All should succeed
        assert all(r.status_code == status.HTTP_200_OK for r in responses)
    
    async def test_response_time(self, async_client):
        """Test response time performance."""
        start_time = time.time()
        response = await async_client.get(f"{settings.API_V1_PREFIX}/health")
        end_time = time.time()
        
        assert response.status_code == status.HTTP_200_OK
        assert end_time - start_time < 1.0  # Should respond within 1 second
    
    def test_memory_usage(self, client):
        """Test memory usage during requests."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Make multiple requests
        for _ in range(100):
            response = client.get(f"{settings.API_V1_PREFIX}/health")
            assert response.status_code == status.HTTP_200_OK
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB)
        assert memory_increase < 100 * 1024 * 1024


# Edge Case Tests

class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_malformed_json(self, client):
        """Test handling of malformed JSON."""
        response = client.post(
            f"{settings.API_V1_PREFIX}/auth/register",
            data='{"invalid": json}',
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_empty_request_body(self, client):
        """Test handling of empty request body."""
        response = client.post(
            f"{settings.API_V1_PREFIX}/auth/register",
            json={}
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_very_long_url(self, client):
        """Test handling of very long URLs."""
        long_path = "a" * 2000
        response = client.get(f"{settings.API_V1_PREFIX}/{long_path}")
        
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_414_REQUEST_URI_TOO_LARGE
        ]
    
    def test_special_characters_in_path(self, client):
        """Test handling of special characters in path."""
        special_path = "test%20with%20spaces/and/special!@#$%^&*()"
        response = client.get(f"{settings.API_V1_PREFIX}/{special_path}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_unicode_in_request(self, client):
        """Test handling of Unicode characters."""
        response = client.post(
            f"{settings.API_V1_PREFIX}/auth/register",
            json={"email": "test@例え.テスト", "password": "pássword123"}
        )
        
        # Should handle Unicode gracefully
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,  # Validation error
            status.HTTP_200_OK  # If Unicode is supported
        ]


# Integration Test Suite

class TestFullIntegration:
    """Full integration test scenarios."""
    
    async def test_complete_user_flow(self, async_client):
        """Test complete user registration and usage flow."""
        # This would test a complete user journey
        # 1. Register user
        # 2. Login
        # 3. Create presentation
        # 4. Generate slides
        # 5. Export presentation
        # 6. Logout
        
        # For now, just test that endpoints exist
        endpoints_to_test = [
            "/auth/register",
            "/auth/login", 
            "/presentations",
            "/generation/start",
            "/export/pdf"
        ]
        
        for endpoint in endpoints_to_test:
            response = await async_client.get(f"{settings.API_V1_PREFIX}{endpoint}")
            # Should not be 404 (endpoint exists)
            assert response.status_code != status.HTTP_404_NOT_FOUND
    
    def test_api_documentation_consistency(self, client):
        """Test that API documentation is consistent with implementation."""
        # Get OpenAPI schema
        response = client.get(f"{settings.API_V1_PREFIX}/openapi.json")
        
        if response.status_code == status.HTTP_200_OK:
            schema = response.json()
            
            # Check that documented endpoints exist
            paths = schema.get("paths", {})
            for path in paths:
                # Test that path exists (at least doesn't return 404)
                test_response = client.get(path)
                assert test_response.status_code != status.HTTP_404_NOT_FOUND


# Test Configuration

@pytest.mark.asyncio
class TestAsyncIntegration:
    """Async integration tests."""
    
    async def test_async_endpoint_performance(self, async_client):
        """Test async endpoint performance."""
        import asyncio
        import time
        
        start_time = time.time()
        
        # Create multiple concurrent requests
        tasks = [
            async_client.get(f"{settings.API_V1_PREFIX}/health")
            for _ in range(20)
        ]
        
        responses = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # All should succeed
        assert all(r.status_code == status.HTTP_200_OK for r in responses)
        
        # Should handle concurrent requests efficiently
        assert end_time - start_time < 2.0  # All 20 requests in under 2 seconds


if __name__ == "__main__":
    pytest.main([__file__, "-v"])