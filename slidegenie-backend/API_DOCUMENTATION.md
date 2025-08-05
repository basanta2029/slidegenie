# SlideGenie API Documentation

## Overview

SlideGenie provides a comprehensive REST API with WebSocket support for real-time features. The API follows RESTful principles with consistent patterns for authentication, error handling, and response formats.

## Base URL

```
https://api.slidegenie.com/api/v1
```

For local development:
```
http://localhost:8000/api/v1
```

## Authentication

Most endpoints require authentication using JWT tokens. Include the token in the Authorization header:

```bash
Authorization: Bearer <your_jwt_token>
```

### Authentication Schemes

1. **JWT Bearer Token** (Primary)
   - Obtained via `/auth/login` or `/auth/register`
   - Include in Authorization header: `Bearer <token>`
   - Tokens expire after 24 hours

2. **API Key** (Service Authentication)
   - For server-to-server communication
   - Include in header: `X-API-Key: <your_api_key>`

3. **OAuth 2.0** (Social Login)
   - Support for Google and Microsoft
   - Authorization flow via `/oauth/authorize`

## API Versioning

The API supports multiple versioning strategies:

1. **URL-based** (Recommended): `/api/v1/endpoint`
2. **Header-based**: `API-Version: v1`
3. **Accept header**: `application/vnd.api+json;version=1`

Current versions:
- `v1` - Current stable version
- `v0.9` - Deprecated, will sunset on 2024-12-31

## Rate Limiting

Rate limits are enforced per endpoint type:

| Endpoint Type | Free Tier | Premium Tier | Admin |
|--------------|-----------|--------------|-------|
| Authentication | 10/min | 10/min | 10/min |
| File Upload | 5/hour | 50/hour | 1000/hour |
| Generation | 20/hour | 100/hour | 1000/hour |
| General API | 1000/hour | 5000/hour | 10000/hour |

