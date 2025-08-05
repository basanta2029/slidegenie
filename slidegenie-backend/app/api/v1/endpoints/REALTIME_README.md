# SlideGenie Real-time System

A comprehensive real-time communication system for SlideGenie that provides WebSocket and Server-Sent Events (SSE) support for live updates, collaboration, and notifications.

## 🚀 Features

### WebSocket Endpoints
- **Generation Progress** (`/realtime/generation/{job_id}`) - Real-time slide generation progress
- **Live Collaboration** (`/realtime/collaboration/{presentation_id}`) - Multi-user editing and presence
- **Notifications** (`/realtime/notifications`) - System and user notifications

### Server-Sent Events (SSE)
- **Generation Progress** (`/realtime/sse/generation/{job_id}`) - Browser-compatible progress updates
- **Notifications** (`/realtime/sse/notifications`) - Browser-compatible notifications

### Core Features
- **Connection Management** - Robust WebSocket connection handling with reconnection support
- **User Presence Tracking** - Real-time user status and activity monitoring
- **Live Editing Synchronization** - Conflict resolution and operation synchronization
- **Message Queuing** - Reliable message delivery with queue management
- **Authentication** - JWT-based WebSocket authentication
- **Error Recovery** - Comprehensive error handling and connection recovery

## 📡 WebSocket Endpoints

### Generation Progress WebSocket

Monitor real-time progress of slide generation jobs.

**Endpoint:** `ws://localhost:8000/api/v1/realtime/generation/{job_id}?token={jwt_token}`

**Connection Flow:**
```javascript
const ws = new WebSocket(`ws://localhost:8000/api/v1/realtime/generation/${jobId}?token=${token}`);

