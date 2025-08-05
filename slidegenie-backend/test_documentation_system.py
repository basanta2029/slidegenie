#!/usr/bin/env python3
"""
Test suite for SlideGenie API documentation system.

This module tests all components of the comprehensive OpenAPI documentation
system including generation, middleware, versioning, and examples.
"""
import json
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from app.core.config import settings
from app.docs.openapi_generator import OpenAPIGenerator, generate_api_documentation
from app.docs.api_examples import APIExamples
from app.docs.openapi_schemas import ErrorResponse, PaginationMeta
from app.core.api_versioning import APIVersionManager, VersionNegotiator
from app.middleware.api_documentation import APIDocumentationMiddleware
from setup_documentation import setup_comprehensive_documentation


class TestOpenAPIGenerator:
    """Test OpenAPI schema generation."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.app = FastAPI(title="Test API", version="1.0.0")
        self.generator = OpenAPIGenerator(self.app)
    
    def test_generate_openapi_schema(self):
        """Test OpenAPI schema generation."""
        schema = self.generator.generate_openapi_schema()
        
        assert "openapi" in schema
        assert schema["openapi"] == "3.0.2"
        assert "info" in schema
        assert schema["info"]["title"] == "Test API API"
        assert "components" in schema
        assert "securitySchemes" in schema["components"]
    
    def test_security_schemes(self):
        """Test security scheme definitions."""
        schema = self.generator.generate_openapi_schema()
        security_schemes = schema["components"]["securitySchemes"]
        
        assert "BearerAuth" in security_schemes
        assert "ApiKeyAuth" in security_schemes
        assert "OAuth2" in security_schemes
        
        bearer_auth = security_schemes["BearerAuth"]
        assert bearer_auth["type"] == "http"
        assert bearer_auth["scheme"] == "bearer"
        assert bearer_auth["bearerFormat"] == "JWT"
    
    def test_error_responses(self):
        """Test error response schemas."""
        schema = self.generator.generate_openapi_schema()
        schemas = schema["components"]["schemas"]
        
        assert "ErrorResponse" in schemas
        assert "ValidationError" in schemas
        assert "RateLimitError" in schemas
        
        error_schema = schemas["ErrorResponse"]
        assert "properties" in error_schema
        assert "error" in error_schema["properties"]
    
    def test_webhook_documentation(self):
        """Test webhook documentation generation."""
        schema = self.generator.generate_openapi_schema()
        
        assert "webhooks" in schema
        assert "generation-complete" in schema["webhooks"]
        assert "export-ready" in schema["webhooks"]
    
    def test_postman_collection_generation(self):
        """Test Postman collection generation."""
        collection = self.generator.generate_postman_collection()
        
        assert "info" in collection
        assert "item" in collection
        assert collection["info"]["name"] == "Test API API"
        assert "variable" in collection
        
        # Check for base_url variable
        variables = {var["key"]: var["value"] for var in collection["variable"]}
        assert "base_url" in variables
        assert "access_token" in variables


class TestAPIExamples:
    """Test API examples generation."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.examples = APIExamples()
    
    def test_auth_register_example(self):
        """Test authentication registration example."""
        example = self.examples.get_auth_register_example()
        
        assert "request" in example
        assert "response" in example
        
        request = example["request"]
        assert "email" in request
        assert "password" in request
        assert "first_name" in request
        assert request["email"].endswith(".edu")
        
        response = example["response"]
        assert "data" in response
        assert "user" in response["data"]
        assert "tokens" in response["data"]
    
    def test_presentations_list_example(self):
        """Test presentations list example."""
        example = self.examples.get_presentations_list_example()
        
        assert "response" in example
        response = example["response"]
        
        assert "data" in response
        assert "meta" in response
        assert isinstance(response["data"], list)
        
        if response["data"]:
            presentation = response["data"][0]
            assert "id" in presentation
            assert "title" in presentation
            assert "status" in presentation
    
    def test_error_examples(self):
        """Test error response examples."""
        error_example = self.examples.get_error_example("UNAUTHORIZED")
        
        assert "error" in error_example
        error = error_example["error"]
        
        assert "code" in error
        assert "message" in error
        assert error["code"] == "UNAUTHORIZED"
        
        validation_error = self.examples.get_validation_error_example()
        assert "error" in validation_error
        assert "field_errors" in validation_error["error"]["details"]
    
    def test_websocket_examples(self):
        """Test WebSocket message examples."""
        progress_example = self.examples.get_websocket_progress_example()
        
        assert "type" in progress_example
        assert "data" in progress_example
        assert progress_example["type"] == "progress"
        
        data = progress_example["data"]
        assert "job_id" in data
        assert "progress" in data
        assert "stage" in data
        assert 0 <= data["progress"] <= 100
    
    def test_webhook_examples(self):
        """Test webhook examples."""
        webhook_example = self.examples.get_webhook_example("generation.complete")
        
        assert "event" in webhook_example
        assert "data" in webhook_example
        assert "timestamp" in webhook_example
        assert "signature" in webhook_example
        assert webhook_example["event"] == "generation.complete"


class TestAPIVersioning:
    """Test API versioning system."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.version_manager = APIVersionManager()
    
    def test_version_manager_initialization(self):
        """Test version manager initialization."""
        assert "1.0.0" in self.version_manager.versions
        assert self.version_manager.default_version == "1.0.0"
        assert self.version_manager.is_version_supported("1.0.0")
    
    def test_version_parsing(self):
        """Test version string parsing."""
        parsed = self.version_manager._parse_version("1.2.3")
        assert parsed == (1, 2, 3)
        
        parsed = self.version_manager._parse_version("2.0.0-beta.1")
        assert parsed == (2, 0, 0)
    
    def test_version_negotiation(self):
        """Test version negotiation."""
        negotiator = VersionNegotiator(self.version_manager)
        
        # Test explicit version request
        version, warnings = negotiator.negotiate_version(requested_version="1.0.0")
        assert version == "1.0.0"
        assert isinstance(warnings, list)
        
        # Test Accept header parsing
        version, _ = negotiator.negotiate_version(
            accept_header="application/vnd.slidegenie.v1+json"
        )
        assert version == "1.0.0"
    
    def test_version_deprecation(self):
        """Test version deprecation."""
        from datetime import datetime, timedelta
        
        # Add a test version
        from app.core.api_versioning import APIVersion, APIVersionStatus, VersionCompatibility
        test_version = APIVersion(
            version="0.9.0",
            status=APIVersionStatus.STABLE,
            release_date=datetime(2023, 1, 1),
            compatibility=VersionCompatibility.BACKWARD_COMPATIBLE
        )
        self.version_manager.add_version(test_version)
        
        # Deprecate it
        sunset_date = datetime.utcnow() + timedelta(days=90)
        self.version_manager.deprecate_version("0.9.0", sunset_date=sunset_date)
        
        assert self.version_manager.is_version_deprecated("0.9.0")
        assert not self.version_manager.is_version_supported("0.9.0")


class TestDocumentationMiddleware:
    """Test documentation middleware."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.app = FastAPI(title="Test API", version="1.0.0")
        self.middleware = APIDocumentationMiddleware(self.app, enable_analytics=True)
        self.client = TestClient(self.app)
    
    def test_documentation_headers(self):
        """Test documentation headers addition."""
        @self.app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        response = self.client.get("/test")
        
        assert "X-API-Version" in response.headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
    
    def test_client_type_extraction(self):
        """Test client type extraction from User-Agent."""
        test_cases = [
            ("PostmanRuntime/7.29.0", "Postman"),
            ("curl/7.68.0", "cURL"),
            ("python-requests/2.28.0", "Python"),
            ("Mozilla/5.0 Node.js/16.0.0", "JavaScript/Node.js"),
            ("SwaggerUI/4.15.5", "Swagger UI"),
            ("SlideGenie-Python-SDK/1.0.0", "SlideGenie SDK"),
            ("Unknown-Client/1.0.0", "Other")
        ]
        
        for user_agent, expected_type in test_cases:
            client_type = self.middleware._extract_client_type(user_agent)
            assert client_type == expected_type


class TestSchemaValidation:
    """Test OpenAPI schema validation."""
    
    def test_error_response_schema(self):
        """Test error response schema validation."""
        from pydantic import ValidationError as PydanticValidationError
        
        # Valid error response
        valid_error = {
            "error": {
                "code": "TEST_ERROR",
                "message": "Test error message"
            }
        }
        
        error_response = ErrorResponse(**valid_error)
        assert error_response.error.code == "TEST_ERROR"
        assert error_response.error.message == "Test error message"
        
        # Invalid error response (missing required fields)
        with pytest.raises(PydanticValidationError):
            ErrorResponse(**{"error": {"code": "TEST_ERROR"}})  # Missing message
    
    def test_pagination_meta_schema(self):
        """Test pagination metadata schema validation."""
        from pydantic import ValidationError as PydanticValidationError
        
        # Valid pagination
        valid_pagination = {
            "page": 1,
            "per_page": 20,
            "total": 100,
            "pages": 5,
            "has_next": True,
            "has_prev": False,
            "next_page": 2,
            "prev_page": None
        }
        
        pagination = PaginationMeta(**valid_pagination)
        assert pagination.page == 1
        assert pagination.total == 100
        assert pagination.has_next is True
        
        # Invalid pagination (negative page)
        with pytest.raises(PydanticValidationError):
            PaginationMeta(**{**valid_pagination, "page": 0})


