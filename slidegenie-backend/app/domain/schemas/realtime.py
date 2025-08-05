"""
Schemas for real-time features including WebSocket and SSE communication.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class WebSocketMessage(BaseModel):
    """Base WebSocket message structure."""
    type: str = Field(..., description="Message type")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(default_factory=dict)
    channel: Optional[str] = None
    sender_id: Optional[UUID] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class GenerationProgressUpdate(BaseModel):
    """Generation progress update message."""
    job_id: UUID
    status: str  # pending, processing, completed, failed, cancelled
    progress: float = Field(ge=0.0, le=1.0, description="Progress percentage (0.0 to 1.0)")
    current_step: str
    message: Optional[str] = None
    estimated_completion: Optional[datetime] = None
    error_message: Optional[str] = None
    result_data: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "processing",
                "progress": 0.65,
                "current_step": "Generating slide content",
                "message": "Processing slide 13 of 20",
                "estimated_completion": "2024-01-01T12:30:00Z"
            }
        }


class UserPresence(BaseModel):
    """User presence information for collaboration."""
    user_id: UUID
    user_name: str
    email: str
    status: str = Field(..., description="online, away, editing, viewing")
    last_seen: datetime
    current_slide: Optional[int] = Field(None, description="Currently viewing slide number")
    cursor_position: Optional[Dict[str, Any]] = Field(None, description="Current cursor position")
    active_section: Optional[str] = Field(None, description="Current section being edited")
    is_editing: bool = Field(default=False, description="Whether user is actively editing")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "user_name": "Dr. Jane Smith",
                "email": "jane.smith@university.edu",
                "status": "editing",
                "last_seen": "2024-01-01T12:00:00Z",
                "current_slide": 5,
                "cursor_position": {"x": 250, "y": 100, "element_id": "text_block_1"},
                "active_section": "Introduction",
                "is_editing": True
            }
        }


class EditOperation(BaseModel):
    """Real-time edit operation for collaboration."""
    operation_id: str = Field(..., description="Unique operation identifier")
    type: str = Field(..., description="insert, delete, replace, move, format")
    slide_id: Optional[UUID] = None
    slide_number: Optional[int] = None
    element_id: Optional[str] = Field(None, description="ID of the element being edited")
    position: Optional[Dict[str, Any]] = Field(None, description="Position information for the operation")
    content: Optional[Dict[str, Any]] = Field(None, description="Content being added/modified")
    previous_content: Optional[Dict[str, Any]] = Field(None, description="Previous content for undo")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional operation metadata")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: UUID
    user_name: str
    applied: bool = Field(default=False, description="Whether operation has been applied")
    conflicts: List[str] = Field(default_factory=list, description="List of conflicting operations")

    class Config:
        json_schema_extra = {
            "example": {
                "operation_id": "op_123456789",
                "type": "insert",
                "slide_id": "slide_123e4567-e89b-12d3-a456-426614174000",
                "slide_number": 5,
                "element_id": "text_block_1",
                "position": {"line": 2, "column": 15},
                "content": {"text": "new research findings", "format": {"bold": True}},
                "metadata": {"selection_range": [15, 36]},
                "timestamp": "2024-01-01T12:00:00Z",
                "user_id": "user_123e4567-e89b-12d3-a456-426614174000",
                "user_name": "Dr. Jane Smith",
                "applied": False
            }
        }


class SlideLock(BaseModel):
    """Slide lock information for edit conflict prevention."""
    slide_id: UUID
    presentation_id: UUID
    locked_by_user_id: UUID
    locked_by_user_name: str
    locked_at: datetime
    expires_at: datetime
    lock_type: str = Field(default="edit", description="edit, view, comment")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "slide_id": "slide_123e4567-e89b-12d3-a456-426614174000",
                "presentation_id": "pres_123e4567-e89b-12d3-a456-426614174000",
                "locked_by_user_id": "user_123e4567-e89b-12d3-a456-426614174000",
                "locked_by_user_name": "Dr. Jane Smith",
                "locked_at": "2024-01-01T12:00:00Z",
                "expires_at": "2024-01-01T12:05:00Z",
                "lock_type": "edit"
            }
        }


class Notification(BaseModel):
    """Real-time notification message."""
    id: str = Field(..., description="Unique notification identifier")
    type: str = Field(..., description="Notification type: info, warning, error, success")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    data: Dict[str, Any] = Field(default_factory=dict, description="Additional notification data")
    priority: str = Field(default="normal", description="low, normal, high, urgent")
    category: str = Field(default="general", description="Notification category")
    action_url: Optional[str] = Field(None, description="URL for notification action")
    action_text: Optional[str] = Field(None, description="Text for notification action")
    expires_at: Optional[datetime] = Field(None, description="When notification expires")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    read: bool = Field(default=False, description="Whether notification has been read")
    user_id: Optional[UUID] = Field(None, description="Target user ID (null for broadcast)")
    channel: str = Field(default="general", description="Notification channel")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "notif_123456789",
                "type": "success",
                "title": "Presentation Generated",
                "message": "Your presentation 'Machine Learning Research' has been successfully generated with 15 slides.",
                "data": {"presentation_id": "pres_123", "slide_count": 15},
                "priority": "normal",
                "category": "generation",
                "action_url": "/presentations/pres_123",
                "action_text": "View Presentation",
                "timestamp": "2024-01-01T12:00:00Z",
                "read": False,
                "channel": "general"
            }
        }


class CollaborationSession(BaseModel):
    """Information about an active collaboration session."""
    presentation_id: UUID
    presentation_title: str
    active_users: List[UserPresence]
    locked_slides: List[SlideLock]
    recent_operations: List[EditOperation]
    session_started: datetime
    last_activity: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "presentation_id": "pres_123e4567-e89b-12d3-a456-426614174000",
                "presentation_title": "Machine Learning Research Presentation",
                "active_users": [],
                "locked_slides": [],
                "recent_operations": [],
                "session_started": "2024-01-01T11:00:00Z",
                "last_activity": "2024-01-01T12:00:00Z"
            }
        }


class ConnectionStats(BaseModel):
    """WebSocket connection statistics."""
    total_connections: int = Field(..., description="Total connections made")
    active_connections: int = Field(..., description="Currently active connections")
    active_users: int = Field(..., description="Number of unique active users")
    messages_sent: int = Field(..., description="Total messages sent")
    errors: int = Field(..., description="Number of errors encountered")
    uptime_seconds: float = Field(..., description="System uptime in seconds")
    average_connections_per_user: float = Field(..., description="Average connections per user")

    class Config:
        json_schema_extra = {
            "example": {
                "total_connections": 1250,
                "active_connections": 45,
                "active_users": 23,
                "messages_sent": 15420,
                "errors": 12,
                "uptime_seconds": 86400.0,
                "average_connections_per_user": 1.96
            }
        }


class RealtimeSystemStats(BaseModel):
    """Complete real-time system statistics."""
    generation_manager: ConnectionStats
    collaboration_manager: ConnectionStats
    notification_manager: ConnectionStats
    active_presentations: int = Field(..., description="Number of presentations with active collaboration")
    active_generation_jobs: int = Field(..., description="Number of active generation jobs")
    total_edit_operations: int = Field(..., description="Total edit operations processed")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "generation_manager": {},
                "collaboration_manager": {},
                "notification_manager": {},
                "active_presentations": 8,
                "active_generation_jobs": 3,
                "total_edit_operations": 1523,
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }


# WebSocket message types for client-server communication

class PingMessage(BaseModel):
    """Ping message for connection keepalive."""
    type: str = Field(default="ping", const=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PongMessage(BaseModel):
    """Pong response message."""
    type: str = Field(default="pong", const=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SubscribeMessage(BaseModel):
    """Subscription request message."""
    type: str = Field(default="subscribe", const=True)
    job_ids: List[UUID] = Field(default_factory=list, description="Job IDs to subscribe to")
    channels: List[str] = Field(default_factory=list, description="Channels to subscribe to")
    presentation_id: Optional[UUID] = Field(None, description="Presentation ID for collaboration")


class UnsubscribeMessage(BaseModel):
    """Unsubscription request message."""
    type: str = Field(default="unsubscribe", const=True)
    job_ids: List[UUID] = Field(default_factory=list, description="Job IDs to unsubscribe from")
    channels: List[str] = Field(default_factory=list, description="Channels to unsubscribe from")


class PresenceUpdateMessage(BaseModel):
    """User presence update message."""
    type: str = Field(default="presence_update", const=True)
    status: str = Field(..., description="User status: online, away, editing, viewing")
    current_slide: Optional[int] = Field(None, description="Current slide number")
    cursor_position: Optional[Dict[str, Any]] = Field(None, description="Cursor position")
    active_section: Optional[str] = Field(None, description="Active section")


class EditOperationMessage(BaseModel):
    """Edit operation message."""
    type: str = Field(default="edit_operation", const=True)
    operation: EditOperation


class LockSlideMessage(BaseModel):
    """Lock slide request message."""
    type: str = Field(default="lock_slide", const=True)
    slide_id: UUID
    lock_type: str = Field(default="edit", description="edit, view, comment")


class UnlockSlideMessage(BaseModel):
    """Unlock slide request message."""
    type: str = Field(default="unlock_slide", const=True)
    slide_id: UUID


class CursorUpdateMessage(BaseModel):
    """Real-time cursor position update."""
    type: str = Field(default="cursor_update", const=True)
    cursor: Dict[str, Any] = Field(..., description="Cursor position and metadata")


class ErrorMessage(BaseModel):
    """Error message."""
    type: str = Field(default="error", const=True)
    error_code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow)