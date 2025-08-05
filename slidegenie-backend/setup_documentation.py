#!/usr/bin/env python3
"""
Setup script for SlideGenie API documentation.

This script demonstrates how to integrate the comprehensive OpenAPI documentation
system into your FastAPI application.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.api_versioning import get_version_info_routes, version_deprecation_middleware
from app.middleware.api_documentation import setup_documentation_middleware
from app.docs import generate_api_documentation


def setup_comprehensive_documentation(app: FastAPI) -> FastAPI:
    """
    Setup comprehensive API documentation for SlideGenie.
    
    This function configures:
    - Enhanced OpenAPI schema generation
    - Interactive documentation with custom UI
    - API versioning and deprecation management
    - Rate limiting documentation
    - WebSocket API documentation
    - SDK integration examples
    - Postman collection generation
    - Analytics dashboard
    
    Args:
        app: FastAPI application instance
        
    Returns:
        Enhanced FastAPI application with documentation
    """
    
    # 1. Setup documentation middleware (must be added early)
    setup_documentation_middleware(
        app, 
        enable_analytics=not settings.is_production  # Enable analytics in dev/staging
    )
    
    # 2. Add version management routes
    version_router = get_version_info_routes()
    app.include_router(version_router, prefix="/api/v1", tags=["version-info"])
    
    # 3. Add version deprecation middleware
    app.middleware("http")(version_deprecation_middleware)
    
    # 4. Update OpenAPI configuration
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        
        # Generate enhanced OpenAPI schema
        documentation = generate_api_documentation(app)
        app.openapi_schema = documentation["openapi_schema"]
        return app.openapi_schema
    
    app.openapi = custom_openapi
    
    # 5. Add CORS for documentation resources
    if not settings.is_production:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Allow all origins for dev docs
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    # 6. Add custom documentation routes
    @app.get("/api-info", tags=["documentation"])
    async def get_api_info():
        """
        Get comprehensive API information and available resources.
        
        Returns:
            API metadata, available endpoints, and documentation links
        """
        return {
            "api_name": settings.PROJECT_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "documentation": {
                "interactive_docs": f"{settings.API_BASE_URL}/docs",
                "redoc": f"{settings.API_BASE_URL}/redoc",
                "openapi_json": f"{settings.API_BASE_URL}/openapi.json",
                "openapi_yaml": f"{settings.API_BASE_URL}/docs/openapi.yaml",
                "postman_collection": f"{settings.API_BASE_URL}/docs/postman.json",
                "sdk_examples": f"{settings.API_BASE_URL}/docs/sdk",
                "analytics": f"{settings.API_BASE_URL}/docs/analytics" if not settings.is_production else None
            },
            "features": [
                "AI-powered slide generation",
                "Multiple export formats (PPTX, PDF, Beamer, Google Slides)",
                "Real-time collaboration",
                "Academic email validation", 
                "OAuth integration",
                "WebSocket support",
                "Rate limiting",
                "Comprehensive error handling"
            ],
            "rate_limits": {
                "authentication": "10 requests per minute",
                "file_upload": "5 requests per hour", 
                "generation": "20 requests per hour (free tier)",
                "general_api": "1000 requests per hour"
            },
            "supported_formats": {
                "input": ["PDF", "DOCX", "LaTeX", "TXT", "MD"],
                "output": ["PPTX", "PDF", "LaTeX Beamer", "Google Slides"]
            }
        }
    
    # 7. Add health check with documentation links
    @app.get("/health-detailed", tags=["health"])
    async def detailed_health_check():
        """
        Detailed health check including documentation service status.
        
        Returns:
            Comprehensive health information
        """
        return {
            "status": "healthy",
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "timestamp": "2024-01-01T00:00:00Z",  # Would be actual timestamp
            "services": {
                "api": "healthy",
                "database": "healthy", 
                "redis": "healthy",
                "ai_services": "healthy",
                "documentation": "healthy"
            },
            "documentation_endpoints": {
                "swagger_ui": "/docs",
                "redoc": "/redoc", 
                "openapi_spec": "/openapi.json",
                "sdk_examples": "/docs/sdk",
                "postman_collection": "/docs/postman.json"
            }
        }
    
    return app


def generate_static_documentation():
    """
    Generate static documentation files for deployment.
    
    This function creates static versions of the documentation
    that can be served by a CDN or static file server.
    """
    import json
    import os
    from pathlib import Path
    
    # Create a temporary FastAPI app for documentation generation
    temp_app = FastAPI(title=settings.PROJECT_NAME, version=settings.APP_VERSION)
    
    # Generate documentation
    documentation = generate_api_documentation(temp_app)
    
    # Create output directory
    output_dir = Path("generated_docs")
    output_dir.mkdir(exist_ok=True)
    
    # Save OpenAPI JSON
    with open(output_dir / "openapi.json", "w") as f:
        json.dump(documentation["openapi_schema"], f, indent=2)
    
    # Save Postman collection
    with open(output_dir / "postman_collection.json", "w") as f:
        json.dump(documentation["postman_collection"], f, indent=2)
    
    # Generate OpenAPI YAML
    try:
        import yaml
        with open(output_dir / "openapi.yaml", "w") as f:
            yaml.dump(documentation["openapi_schema"], f, default_flow_style=False)
    except ImportError:
        print("PyYAML not installed, skipping YAML generation")
    
    # Generate SDK examples as markdown
    sdk_examples = generate_sdk_examples_markdown()
    with open(output_dir / "sdk_examples.md", "w") as f:
        f.write(sdk_examples)
    
    print(f"Documentation generated in {output_dir.absolute()}")
    print(f"- OpenAPI JSON: {output_dir / 'openapi.json'}")
    print(f"- Postman Collection: {output_dir / 'postman_collection.json'}")
    print(f"- OpenAPI YAML: {output_dir / 'openapi.yaml'}")
    print(f"- SDK Examples: {output_dir / 'sdk_examples.md'}")


def generate_sdk_examples_markdown() -> str:
    """Generate SDK examples in Markdown format."""
    return f"""