class TestIntegration:
    """Test full integration."""
    
    def setup_method(self):
        """Setup integration test fixtures."""
        self.app = FastAPI(title="Test API", version="1.0.0")
        self.app = setup_comprehensive_documentation(self.app)
        self.client = TestClient(self.app)
    
    def test_openapi_json_endpoint(self):
        """Test OpenAPI JSON endpoint."""
        response = self.client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "components" in schema
        assert "securitySchemes" in schema["components"]
    
    def test_documentation_endpoints(self):
        """Test documentation endpoints."""
        endpoints = [
            "/docs",
            "/redoc",
            "/api-info",
            "/health-detailed"
        ]
        
        for endpoint in endpoints:
            response = self.client.get(endpoint)
            assert response.status_code == 200, f"Failed for endpoint: {endpoint}"
    
    def test_version_info_endpoints(self):
        """Test version information endpoints."""
        # List all versions
        response = self.client.get("/api/v1/versions")
        assert response.status_code == 200
        
        data = response.json()
        assert "versions" in data
        assert "default_version" in data
        assert "supported_versions" in data
        
        # Get specific version
        response = self.client.get("/api/v1/versions/1.0.0")
        assert response.status_code == 200
        
        version_data = response.json()
        assert version_data["version"] == "1.0.0"
        assert "status" in version_data
        assert "compatibility" in version_data
    
    def test_static_file_generation(self):
        """Test static documentation file generation."""
        from setup_documentation import generate_static_documentation
        import os
        from pathlib import Path
        
        # Generate static files
        generate_static_documentation()
        
        # Check if files were created
        output_dir = Path("generated_docs")
        assert output_dir.exists()
        assert (output_dir / "openapi.json").exists()
        assert (output_dir / "postman_collection.json").exists()
        assert (output_dir / "sdk_examples.md").exists()
        
        # Verify OpenAPI JSON content
        with open(output_dir / "openapi.json") as f:
            openapi_data = json.load(f)
            assert "openapi" in openapi_data
            assert "info" in openapi_data
        
        # Cleanup
        import shutil
        if output_dir.exists():
            shutil.rmtree(output_dir)


class TestErrorHandling:
    """Test error handling in documentation system."""
    
    def test_invalid_version_request(self):
        """Test handling of invalid version requests."""
        app = FastAPI(title="Test API", version="1.0.0")
        app = setup_comprehensive_documentation(app)
        client = TestClient(app)
        
        # Test non-existent version
        response = client.get("/api/v1/versions/99.99.99")
        assert response.status_code == 404
        
        error_data = response.json()
        assert "detail" in error_data
        assert "not found" in error_data["detail"].lower()
    
    def test_malformed_accept_header(self):
        """Test handling of malformed Accept headers."""
        from app.core.api_versioning import VersionNegotiator, APIVersionManager
        
        negotiator = VersionNegotiator(APIVersionManager())
        
        # Test malformed Accept header
        version, warnings = negotiator.negotiate_version(
            accept_header="invalid-accept-header"
        )
        
        # Should fall back to latest version
        assert version is not None
        assert isinstance(warnings, list)


# Performance Tests
class TestPerformance:
    """Test performance of documentation system."""
    
    def test_openapi_generation_performance(self):
        """Test OpenAPI generation performance."""
        import time
        
        app = FastAPI(title="Test API", version="1.0.0")
        generator = OpenAPIGenerator(app)
        
        start_time = time.time()
        schema = generator.generate_openapi_schema()
        generation_time = time.time() - start_time
        
        # Should generate schema in reasonable time
        assert generation_time < 1.0  # Less than 1 second
        assert schema is not None
        assert "openapi" in schema
    
    def test_middleware_overhead(self):
        """Test middleware performance overhead."""
        import time
        
        app = FastAPI(title="Test API", version="1.0.0")
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        # Test without middleware
        client_without = TestClient(app)
        start_time = time.time()
        for _ in range(100):
            response = client_without.get("/test")
            assert response.status_code == 200
        time_without = time.time() - start_time
        
        # Add middleware
        app = setup_comprehensive_documentation(app)
        client_with = TestClient(app)
        
        start_time = time.time()
        for _ in range(100):
            response = client_with.get("/test")
            assert response.status_code == 200
        time_with = time.time() - start_time
        
        # Middleware should not add significant overhead
        overhead_ratio = time_with / time_without
        assert overhead_ratio < 2.0  # Less than 2x overhead


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
    print("\n" + "="*50)
    print("SlideGenie API Documentation System Tests Complete")
    print("="*50)
    print("\nTo run individual test classes:")
    print("pytest test_documentation_system.py::TestOpenAPIGenerator -v")
    print("pytest test_documentation_system.py::TestAPIExamples -v") 
    print("pytest test_documentation_system.py::TestAPIVersioning -v")
    print("pytest test_documentation_system.py::TestIntegration -v")
    print("\nTo run with coverage:")
    print("pytest test_documentation_system.py --cov=app.docs --cov=app.core.api_versioning --cov=app.middleware.api_documentation")