"""
API documentation middleware for SlideGenie.

This middleware enhances the API with comprehensive documentation features:
- Dynamic OpenAPI schema generation
- Interactive documentation with custom themes
- API usage analytics and monitoring
- Rate limiting documentation
- Client SDK integration examples
"""
import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from fastapi import FastAPI, Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles

from app.core.config import settings
from app.core.logging import get_logger
from app.docs.openapi_generator import generate_api_documentation
from app.docs.api_examples import APIExamples

logger = get_logger(__name__)


class APIDocumentationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for enhanced API documentation and monitoring.
    """

    def __init__(self, app: FastAPI, enable_analytics: bool = True):
        super().__init__(app)
        self.app = app
        self.enable_analytics = enable_analytics
        self.examples = APIExamples()
        
        # Track API usage for documentation analytics
        self.endpoint_stats = {}
        self.client_stats = {}
        
        # Initialize documentation routes
        self._setup_documentation_routes()

    async def dispatch(self, request: Request, call_next):
        """Process request and add documentation enhancements."""
        start_time = time.time()
        
        # Handle documentation-specific routes
        if request.url.path.startswith("/docs/") or request.url.path in ["/docs", "/redoc", "/openapi.json"]:
            return await self._handle_documentation_request(request, call_next)
        
        # Process regular API requests
        response = await call_next(request)
        
        # Add documentation headers
        self._add_documentation_headers(request, response)
        
        # Track API usage for analytics
        if self.enable_analytics:
            processing_time = time.time() - start_time
            await self._track_api_usage(request, response, processing_time)
        
        return response

    async def _handle_documentation_request(self, request: Request, call_next):
        """Handle documentation-specific requests."""
        path = request.url.path
        
        # Custom OpenAPI JSON with enhancements
        if path == "/openapi.json" or path.endswith("/openapi.json"):
            return await self._serve_enhanced_openapi_json()
        
        # Custom Swagger UI
        if path == "/docs" or path == "/docs/":
            return await self._serve_custom_swagger_ui(request)
        
        # Custom ReDoc
        if path == "/redoc" or path == "/redoc/":
            return await self._serve_custom_redoc(request)
        
        # API analytics dashboard
        if path == "/docs/analytics":
            return await self._serve_analytics_dashboard(request)
        
        # SDK examples
        if path == "/docs/sdk":
            return await self._serve_sdk_examples(request)
        
        # Postman collection
        if path == "/docs/postman.json":
            return await self._serve_postman_collection()
        
        # OpenAPI YAML
        if path == "/docs/openapi.yaml":
            return await self._serve_openapi_yaml()
        
        # Continue with normal processing
        return await call_next(request)

    async def _serve_enhanced_openapi_json(self) -> JSONResponse:
        """Serve enhanced OpenAPI JSON schema."""
        try:
            documentation = generate_api_documentation(self.app)
            return JSONResponse(
                content=documentation["openapi_schema"],
                headers={
                    "Cache-Control": "public, max-age=3600",
                    "X-Generated-At": documentation["generated_at"]
                }
            )
        except Exception as e:
            logger.error(f"Error generating OpenAPI schema: {str(e)}")
            # Fallback to default OpenAPI
            return JSONResponse(content=self.app.openapi())

    async def _serve_custom_swagger_ui(self, request: Request) -> HTMLResponse:
        """Serve custom Swagger UI with enhanced features."""
        swagger_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{settings.PROJECT_NAME} API Documentation</title>
            <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui.css" />
            <link rel="icon" type="image/png" href="https://cdn.slidegenie.com/favicon.png" sizes="32x32" />
            <style>
                .swagger-ui .topbar {{ display: none; }}
                .swagger-ui .info .title {{ color: #1976d2; }}
                .swagger-ui .info .description {{ margin-top: 20px; }}
                .swagger-ui .scheme-container {{ background: #f8f9fa; border-radius: 8px; padding: 15px; margin-bottom: 20px; }}
                .custom-header {{ 
                    background: linear-gradient(135deg, #1976d2 0%, #42a5f5 100%);
                    color: white;
                    padding: 20px;
                    text-align: center;
                    margin-bottom: 0;
                }}
                .custom-nav {{ 
                    background: #f8f9fa;
                    padding: 10px;
                    border-bottom: 1px solid #dee2e6;
                }}
                .custom-nav a {{ 
                    color: #1976d2;
                    text-decoration: none;
                    margin: 0 15px;
                    font-weight: 500;
                }}
                .custom-nav a:hover {{ text-decoration: underline; }}
                .api-info {{ 
                    background: #e3f2fd;
                    border-left: 4px solid #1976d2;
                    padding: 15px;
                    margin: 20px 0;
                    border-radius: 4px;
                }}
            </style>
        </head>
        <body>
            <div class="custom-header">
                <h1>{settings.PROJECT_NAME} API Documentation</h1>
                <p>Version {settings.APP_VERSION} • Environment: {settings.ENVIRONMENT}</p>
            </div>
            
            <div class="custom-nav">
                <a href="/docs">Interactive API Docs</a>
                <a href="/redoc">ReDoc Documentation</a>
                <a href="/docs/sdk">SDK Examples</a>
                <a href="/docs/postman.json">Postman Collection</a>
                <a href="/docs/analytics">API Analytics</a>
                <a href="https://docs.slidegenie.com" target="_blank">Full Documentation</a>
            </div>
            
            <div class="api-info">
                <strong>Quick Start:</strong>
                <ol>
                    <li>Register for an account or login to get access tokens</li>
                    <li>Use the "Authorize" button below to authenticate your requests</li>
                    <li>Try out the endpoints directly in this interface</li>
                    <li>Check out the SDK examples for integration in your preferred language</li>
                </ol>
            </div>
            
            <div id="swagger-ui"></div>
            
            <script src="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-bundle.js"></script>
            <script>
                const ui = SwaggerUIBundle({{
                    url: '/openapi.json',
                    dom_id: '#swagger-ui',
                    presets: [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIBundle.presets.standalone
                    ],
                    layout: "StandaloneLayout",
                    deepLinking: true,
                    showExtensions: true,
                    showCommonExtensions: true,
                    defaultModelRendering: 'model',
                    defaultModelsExpandDepth: 2,
                    defaultModelExpandDepth: 2,
                    displayOperationId: true,
                    tryItOutEnabled: true,
                    requestInterceptor: (req) => {{
                        // Add custom headers or modify requests
                        req.headers['X-Client'] = 'swagger-ui';
                        return req;
                    }},
                    responseInterceptor: (res) => {{
                        // Log API responses for debugging
                        console.log('API Response:', res);
                        return res;
                    }},
                    onComplete: () => {{
                        console.log('Swagger UI loaded successfully');
                    }}
                }});
                
                // Add custom functionality
                window.ui = ui;
            </script>
        </body>
        </html>
        """
        
        return HTMLResponse(content=swagger_html)

    async def _serve_custom_redoc(self, request: Request) -> HTMLResponse:
        """Serve custom ReDoc with enhanced features."""
        redoc_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{settings.PROJECT_NAME} API Documentation</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
            <style>
                body {{ 
                    margin: 0; 
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                }}
                .custom-header {{ 
                    background: linear-gradient(135deg, #1976d2 0%, #42a5f5 100%);
                    color: white;
                    padding: 20px;
                    text-align: center;
                }}
                .custom-nav {{ 
                    background: #f8f9fa;
                    padding: 10px;
                    text-align: center;
                    border-bottom: 1px solid #dee2e6;
                }}
                .custom-nav a {{ 
                    color: #1976d2;
                    text-decoration: none;
                    margin: 0 15px;
                    font-weight: 500;
                }}
                .custom-nav a:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <div class="custom-header">
                <h1>{settings.PROJECT_NAME} API Documentation</h1>
                <p>Comprehensive API Reference • Version {settings.APP_VERSION}</p>
            </div>
            
            <div class="custom-nav">
                <a href="/docs">Interactive API Docs</a>
                <a href="/redoc">ReDoc Documentation</a>
                <a href="/docs/sdk">SDK Examples</a>
                <a href="/docs/postman.json">Postman Collection</a>
                <a href="https://docs.slidegenie.com" target="_blank">Full Documentation</a>
            </div>
            
            <redoc spec-url="/openapi.json" theme="{{
                colors: {{
                    primary: {{
                        main: '#1976d2'
                    }}
                }},
                typography: {{
                    fontSize: '14px',
                    fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif',
                    headings: {{
                        fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif',
                        fontWeight: '600'
                    }}
                }},
                sidebar: {{
                    width: '300px',
                    backgroundColor: '#fafafa'
                }},
                rightPanel: {{
                    backgroundColor: '#263238',
                    width: '40%'
                }}
            }}"></redoc>
            
            <script src="https://cdn.jsdelivr.net/npm/redoc@2.1.3/bundles/redoc.standalone.js"></script>
        </body>
        </html>
        """
        
        return HTMLResponse(content=redoc_html)

    async def _serve_analytics_dashboard(self, request: Request) -> HTMLResponse:
        """Serve API analytics dashboard."""
        if not self.enable_analytics:
            return HTMLResponse(
                "<h1>Analytics Disabled</h1><p>API analytics are disabled in this environment.</p>",
                status_code=503
            )
        
        analytics_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{settings.PROJECT_NAME} API Analytics</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body {{ 
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                    margin: 0;
                    background: #f8f9fa;
                }}
                .header {{ 
                    background: linear-gradient(135deg, #1976d2 0%, #42a5f5 100%);
                    color: white;
                    padding: 20px;
                    text-align: center;
                }}
                .container {{ 
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .stats-grid {{ 
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }}
                .stat-card {{ 
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .stat-value {{ 
                    font-size: 2em;
                    font-weight: 700;
                    color: #1976d2;
                }}
                .stat-label {{ 
                    color: #666;
                    margin-top: 5px;
                }}
                .chart-container {{ 
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    margin-bottom: 20px;
                }}
                .nav-link {{ 
                    color: #1976d2;
                    text-decoration: none;
                    margin: 0 10px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{settings.PROJECT_NAME} API Analytics</h1>
                <p>Real-time API usage statistics and performance metrics</p>
                <div>
                    <a href="/docs" class="nav-link">← Back to API Docs</a>
                </div>
            </div>
            
            <div class="container">
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value" id="total-requests">Loading...</div>
                        <div class="stat-label">Total Requests</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="unique-clients">Loading...</div>
                        <div class="stat-label">Unique Clients</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="avg-response-time">Loading...</div>
                        <div class="stat-label">Avg Response Time (ms)</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="error-rate">Loading...</div>
                        <div class="stat-label">Error Rate (%)</div>
                    </div>
                </div>
                
                <div class="chart-container">
                    <h3>Most Popular Endpoints</h3>
                    <canvas id="endpoints-chart"></canvas>
                </div>
                
                <div class="chart-container">
                    <h3>Client Types</h3>
                    <canvas id="clients-chart"></canvas>
                </div>
            </div>
            
            <script>
                // Load analytics data
                async function loadAnalytics() {{
                    try {{
                        const response = await fetch('/docs/api/analytics');
                        const data = await response.json();
                        
                        // Update stats
                        document.getElementById('total-requests').textContent = data.total_requests || 0;
                        document.getElementById('unique-clients').textContent = data.unique_clients || 0;
                        document.getElementById('avg-response-time').textContent = 
                            Math.round(data.avg_response_time || 0);
                        document.getElementById('error-rate').textContent = 
                            (data.error_rate || 0).toFixed(1);
                        
                        // Create charts
                        createEndpointsChart(data.endpoint_stats || {{}});
                        createClientsChart(data.client_stats || {{}});
                        
                    }} catch (error) {{
                        console.error('Failed to load analytics:', error);
                    }}
                }}
                
                function createEndpointsChart(endpointStats) {{
                    const ctx = document.getElementById('endpoints-chart').getContext('2d');
                    const entries = Object.entries(endpointStats).slice(0, 10);
                    
                    new Chart(ctx, {{
                        type: 'bar',
                        data: {{
                            labels: entries.map(([endpoint]) => endpoint),
                            datasets: [{{
                                label: 'Requests',
                                data: entries.map(([, count]) => count),
                                backgroundColor: '#1976d2',
                                borderRadius: 4
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            plugins: {{
                                legend: {{ display: false }}
                            }},
                            scales: {{
                                y: {{ beginAtZero: true }}
                            }}
                        }}
                    }});
                }}
                
                function createClientsChart(clientStats) {{
                    const ctx = document.getElementById('clients-chart').getContext('2d');
                    const entries = Object.entries(clientStats);
                    
                    new Chart(ctx, {{
                        type: 'doughnut',
                        data: {{
                            labels: entries.map(([client]) => client),
                            datasets: [{{
                                data: entries.map(([, count]) => count),
                                backgroundColor: [
                                    '#1976d2', '#42a5f5', '#90caf9', 
                                    '#e3f2fd', '#ffb74d', '#ff8a65'
                                ]
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            plugins: {{
                                legend: {{ position: 'bottom' }}
                            }}
                        }}
                    }});
                }}
                
                // Load analytics on page load
                loadAnalytics();
                
                // Refresh every 30 seconds
                setInterval(loadAnalytics, 30000);
            </script>
        </body>
        </html>
        """
        
        return HTMLResponse(content=analytics_html)

    async def _serve_sdk_examples(self, request: Request) -> HTMLResponse:
        """Serve SDK integration examples."""
        sdk_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{settings.PROJECT_NAME} SDK Examples</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css" rel="stylesheet">
            <style>
                body {{ 
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                    margin: 0;
                    background: #f8f9fa;
                }}
                .header {{ 
                    background: linear-gradient(135deg, #1976d2 0%, #42a5f5 100%);
                    color: white;
                    padding: 20px;
                    text-align: center;
                }}
                .container {{ 
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .sdk-section {{ 
                    background: white;
                    margin-bottom: 30px;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .sdk-header {{ 
                    background: #1976d2;
                    color: white;
                    padding: 15px 20px;
                    font-weight: 600;
                }}
                .sdk-content {{ 
                    padding: 20px;
                }}
                .code-block {{ 
                    margin: 15px 0;
                    border-radius: 8px;
                    overflow: hidden;
                }}
                .nav-link {{ 
                    color: #1976d2;
                    text-decoration: none;
                    margin: 0 10px;
                }}
                .installation {{ 
                    background: #e8f5e8;
                    border-left: 4px solid #4caf50;
                    padding: 15px;
                    margin: 15px 0;
                    border-radius: 4px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{settings.PROJECT_NAME} SDK Examples</h1>
                <p>Integration examples for popular programming languages</p>
                <div>
                    <a href="/docs" class="nav-link">← Back to API Docs</a>
                </div>
            </div>
            
            <div class="container">
                <div class="sdk-section">
                    <div class="sdk-header">Python SDK</div>
                    <div class="sdk-content">
                        <div class="installation">
                            <strong>Installation:</strong>
                            <pre><code>pip install slidegenie-python</code></pre>
                        </div>
                        
                        <h4>Quick Start</h4>
                        <div class="code-block">
                            <pre><code class="language-python">from slidegenie import SlideGenieClient

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

# Export to PowerPoint
export = client.export.create(
    presentation_id=presentation.id,
    format="pptx"
)

# Download the file
export_result = client.export.wait_for_completion(export.id)
client.export.download(export_result.download_url, "presentation.pptx")</code></pre>
                        </div>
                    </div>
                </div>
                
                <div class="sdk-section">
                    <div class="sdk-header">JavaScript/Node.js SDK</div>
                    <div class="sdk-content">
                        <div class="installation">
                            <strong>Installation:</strong>
                            <pre><code>npm install @slidegenie/js-sdk</code></pre>
                        </div>
                        
                        <h4>Quick Start</h4>
                        <div class="code-block">
                            <pre><code class="language-javascript">import {{ SlideGenieClient }} from '@slidegenie/js-sdk';

// Initialize client
const client = new SlideGenieClient({{
    apiKey: 'your-api-key',
    baseUrl: '{settings.API_BASE_URL}'
}});

// Upload document
const fileInput = document.getElementById('file-input');
const file = fileInput.files[0];

const document = await client.documents.upload(file, {{
    filename: file.name,
    processingOptions: {{
        extractCitations: true,
        detectSections: true
    }}
}});

// Generate presentation
const presentation = await client.presentations.create({{
    title: 'My Presentation',
    templateId: 'conference-template'
}});

// Generate slides
const job = await client.generation.create({{
    sourceType: 'document',
    sourceId: document.id,
    presentationId: presentation.id,
    options: {{
        maxSlides: 20,
        slideStyle: 'academic'
    }}
}});

// Monitor progress
client.generation.onProgress(job.id, (progress) => {{
    console.log(`Progress: ${{progress.progress}}%`);
    console.log(`Stage: ${{progress.stage}}`);
}});

// Wait for completion
const result = await client.generation.waitForCompletion(job.id);
console.log(`Generated ${{result.slidesGenerated}} slides!`);</code></pre>
                        </div>
                    </div>
                </div>
                
                <div class="sdk-section">
                    <div class="sdk-header">cURL Examples</div>
                    <div class="sdk-content">
                        <h4>Authentication</h4>
                        <div class="code-block">
                            <pre><code class="language-bash"># Login to get access token
curl -X POST "{settings.API_BASE_URL}/api/v1/auth/login" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "email": "user@university.edu",
    "password": "your-password"
  }}'</code></pre>
                        </div>
                        
                        <h4>Upload Document</h4>
                        <div class="code-block">
                            <pre><code class="language-bash">curl -X POST "{settings.API_BASE_URL}/api/v1/documents/upload" \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \\
  -F "file=@research_paper.pdf" \\
  -F "processing_options={{\\"extract_citations\\": true}}"</code></pre>
                        </div>
                        
                        <h4>Create Presentation</h4>
                        <div class="code-block">
                            <pre><code class="language-bash">curl -X POST "{settings.API_BASE_URL}/api/v1/presentations" \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "title": "Research Presentation",
    "description": "Generated from uploaded paper",
    "template_id": "academic-template-id"
  }}'</code></pre>
                        </div>
                        
                        <h4>Generate Slides</h4>
                        <div class="code-block">
                            <pre><code class="language-bash">curl -X POST "{settings.API_BASE_URL}/api/v1/generation/create" \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "source_type": "document",
    "source_id": "document-uuid",
    "presentation_title": "My Presentation",
    "template_id": "template-uuid",
    "generation_options": {{
      "max_slides": 15,
      "include_references": true,
      "citation_format": "APA"
    }}
  }}'</code></pre>
                        </div>
                    </div>
                </div>
            </div>
            
            <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-core.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/plugins/autoloader/prism-autoloader.min.js"></script>
        </body>
        </html>
        """
        
        return HTMLResponse(content=sdk_html)

    async def _serve_postman_collection(self) -> JSONResponse:
        """Serve Postman collection."""
        try:
            documentation = generate_api_documentation(self.app)
            return JSONResponse(
                content=documentation["postman_collection"],
                headers={
                    "Content-Disposition": f"attachment; filename=slidegenie-api-{settings.APP_VERSION}.postman_collection.json",
                    "Cache-Control": "public, max-age=3600"
                }
            )
        except Exception as e:
            logger.error(f"Error generating Postman collection: {str(e)}")
            return JSONResponse(
                content={"error": "Failed to generate Postman collection"},
                status_code=500
            )

    async def _serve_openapi_yaml(self) -> Response:
        """Serve OpenAPI specification in YAML format."""
        try:
            import yaml
            documentation = generate_api_documentation(self.app)
            yaml_content = yaml.dump(documentation["openapi_schema"], default_flow_style=False)
            
            return Response(
                content=yaml_content,
                media_type="application/x-yaml",
                headers={
                    "Content-Disposition": f"attachment; filename=slidegenie-api-{settings.APP_VERSION}.yaml",
                    "Cache-Control": "public, max-age=3600"
                }
            )
        except ImportError:
            return JSONResponse(
                content={"error": "YAML support not available"},
                status_code=503
            )
        except Exception as e:
            logger.error(f"Error generating OpenAPI YAML: {str(e)}")
            return JSONResponse(
                content={"error": "Failed to generate OpenAPI YAML"},
                status_code=500
            )

    def _setup_documentation_routes(self):
        """Setup additional documentation routes."""
        # Add analytics API endpoint
        @self.app.get("/docs/api/analytics")
        async def get_analytics_data():
            """Get API analytics data."""
            if not self.enable_analytics:
                return {"error": "Analytics disabled"}
            
            return {
                "total_requests": sum(self.endpoint_stats.values()),
                "unique_clients": len(self.client_stats),
                "endpoint_stats": dict(sorted(self.endpoint_stats.items(), key=lambda x: x[1], reverse=True)),
                "client_stats": dict(sorted(self.client_stats.items(), key=lambda x: x[1], reverse=True)),
                "avg_response_time": 0,  # Calculate from tracked data
                "error_rate": 0,  # Calculate from tracked data
                "last_updated": datetime.utcnow().isoformat()
            }

    def _add_documentation_headers(self, request: Request, response: Response):
        """Add documentation-related headers to responses."""
        # Add API version header
        response.headers["X-API-Version"] = settings.APP_VERSION
        
        # Add documentation links
        if not settings.is_production:
            response.headers["Link"] = f'<{settings.API_BASE_URL}/docs>; rel="documentation"'
        
        # Add rate limiting headers (example values)
        response.headers["X-RateLimit-Limit"] = "1000"
        response.headers["X-RateLimit-Remaining"] = "950"
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 3600)

    async def _track_api_usage(self, request: Request, response: Response, processing_time: float):
        """Track API usage for analytics."""
        if not self.enable_analytics:
            return
        
        try:
            # Track endpoint usage
            endpoint = f"{request.method} {request.url.path}"
            self.endpoint_stats[endpoint] = self.endpoint_stats.get(endpoint, 0) + 1
            
            # Track client usage
            user_agent = request.headers.get("user-agent", "unknown")
            client_type = self._extract_client_type(user_agent)
            self.client_stats[client_type] = self.client_stats.get(client_type, 0) + 1
            
            # Log for external analytics systems
            logger.info(
                "API request tracked",
                endpoint=endpoint,
                client_type=client_type,
                status_code=response.status_code,
                processing_time_ms=round(processing_time * 1000, 2)
            )
            
        except Exception as e:
            logger.error(f"Error tracking API usage: {str(e)}")

    def _extract_client_type(self, user_agent: str) -> str:
        """Extract client type from user agent."""
        user_agent_lower = user_agent.lower()
        
        if "postman" in user_agent_lower:
            return "Postman"
        elif "curl" in user_agent_lower:
            return "cURL"
        elif "python" in user_agent_lower:
            return "Python"
        elif "javascript" in user_agent_lower or "node" in user_agent_lower:
            return "JavaScript/Node.js"
        elif "swagger" in user_agent_lower:
            return "Swagger UI"
        elif "insomnia" in user_agent_lower:
            return "Insomnia"
        elif "slidegenie" in user_agent_lower:
            return "SlideGenie SDK"
        else:
            return "Other"


def setup_documentation_middleware(app: FastAPI, enable_analytics: bool = True):
    """
    Setup documentation middleware for the FastAPI app.
    
    Args:
        app: FastAPI application instance
        enable_analytics: Whether to enable analytics tracking
    """
    app.add_middleware(APIDocumentationMiddleware, enable_analytics=enable_analytics)
    
    logger.info(
        "API documentation middleware configured",
        analytics_enabled=enable_analytics,
        environment=settings.ENVIRONMENT
    )