ws.onopen = () => {
    console.log('Connected to generation progress');
};

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    handleProgressUpdate(message);
};
```

**Message Types:**

| Type | Direction | Description |
|------|-----------|-------------|
| `connected` | Server → Client | Connection established |
| `job_progress` | Server → Client | Progress update |
| `ping` | Client → Server | Keepalive ping |
| `pong` | Server → Client | Keepalive response |
| `subscribe_job` | Client → Server | Subscribe to additional job |
| `unsubscribe_job` | Client → Server | Unsubscribe from job |

**Example Progress Message:**
```json
{
  "type": "job_progress",
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "data": {
    "status": "processing",
    "progress": 0.65,
    "current_step": "Generating slide content",
    "message": "Processing slide 13 of 20",
    "estimated_completion": "2024-01-01T12:30:00Z"
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Collaboration WebSocket

Enable real-time collaboration on presentations.

**Endpoint:** `ws://localhost:8000/api/v1/realtime/collaboration/{presentation_id}?token={jwt_token}`

**Features:**
- User presence tracking
- Real-time cursor positions
- Live edit operations
- Slide locking for conflict prevention
- User join/leave notifications

**Message Types:**

| Type | Direction | Description |
|------|-----------|-------------|
| `user_joined` | Server → Client | User joined session |
| `user_left` | Server → Client | User left session |
| `presence_update` | Bidirectional | User status/position update |
| `edit_operation` | Bidirectional | Live edit operation |
| `lock_slide` | Client → Server | Request slide lock |
| `unlock_slide` | Client → Server | Release slide lock |
| `cursor_update` | Bidirectional | Real-time cursor position |

**Example Edit Operation:**
```json
{
  "type": "edit_operation",
  "operation": {
    "operation_id": "op_123456789",
    "type": "insert",
    "slide_id": "slide_123e4567-e89b-12d3-a456-426614174000",
    "slide_number": 5,
    "element_id": "text_block_1",
    "position": {"line": 2, "column": 15},
    "content": {"text": "new research findings", "format": {"bold": true}},
    "user_id": "user_123e4567-e89b-12d3-a456-426614174000",
    "user_name": "Dr. Jane Smith",
    "timestamp": "2024-01-01T12:00:00Z"
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Notifications WebSocket

Receive real-time system and user notifications.

**Endpoint:** `ws://localhost:8000/api/v1/realtime/notifications?token={jwt_token}`

**Auto-subscribed Channels:**
- `general` - System-wide notifications
- `user_{user_id}` - User-specific notifications

**Message Types:**

| Type | Direction | Description |
|------|-----------|-------------|
| `notification` | Server → Client | New notification |
| `subscribe_channel` | Client → Server | Subscribe to channel |
| `unsubscribe_channel` | Client → Server | Unsubscribe from channel |
| `mark_read` | Client → Server | Mark notification as read |

**Example Notification:**
```json
{
  "type": "notification",
  "notification_type": "success",
  "title": "Presentation Generated",
  "message": "Your presentation 'Machine Learning Research' has been successfully generated with 15 slides.",
  "data": {"presentation_id": "pres_123", "slide_count": 15},
  "priority": "normal",
  "category": "generation",
  "action_url": "/presentations/pres_123",
  "action_text": "View Presentation",
  "timestamp": "2024-01-01T12:00:00Z",
  "id": "notif_123456789",
  "channel": "general"
}
```

## 🌊 Server-Sent Events (SSE)

For clients that cannot use WebSocket, SSE endpoints provide similar functionality.

### Generation Progress SSE

**Endpoint:** `GET /api/v1/realtime/sse/generation/{job_id}`
**Headers:** `Authorization: Bearer {jwt_token}`

```javascript
const eventSource = new EventSource(`/api/v1/realtime/sse/generation/${jobId}`, {
    headers: {
        'Authorization': `Bearer ${token}`
    }
});

eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleProgressUpdate(data);
};
```

### Notifications SSE

**Endpoint:** `GET /api/v1/realtime/sse/notifications`
**Headers:** `Authorization: Bearer {jwt_token}`

## 🏗️ Architecture

### Connection Managers

The system uses three specialized connection managers:

1. **GenerationProgressManager** - Handles job progress subscriptions
2. **CollaborationManager** - Manages presentation collaboration sessions
3. **NotificationManager** - Routes notifications and system messages

### Key Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Real-time System                        │
├─────────────────────────────────────────────────────────────┤
│  WebSocket Endpoints          │  SSE Endpoints             │
│  ├─ Generation Progress       │  ├─ Generation Progress    │
│  ├─ Live Collaboration       │  └─ Notifications          │
│  └─ Notifications             │                            │
├─────────────────────────────────────────────────────────────┤
│                 Connection Managers                         │
│  ├─ GenerationProgressManager  ├─ CollaborationManager     │
│  └─ NotificationManager        │                           │
├─────────────────────────────────────────────────────────────┤
│                 Integration Layer                           │
│  ├─ RealtimeService           ├─ Integration Utilities     │
│  └─ Event Handlers            │                            │
├─────────────────────────────────────────────────────────────┤
│              External Service Integration                   │
│  ├─ Generation Service        ├─ Document Processing       │
│  ├─ Collaboration Features    └─ Export Service            │
└─────────────────────────────────────────────────────────────┘
```

### Message Flow

1. **Client Connection** - WebSocket established with JWT authentication
2. **Subscription** - Client subscribes to specific jobs/channels
3. **Event Triggered** - External service triggers an event
4. **Processing** - Real-time service processes and routes the event
5. **Broadcasting** - Message sent to all relevant subscribers
6. **Client Update** - Frontend updates UI based on received message

## 🔧 Integration with Existing Services

### Generation Service Integration

```python
from app.services.realtime_integration import GenerationProgressIntegration

async def your_generation_function():
    integration = GenerationProgressIntegration()
    
    # Notify job started
    await integration.on_job_started(job_id, user_id, "presentation")
    
    # Update progress during processing
    await integration.on_parsing_progress(job_id, 0.5, "Parsing document")
    
    # Notify completion
    await integration.on_job_completed(job_id, user_id, presentation_id, slide_count)
```

### Document Processing Integration

```python
from app.services.realtime_integration import DocumentProcessingIntegration

async def your_processing_function():
    integration = DocumentProcessingIntegration()
    
    await integration.on_processing_started(job_id, user_id, filename)
    await integration.on_security_scan_complete(job_id, scan_results)
    await integration.on_content_analysis_complete(job_id, analysis_results)
```

### Collaboration Integration

```python
from app.services.realtime_integration import CollaborationIntegration

async def your_collaboration_function():
    integration = CollaborationIntegration()
    
    await integration.on_presentation_shared(
        presentation_id, title, shared_by, shared_with_users
    )
    await integration.on_comment_added(
        presentation_id, slide_number, comment, author_id, collaborators
    )
```

## 📊 Monitoring and Statistics

### System Stats Endpoint

**Endpoint:** `GET /api/v1/realtime/stats`
**Auth:** Requires authentication

```json
{
  "generation_manager": {
    "total_connections": 1250,
    "active_connections": 45,
    "active_users": 23,
    "messages_sent": 15420,
    "errors": 12,
    "uptime_seconds": 86400.0,
    "active_jobs": 8,
    "job_subscribers": 15
  },
  "collaboration_manager": {
    "active_connections": 32,
    "active_presentations": 8,
    "active_users_in_presentations": 18,
    "locked_slides": 3
  },
  "notification_manager": {
    "active_connections": 67,
    "channels": 12,
    "notification_history_size": 150
  },
  "active_presentations": 8,
  "active_generation_jobs": 3,
  "total_edit_operations": 1523,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## 🛡️ Security

### Authentication
- JWT token required for all WebSocket and SSE connections
- Token validation on connection establishment
- User permissions checked for presentation access

### Connection Security
- Connection limit per user to prevent abuse
- Rate limiting on message sending
- Automatic cleanup of stale connections

### Data Protection
- No sensitive data stored in connection managers
- All messages include timestamps for debugging
- Connection metadata limited to essential information

## 🔄 Error Handling and Recovery

### Connection Recovery
- Automatic reconnection logic on client side
- Message queuing for temporary disconnections
- Graceful degradation to SSE when WebSocket fails

### Error Types
- `AUTHENTICATION_FAILED` - Invalid or expired token
- `PERMISSION_DENIED` - Insufficient permissions for resource
- `RATE_LIMIT_EXCEEDED` - Too many messages sent
- `INTERNAL_ERROR` - Server-side processing error

### Example Error Response
```json
{
  "type": "error",
  "error_code": "PERMISSION_DENIED",
  "message": "You don't have access to this presentation",
  "details": {"presentation_id": "123", "required_permission": "view"},
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## 🚦 Performance Considerations

### Scalability
- Connection managers designed for horizontal scaling
- Message broadcasting optimized for large user bases
- Background cleanup tasks prevent memory leaks

### Optimization
- Efficient JSON serialization with custom encoders
- Connection pooling and reuse
- Message batching for high-frequency updates

### Monitoring
- Built-in statistics and metrics collection
- Connection health monitoring
- Performance tracking for message delivery

## 🧪 Testing

### WebSocket Testing with JavaScript

```javascript
// Test generation progress WebSocket
const testGenerationProgress = async (jobId, token) => {
    const ws = new WebSocket(`ws://localhost:8000/api/v1/realtime/generation/${jobId}?token=${token}`);
    
    ws.onopen = () => console.log('Connected');
    ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        console.log('Received:', message);
    };
    
    // Send ping
    setTimeout(() => {
        ws.send(JSON.stringify({type: 'ping'}));
    }, 1000);
};

// Test collaboration WebSocket
const testCollaboration = async (presentationId, token) => {
    const ws = new WebSocket(`ws://localhost:8000/api/v1/realtime/collaboration/${presentationId}?token=${token}`);
    
    ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (message.type === 'user_joined') {
            console.log('User joined:', message);
        }
    };
    
    // Send presence update
    setTimeout(() => {
        ws.send(JSON.stringify({
            type: 'presence_update',
            status: 'editing',
            current_slide: 5
        }));
    }, 1000);
};
```

### SSE Testing with curl

```bash
# Test generation progress SSE
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "Accept: text/event-stream" \
     "http://localhost:8000/api/v1/realtime/sse/generation/JOB_ID"

# Test notifications SSE
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "Accept: text/event-stream" \
     "http://localhost:8000/api/v1/realtime/sse/notifications"
```

## 🔧 Configuration

### Environment Variables

```bash
# Redis configuration (for scaling)
REDIS_URL=redis://localhost:6379

# WebSocket configuration
WEBSOCKET_MAX_CONNECTIONS_PER_USER=5
WEBSOCKET_MESSAGE_QUEUE_SIZE=100
WEBSOCKET_CLEANUP_INTERVAL=60

# SSE configuration
SSE_KEEPALIVE_INTERVAL=30
SSE_MAX_CONNECTIONS=1000
```

### Application Configuration

```python
# In app/core/config.py
class Settings:
    # Real-time settings
    realtime_enabled: bool = True
    websocket_max_connections: int = 10000
    sse_enabled: bool = True
    notification_retention_hours: int = 24
    collaboration_lock_timeout_minutes: int = 5
```

## 🚀 Getting Started

1. **Install Dependencies**
   ```bash
   pip install fastapi websockets aiofiles
   ```

2. **Import the Router**
   ```python
   from app.api.v1.endpoints.realtime import router as realtime_router
   app.include_router(realtime_router, prefix="/api/v1/realtime", tags=["realtime"])
   ```

3. **Initialize Services**
   ```python
   from app.services.realtime_integration import setup_integrations
   
   @app.on_event("startup")
   async def startup():
       await setup_integrations()
   ```

4. **Frontend Integration**
   ```javascript
   // Connect to generation progress
   const progressWs = new WebSocket(`ws://localhost:8000/api/v1/realtime/generation/${jobId}?token=${token}`);
   
   // Connect to collaboration
   const collabWs = new WebSocket(`ws://localhost:8000/api/v1/realtime/collaboration/${presentationId}?token=${token}`);
   
   // Connect to notifications
   const notificationWs = new WebSocket(`ws://localhost:8000/api/v1/realtime/notifications?token=${token}`);
   ```

## 📚 API Reference

### WebSocket Message Schemas

All message schemas are defined in `app/domain/schemas/realtime.py` and include:

- `WebSocketMessage` - Base message structure
- `GenerationProgressUpdate` - Progress update data
- `UserPresence` - User presence information
- `EditOperation` - Collaborative edit operation
- `SlideLock` - Slide locking information
- `Notification` - Notification message structure

### Integration Utilities

Integration utilities in `app/services/realtime_integration.py` provide:

- `GenerationProgressIntegration` - Generation service integration
- `DocumentProcessingIntegration` - Document processing integration
- `CollaborationIntegration` - Collaboration features integration
- `ExportIntegration` - Export service integration
- `SystemIntegration` - System-wide events integration

## 🤝 Contributing

When extending the real-time system:

1. Add new message types to the schemas
2. Implement handlers in the appropriate manager
3. Create integration utilities for external services
4. Update documentation and examples
5. Add comprehensive tests

## 📄 License

This real-time system is part of the SlideGenie project and follows the same licensing terms.