# SlideGenie API SDK Examples

## Python SDK

### Installation
```bash
pip install slidegenie-python
```

### Quick Start
```python
from slidegenie import SlideGenieClient

# Initialize client
client = SlideGenieClient(
    api_key="your-api-key",
    base_url="{settings.API_BASE_URL}"
)

# Upload document
with open("research_paper.pdf", "rb") as f:
    document = client.documents.upload(f, filename="research_paper.pdf")

# Generate presentation
presentation = client.presentations.create(
    title="AI Research Presentation",
    template_id="academic-template"
)

# Generate slides from document
job = client.generation.create(
    source_type="document",
    source_id=document.id,
    presentation_id=presentation.id,
    options={{
        "max_slides": 15,
        "include_references": True,
        "citation_format": "APA"
    }}
)

# Wait for completion
result = client.generation.wait_for_completion(job.id)
print(f"Generated {{result.slides_count}} slides!")
```

## JavaScript/Node.js SDK

### Installation
```bash
npm install @slidegenie/js-sdk
```

### Quick Start
```javascript
import {{ SlideGenieClient }} from '@slidegenie/js-sdk';

const client = new SlideGenieClient({{
    apiKey: 'your-api-key',
    baseUrl: '{settings.API_BASE_URL}'
}});

// Upload and process document
const document = await client.documents.upload(file);

// Generate presentation
const presentation = await client.presentations.create({{
    title: 'My Presentation',
    templateId: 'conference-template'
}});

// Generate slides
const job = await client.generation.create({{
    sourceType: 'document',
    sourceId: document.id,
    presentationId: presentation.id
}});

// Monitor progress
client.generation.onProgress(job.id, (progress) => {{
    console.log(`Progress: ${{progress.progress}}%`);
}});

const result = await client.generation.waitForCompletion(job.id);
```

## cURL Examples

### Authentication
```bash
curl -X POST "{settings.API_BASE_URL}/api/v1/auth/login" \\
  -H "Content-Type: application/json" \\
  -d '{{"email": "user@university.edu", "password": "password"}}'
```

### Upload Document
```bash
curl -X POST "{settings.API_BASE_URL}/api/v1/documents/upload" \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -F "file=@paper.pdf"
```

### Generate Slides
```bash
curl -X POST "{settings.API_BASE_URL}/api/v1/generation/create" \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{{"source_type": "document", "source_id": "doc-id"}}'
```
"""


if __name__ == "__main__":
    # Example usage
    print("Setting up SlideGenie API documentation...")
    
    # This would be used in your main.py file:
    # app = FastAPI(...)
    # app = setup_comprehensive_documentation(app)
    
    # Generate static documentation
    generate_static_documentation()
    
    print("Documentation setup complete!")
    print(f"Visit http://localhost:8000/docs for interactive documentation")
    print(f"Visit http://localhost:8000/redoc for ReDoc documentation")
    print(f"Visit http://localhost:8000/docs/sdk for SDK examples")
    print(f"Visit http://localhost:8000/docs/analytics for API analytics")