Rate limit headers:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1640995200
X-RateLimit-Retry-After: 3600
```

## Error Handling

All errors follow a consistent format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": {
      "field_errors": [
        {
          "field": "email",
          "message": "Invalid email format",
          "code": "invalid_email"
        }
      ]
    },
    "request_id": "req_123456789",
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

Common error codes:
- `UNAUTHORIZED` - Authentication required
- `FORBIDDEN` - Insufficient permissions
- `NOT_FOUND` - Resource not found
- `VALIDATION_ERROR` - Input validation failed
- `RATE_LIMIT_EXCEEDED` - Too many requests
- `INTERNAL_ERROR` - Server error

## Core Endpoints

### API Information

#### Get API Info
```http
GET /
```

Returns API information and available endpoints.

**Response:**
```json
{
  "name": "SlideGenie API",
  "version": "1.0.0",
  "description": "AI-powered presentation generation API",
  "documentation_url": "/docs",
  "health_check_url": "/health/health",
  "endpoints": {
    "auth": "/auth",
    "presentations": "/presentations",
    "generation": "/generation",
    "templates": "/templates"
  }
}
```

#### Get API Status
```http
GET /status
```

Returns detailed API status with component health.

#### Get API Limits
```http
GET /limits
```

Returns current API limits and quotas for the authenticated user.

### Health Monitoring

#### Comprehensive Health Check
```http
GET /health/health
```

Returns detailed health status of all components.

**Query Parameters:**
- `force_refresh` (boolean): Force refresh health data

**Response:**
```json
{
  "status": "healthy",
  "components": {
    "database": {
      "status": "healthy",
      "latency_ms": 5.2,
      "details": {...}
    },
    "redis": {
      "status": "healthy",
      "latency_ms": 1.3
    },
    "storage": {
      "status": "healthy",
      "latency_ms": 23.5
    }
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### Kubernetes Probes
- **Readiness**: `GET /health/ready`
- **Liveness**: `GET /health/live`

## Authentication Endpoints

### Register
```http
POST /auth/register
Content-Type: application/json

{
  "email": "user@university.edu",
  "password": "SecurePassword123!",
  "full_name": "John Doe",
  "institution": "University Name"
}
```

### Login
```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@university.edu",
  "password": "SecurePassword123!"
}
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@university.edu",
    "full_name": "John Doe",
    "role": "user"
  }
}
```

### Refresh Token
```http
POST /auth/refresh
Authorization: Bearer <token>
```

### Logout
```http
POST /auth/logout
Authorization: Bearer <token>
```

## User Management

### Get Current User
```http
GET /users/me
Authorization: Bearer <token>
```

### Update Profile
```http
PUT /users/me
Authorization: Bearer <token>
Content-Type: application/json

{
  "full_name": "Updated Name",
  "institution": "New University"
}
```

## Presentation Management

### List Presentations
```http
GET /presentations?page=1&page_size=20&sort_by=created_at&sort_order=desc
Authorization: Bearer <token>
```

**Query Parameters:**
- `page` (int): Page number (default: 1)
- `page_size` (int): Items per page (default: 20, max: 100)
- `sort_by` (string): Sort field (created_at, updated_at, title)
- `sort_order` (string): Sort order (asc, desc)
- `search` (string): Search in title and description

### Create Presentation
```http
POST /presentations
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "My Research Presentation",
  "description": "Presentation about AI research",
  "template_id": "123e4567-e89b-12d3-a456-426614174000",
  "theme_config": {
    "colors": {
      "primary": "#003366"
    }
  }
}
```

### Get Presentation
```http
GET /presentations/{presentation_id}
Authorization: Bearer <token>
```

### Update Presentation
```http
PUT /presentations/{presentation_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "Updated Title",
  "description": "Updated description"
}
```

### Delete Presentation
```http
DELETE /presentations/{presentation_id}
Authorization: Bearer <token>
```

## Document Upload

### Upload Document
```http
POST /documents/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <binary>
metadata: {"source": "conference_paper", "year": 2024}
```

**Response:**
```json
{
  "document_id": "123e4567-e89b-12d3-a456-426614174000",
  "filename": "research_paper.pdf",
  "size_bytes": 2048576,
  "content_type": "application/pdf",
  "processing_status": "pending",
  "metadata": {
    "source": "conference_paper",
    "year": 2024
  }
}
```

### Get Upload Status
```http
GET /documents/upload/{document_id}/status
Authorization: Bearer <token>
```

## Generation Endpoints

### Start Generation
```http
POST /generation/start
Authorization: Bearer <token>
Content-Type: application/json

{
  "source_type": "document",
  "source_id": "123e4567-e89b-12d3-a456-426614174000",
  "presentation_id": "456e7890-e89b-12d3-a456-426614174000",
  "options": {
    "slide_count": 15,
    "include_references": true,
    "style": "academic"
  }
}
```

### Get Generation Status
```http
GET /generation/{job_id}/status
Authorization: Bearer <token>
```

**Response:**
```json
{
  "job_id": "789e0123-e89b-12d3-a456-426614174000",
  "status": "processing",
  "progress": 65,
  "current_step": "Generating slide content",
  "message": "Processing slide 8 of 12",
  "estimated_completion": "2024-01-01T12:05:00Z"
}
```

### Cancel Generation
```http
POST /generation/{job_id}/cancel
Authorization: Bearer <token>
```

## Slide Generation

### Generate Presentation
```http
POST /slides/generate
Authorization: Bearer <token>
Content-Type: application/json

{
  "content": "Your presentation content here",
  "output_format": "pptx",
  "options": {
    "template": "ieee-conference",
    "slide_count": 20
  }
}
```

### Generate with File Upload
```http
POST /slides/generate-advanced
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <binary>
output_format: pptx
options: {"template": "academic", "quality": "high"}
```

### Preview Presentation
```http
POST /slides/preview
Authorization: Bearer <token>
Content-Type: application/json

{
  "content": "Your content",
  "max_slides": 5
}
```

### Download Generated Presentation
```http
GET /slides/download/{job_id}
Authorization: Bearer <token>
```

## Template System

### List Templates
```http
GET /templates?category=conference&academic_field=Computer%20Science&page=1&page_size=20
Authorization: Bearer <token>
```

### Search Templates
```http
GET /templates/search?q=IEEE&category=conference
Authorization: Bearer <token>
```

### Get Template Details
```http
GET /templates/{template_id}
Authorization: Bearer <token>
```

### Clone Template
```http
POST /templates/{template_id}/clone
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "my-custom-template",
  "display_name": "My Custom Template",
  "modifications": {
    "theme": {
      "colors": {
        "primary": "#FF0000"
      }
    }
  }
}
```

### Generate Template Preview
```http
GET /templates/{template_id}/preview?slide_types=title,content&format=png
Authorization: Bearer <token>
```

## Export Endpoints

### Export to PDF
```http
POST /export/pdf
Authorization: Bearer <token>
Content-Type: application/json

{
  "presentation_id": "123e4567-e89b-12d3-a456-426614174000",
  "options": {
    "quality": "high",
    "include_notes": true
  }
}
```

### Export to PowerPoint
```http
POST /export/pptx
Authorization: Bearer <token>
Content-Type: application/json

{
  "presentation_id": "123e4567-e89b-12d3-a456-426614174000",
  "template_id": "456e7890-e89b-12d3-a456-426614174000"
}
```

### Export to Google Slides
```http
POST /export/google-slides
Authorization: Bearer <token>
Content-Type: application/json

{
  "presentation_id": "123e4567-e89b-12d3-a456-426614174000",
  "google_auth_token": "ya29..."
}
```

## Real-time Endpoints

### WebSocket Connections

#### Generation Progress
```javascript
ws://localhost:8000/api/v1/realtime/generation/{job_id}?token={jwt_token}
```

Message format:
```json
{
  "type": "job_progress",
  "job_id": "uuid",
  "data": {
    "status": "processing",
    "progress": 0.65,
    "current_step": "Generating slide content",
    "message": "Processing slide 13 of 20",
    "estimated_completion": "2024-01-01T12:30:00Z"
  }
}
```

#### Live Collaboration
```javascript
ws://localhost:8000/api/v1/realtime/collaboration/{presentation_id}?token={jwt_token}
```

Message types:
- `user_joined` - User joined collaboration session
- `user_left` - User left session
- `edit_operation` - Content edit
- `cursor_move` - Cursor position update
- `slide_locked` - Slide locked for editing
- `slide_unlocked` - Slide unlocked

#### Notifications
```javascript
ws://localhost:8000/api/v1/realtime/notifications?token={jwt_token}
```

### Server-Sent Events (SSE)

#### Generation Progress SSE
```http
GET /realtime/sse/generation/{job_id}
Authorization: Bearer <token>
```

#### Notifications SSE
```http
GET /realtime/sse/notifications
Authorization: Bearer <token>
```

## Analytics Endpoints

### Usage Statistics
```http
GET /analytics/usage?force_refresh=false
Authorization: Bearer <token>
```

**Response:**
```json
{
  "period": "last_30_days",
  "total_presentations": 150,
  "total_slides": 2250,
  "average_slides_per_presentation": 15,
  "generation_time_avg_seconds": 45,
  "top_templates": [...],
  "daily_usage": [...]
}
```

### Generation Analytics
```http
GET /analytics/generation?days=30
Authorization: Bearer <token>
```

### Export Analytics
```http
GET /analytics/exports?days=30
Authorization: Bearer <token>
```

## Admin Endpoints

All admin endpoints require admin role authentication.

### User Management
- `GET /admin/users` - List all users
- `GET /admin/users/{user_id}` - Get user details
- `PUT /admin/users/{user_id}` - Update user
- `DELETE /admin/users/{user_id}` - Delete user
- `POST /admin/users/{user_id}/suspend` - Suspend user
- `POST /admin/users/{user_id}/activate` - Activate user

### System Management
- `GET /admin/stats` - System statistics
- `GET /admin/logs` - System logs
- `POST /admin/cache/clear` - Clear cache
- `GET /admin/security/audit` - Security audit log
- `POST /admin/maintenance` - Schedule maintenance

### Template Management
- `POST /admin/templates` - Create template
- `PUT /admin/templates/{id}` - Update template
- `DELETE /admin/templates/{id}` - Delete template
- `GET /admin/templates/{id}/stats` - Template statistics

## SDK Examples

### Python SDK
```python
from slidegenie import SlideGenieClient

client = SlideGenieClient(
    api_key="your-api-key",
    base_url="https://api.slidegenie.com"
)

# Upload document
document = client.documents.upload("paper.pdf")

# Create presentation
presentation = client.presentations.create(
    title="My Presentation",
    template_id="template-id"
)

# Generate slides
job = client.generation.create(
    source_id=document.id,
    presentation_id=presentation.id
)

# Monitor progress
while job.status != "completed":
    job = client.generation.get_status(job.id)
    print(f"Progress: {job.progress}%")
```

### JavaScript/Node.js SDK
```javascript
import { SlideGenieClient } from '@slidegenie/js-sdk';

const client = new SlideGenieClient({
    apiKey: 'your-api-key',
    baseUrl: 'https://api.slidegenie.com'
});

// Async/await usage
async function generatePresentation() {
    const document = await client.documents.upload(file);
    const presentation = await client.presentations.create({
        title: 'My Presentation'
    });
    
    const job = await client.generation.create({
        sourceId: document.id,
        presentationId: presentation.id
    });
    
    // Monitor with WebSocket
    const ws = client.realtime.generationProgress(job.id);
    ws.on('progress', (data) => {
        console.log(`Progress: ${data.progress}%`);
    });
}
```

### cURL Examples
```bash
# Authentication
curl -X POST "https://api.slidegenie.com/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@university.edu", "password": "password"}'

# Upload document
curl -X POST "https://api.slidegenie.com/api/v1/documents/upload" \
  -H "Authorization: Bearer TOKEN" \
  -F "file=@paper.pdf"

# Generate presentation
curl -X POST "https://api.slidegenie.com/api/v1/generation/start" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source_id": "doc-id",
    "presentation_id": "pres-id",
    "options": {"slide_count": 15}
  }'
```

## Postman Collection

Download the Postman collection:
```http
GET /docs/postman.json
```

The collection includes:
- All endpoints with examples
- Authentication setup
- Environment variables
- Request/response examples
- WebSocket requests

## Best Practices

1. **Authentication**
   - Store tokens securely
   - Implement token refresh logic
   - Use API keys for server-to-server communication

2. **Error Handling**
   - Always check response status codes
   - Implement exponential backoff for retries
   - Log request IDs for debugging

3. **Rate Limiting**
   - Monitor rate limit headers
   - Implement queuing for bulk operations
   - Use webhooks for long-running operations

4. **Performance**
   - Use pagination for list endpoints
   - Implement caching where appropriate
   - Use WebSocket for real-time updates

5. **Security**
   - Always use HTTPS in production
   - Validate input on client side
   - Don't expose sensitive data in URLs

## Support

- Documentation: https://docs.slidegenie.com
- API Status: https://status.slidegenie.com
- Support Email: api-support@slidegenie.com
- GitHub Issues: https://github.com/slidegenie/api-issues