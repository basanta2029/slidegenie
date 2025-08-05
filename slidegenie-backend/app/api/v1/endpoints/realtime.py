"""
Comprehensive real-time features for SlideGenie.

Provides WebSocket and Server-Sent Events (SSE) support for:
- Real-time generation progress updates
- Live collaboration features
- User presence tracking
- Real-time notifications
- Live editing synchronization
- Connection management and broadcasting
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import get_current_user_websocket, get_current_user
from app.domain.schemas.user import User
from app.infrastructure.database.base import get_db
from app.infrastructure.database.models import Presentation
from app.repositories.presentation import PresentationRepository

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()

# Global connection managers
generation_manager = None
collaboration_manager = None
notification_manager = None


class RealtimeMessage(BaseModel):
    """Base real-time message structure."""
    type: str = Field(..., description="Message type")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(default_factory=dict)
    channel: Optional[str] = None
    sender_id: Optional[UUID] = None


class PresenceInfo(BaseModel):
    """User presence information."""
    user_id: UUID
    user_name: str
    email: str
    status: str  # online, away, editing, viewing
    last_seen: datetime
    current_slide: Optional[int] = None
    cursor_position: Optional[Dict[str, Any]] = None
    active_section: Optional[str] = None


class EditOperation(BaseModel):
    """Real-time edit operation."""
    operation_id: str = Field(default_factory=lambda: str(uuid4()))
    type: str  # insert, delete, replace, move
    slide_id: Optional[UUID] = None
    slide_number: Optional[int] = None
    element_id: Optional[str] = None
    position: Optional[Dict[str, Any]] = None
    content: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: UUID
    applied: bool = False


class ConnectionManager:
    """Base connection manager for WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[UUID, Set[str]] = {}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        self.message_queue: Dict[str, List[Dict[str, Any]]] = {}
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "messages_sent": 0,
            "errors": 0,
            "uptime_start": datetime.utcnow()
        }

    async def connect(self, websocket: WebSocket, connection_id: str, user_id: UUID, metadata: Dict[str, Any] = None) -> None:
        """Accept new WebSocket connection."""
        await websocket.accept()
        
        self.active_connections[connection_id] = websocket
        
        # Track user connections
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)
        
        # Store metadata
        self.connection_metadata[connection_id] = {
            "user_id": user_id,
            "connected_at": datetime.utcnow(),
            "last_ping": datetime.utcnow(),
            "metadata": metadata or {}
        }
        
        # Initialize message queue
        self.message_queue[connection_id] = []
        
        self.stats["total_connections"] += 1
        self.stats["active_connections"] = len(self.active_connections)
        
        logger.info(f"WebSocket connection {connection_id} established for user {user_id}")

    async def disconnect(self, connection_id: str) -> None:
        """Handle WebSocket disconnection."""
        if connection_id not in self.active_connections:
            return
        
        # Get user info before cleanup
        metadata = self.connection_metadata.get(connection_id, {})
        user_id = metadata.get("user_id")
        
        # Remove from active connections
        del self.active_connections[connection_id]
        
        # Remove from user connections
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        # Cleanup metadata and message queue
        self.connection_metadata.pop(connection_id, None)
        self.message_queue.pop(connection_id, None)
        
        self.stats["active_connections"] = len(self.active_connections)
        
        logger.info(f"WebSocket connection {connection_id} disconnected")

    async def send_personal_message(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """Send message to specific connection."""
        if connection_id not in self.active_connections:
            return False
        
        try:
            websocket = self.active_connections[connection_id]
            await websocket.send_text(json.dumps(message, default=str))
            self.stats["messages_sent"] += 1
            return True
        except Exception as e:
            logger.error(f"Failed to send message to {connection_id}: {e}")
            self.stats["errors"] += 1
            await self.disconnect(connection_id)
            return False

    async def send_to_user(self, user_id: UUID, message: Dict[str, Any]) -> int:
        """Send message to all connections of a user."""
        if user_id not in self.user_connections:
            return 0
        
        sent_count = 0
        connections = list(self.user_connections[user_id])
        
        for connection_id in connections:
            if await self.send_personal_message(connection_id, message):
                sent_count += 1
        
        return sent_count

    async def broadcast(self, message: Dict[str, Any], exclude_user: Optional[UUID] = None) -> int:
        """Broadcast message to all connections."""
        sent_count = 0
        connections = list(self.active_connections.keys())
        
        for connection_id in connections:
            metadata = self.connection_metadata.get(connection_id, {})
            if exclude_user and metadata.get("user_id") == exclude_user:
                continue
            
            if await self.send_personal_message(connection_id, message):
                sent_count += 1
        
        return sent_count

    async def queue_message(self, connection_id: str, message: Dict[str, Any]) -> None:
        """Queue message for delivery when connection is available."""
        if connection_id in self.message_queue:
            self.message_queue[connection_id].append(message)
            # Limit queue size
            if len(self.message_queue[connection_id]) > 100:
                self.message_queue[connection_id] = self.message_queue[connection_id][-100:]

    async def deliver_queued_messages(self, connection_id: str) -> None:
        """Deliver all queued messages for a connection."""
        if connection_id not in self.message_queue:
            return
        
        messages = self.message_queue[connection_id]
        self.message_queue[connection_id] = []
        
        for message in messages:
            await self.send_personal_message(connection_id, message)

    def get_user_connections(self, user_id: UUID) -> List[str]:
        """Get all connection IDs for a user."""
        return list(self.user_connections.get(user_id, set()))

    def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get connection metadata."""
        return self.connection_metadata.get(connection_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get connection manager statistics."""
        uptime = datetime.utcnow() - self.stats["uptime_start"]
        return {
            **self.stats,
            "uptime_seconds": uptime.total_seconds(),
            "active_users": len(self.user_connections),
            "average_connections_per_user": (
                len(self.active_connections) / len(self.user_connections)
                if self.user_connections else 0
            )
        }


class GenerationProgressManager(ConnectionManager):
    """Manages real-time generation progress updates."""
    
    def __init__(self):
        super().__init__()
        self.job_subscribers: Dict[UUID, Set[str]] = {}
        self.active_jobs: Dict[UUID, Dict[str, Any]] = {}

    async def subscribe_to_job(self, connection_id: str, job_id: UUID) -> None:
        """Subscribe connection to job progress updates."""
        if job_id not in self.job_subscribers:
            self.job_subscribers[job_id] = set()
        self.job_subscribers[job_id].add(connection_id)
        
        # Send current job status if available
        if job_id in self.active_jobs:
            await self.send_personal_message(connection_id, {
                "type": "job_progress",
                "job_id": str(job_id),
                "data": self.active_jobs[job_id],
                "timestamp": datetime.utcnow().isoformat()
            })

    async def unsubscribe_from_job(self, connection_id: str, job_id: UUID) -> None:
        """Unsubscribe connection from job progress updates."""
        if job_id in self.job_subscribers:
            self.job_subscribers[job_id].discard(connection_id)
            if not self.job_subscribers[job_id]:
                del self.job_subscribers[job_id]

    async def update_job_progress(self, job_id: UUID, progress_data: Dict[str, Any]) -> None:
        """Update job progress and notify subscribers."""
        self.active_jobs[job_id] = progress_data
        
        if job_id not in self.job_subscribers:
            return
        
        message = {
            "type": "job_progress",
            "job_id": str(job_id),
            "data": progress_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send to all subscribers
        subscribers = list(self.job_subscribers[job_id])
        for connection_id in subscribers:
            await self.send_personal_message(connection_id, message)

    async def complete_job(self, job_id: UUID, result_data: Dict[str, Any]) -> None:
        """Mark job as complete and send final update."""
        await self.update_job_progress(job_id, {
            "status": "completed",
            "progress": 1.0,
            "result": result_data,
            "completed_at": datetime.utcnow().isoformat()
        })
        
        # Clean up after delay to allow final message delivery
        await asyncio.sleep(5)
        self.active_jobs.pop(job_id, None)
        self.job_subscribers.pop(job_id, None)

    async def disconnect(self, connection_id: str) -> None:
        """Handle disconnection and cleanup subscriptions."""
        # Remove from all job subscriptions
        for job_id in list(self.job_subscribers.keys()):
            self.job_subscribers[job_id].discard(connection_id)
            if not self.job_subscribers[job_id]:
                del self.job_subscribers[job_id]
        
        await super().disconnect(connection_id)


class CollaborationManager(ConnectionManager):
    """Manages real-time collaboration features."""
    
    def __init__(self):
        super().__init__()
        self.presentation_sessions: Dict[UUID, Set[str]] = {}
        self.user_presence: Dict[UUID, Dict[UUID, PresenceInfo]] = {}  # presentation_id -> user_id -> presence
        self.edit_operations: Dict[UUID, List[EditOperation]] = {}  # presentation_id -> operations
        self.presentation_locks: Dict[UUID, Dict[str, Any]] = {}  # slide locks

    async def join_presentation(self, connection_id: str, presentation_id: UUID, user_id: UUID, user_name: str, email: str) -> None:
        """Join collaborative session for a presentation."""
        # Add to presentation session
        if presentation_id not in self.presentation_sessions:
            self.presentation_sessions[presentation_id] = set()
        self.presentation_sessions[presentation_id].add(connection_id)
        
        # Update user presence
        if presentation_id not in self.user_presence:
            self.user_presence[presentation_id] = {}
        
        self.user_presence[presentation_id][user_id] = PresenceInfo(
            user_id=user_id,
            user_name=user_name,
            email=email,
            status="online",
            last_seen=datetime.utcnow()
        )
        
        # Update connection metadata
        if connection_id in self.connection_metadata:
            self.connection_metadata[connection_id]["presentation_id"] = presentation_id
        
        # Notify other users
        await self.broadcast_to_presentation(presentation_id, {
            "type": "user_joined",
            "user_id": str(user_id),
            "user_name": user_name,
            "timestamp": datetime.utcnow().isoformat()
        }, exclude_connection=connection_id)
        
        # Send current presence info to new user
        presence_list = [
            {
                "user_id": str(p.user_id),
                "user_name": p.user_name,
                "email": p.email,
                "status": p.status,
                "last_seen": p.last_seen.isoformat(),
                "current_slide": p.current_slide,
                "active_section": p.active_section
            }
            for p in self.user_presence[presentation_id].values()
        ]
        
        await self.send_personal_message(connection_id, {
            "type": "presence_update",
            "presentation_id": str(presentation_id),
            "users": presence_list,
            "timestamp": datetime.utcnow().isoformat()
        })

    async def leave_presentation(self, connection_id: str, presentation_id: UUID, user_id: UUID) -> None:
        """Leave collaborative session."""
        # Remove from presentation session
        if presentation_id in self.presentation_sessions:
            self.presentation_sessions[presentation_id].discard(connection_id)
            if not self.presentation_sessions[presentation_id]:
                del self.presentation_sessions[presentation_id]
        
        # Update presence
        if presentation_id in self.user_presence and user_id in self.user_presence[presentation_id]:
            user_name = self.user_presence[presentation_id][user_id].user_name
            del self.user_presence[presentation_id][user_id]
            
            # Notify others
            await self.broadcast_to_presentation(presentation_id, {
                "type": "user_left",
                "user_id": str(user_id),
                "user_name": user_name,
                "timestamp": datetime.utcnow().isoformat()
            })

    async def update_user_presence(self, presentation_id: UUID, user_id: UUID, status: str, current_slide: Optional[int] = None, cursor_position: Optional[Dict[str, Any]] = None) -> None:
        """Update user presence information."""
        if presentation_id not in self.user_presence or user_id not in self.user_presence[presentation_id]:
            return
        
        presence = self.user_presence[presentation_id][user_id]
        presence.status = status
        presence.last_seen = datetime.utcnow()
        if current_slide is not None:
            presence.current_slide = current_slide
        if cursor_position is not None:
            presence.cursor_position = cursor_position
        
        # Broadcast presence update
        await self.broadcast_to_presentation(presentation_id, {
            "type": "presence_update",
            "user_id": str(user_id),
            "status": status,
            "current_slide": current_slide,
            "cursor_position": cursor_position,
            "timestamp": datetime.utcnow().isoformat()
        })

    async def handle_edit_operation(self, presentation_id: UUID, operation: EditOperation) -> None:
        """Handle real-time edit operation."""
        # Store operation
        if presentation_id not in self.edit_operations:
            self.edit_operations[presentation_id] = []
        
        self.edit_operations[presentation_id].append(operation)
        
        # Limit operation history
        if len(self.edit_operations[presentation_id]) > 1000:
            self.edit_operations[presentation_id] = self.edit_operations[presentation_id][-1000:]
        
        # Broadcast to other users
        await self.broadcast_to_presentation(presentation_id, {
            "type": "edit_operation",
            "operation": operation.dict(),
            "timestamp": datetime.utcnow().isoformat()
        }, exclude_user=operation.user_id)

    async def lock_slide(self, presentation_id: UUID, slide_id: UUID, user_id: UUID, user_name: str) -> bool:
        """Lock a slide for editing."""
        if presentation_id not in self.presentation_locks:
            self.presentation_locks[presentation_id] = {}
        
        slide_key = str(slide_id)
        current_lock = self.presentation_locks[presentation_id].get(slide_key)
        
        # Check if already locked by someone else
        if current_lock and current_lock["user_id"] != user_id:
            # Check if lock is expired (5 minutes)
            lock_time = datetime.fromisoformat(current_lock["locked_at"])
            if datetime.utcnow() - lock_time < timedelta(minutes=5):
                return False
        
        # Acquire lock
        self.presentation_locks[presentation_id][slide_key] = {
            "user_id": user_id,
            "user_name": user_name,
            "locked_at": datetime.utcnow().isoformat()
        }
        
        # Notify others
        await self.broadcast_to_presentation(presentation_id, {
            "type": "slide_locked",
            "slide_id": str(slide_id),
            "user_id": str(user_id),
            "user_name": user_name,
            "timestamp": datetime.utcnow().isoformat()
        }, exclude_user=user_id)
        
        return True

    async def unlock_slide(self, presentation_id: UUID, slide_id: UUID, user_id: UUID) -> None:
        """Unlock a slide."""
        if presentation_id not in self.presentation_locks:
            return
        
        slide_key = str(slide_id)
        current_lock = self.presentation_locks[presentation_id].get(slide_key)
        
        if current_lock and current_lock["user_id"] == user_id:
            del self.presentation_locks[presentation_id][slide_key]
            
            # Notify others
            await self.broadcast_to_presentation(presentation_id, {
                "type": "slide_unlocked",
                "slide_id": str(slide_id),
                "user_id": str(user_id),
                "timestamp": datetime.utcnow().isoformat()
            })

    async def broadcast_to_presentation(self, presentation_id: UUID, message: Dict[str, Any], exclude_connection: Optional[str] = None, exclude_user: Optional[UUID] = None) -> int:
        """Broadcast message to all users in a presentation session."""
        if presentation_id not in self.presentation_sessions:
            return 0
        
        sent_count = 0
        connections = list(self.presentation_sessions[presentation_id])
        
        for connection_id in connections:
            if exclude_connection and connection_id == exclude_connection:
                continue
            
            metadata = self.connection_metadata.get(connection_id, {})
            if exclude_user and metadata.get("user_id") == exclude_user:
                continue
            
            if await self.send_personal_message(connection_id, message):
                sent_count += 1
        
        return sent_count

    async def disconnect(self, connection_id: str) -> None:
        """Handle disconnection and cleanup collaboration state."""
        metadata = self.connection_metadata.get(connection_id, {})
        presentation_id = metadata.get("presentation_id")
        user_id = metadata.get("user_id")
        
        if presentation_id and user_id:
            await self.leave_presentation(connection_id, presentation_id, user_id)
        
        await super().disconnect(connection_id)


class NotificationManager(ConnectionManager):
    """Manages real-time notifications and system messages."""
    
    def __init__(self):
        super().__init__()
        self.channel_subscriptions: Dict[str, Set[str]] = {}
        self.notification_history: List[Dict[str, Any]] = []

    async def subscribe_to_channel(self, connection_id: str, channel: str) -> None:
        """Subscribe connection to notification channel."""
        if channel not in self.channel_subscriptions:
            self.channel_subscriptions[channel] = set()
        self.channel_subscriptions[channel].add(connection_id)

    async def unsubscribe_from_channel(self, connection_id: str, channel: str) -> None:
        """Unsubscribe connection from notification channel."""
        if channel in self.channel_subscriptions:
            self.channel_subscriptions[channel].discard(connection_id)
            if not self.channel_subscriptions[channel]:
                del self.channel_subscriptions[channel]

    async def send_notification(self, notification_type: str, title: str, message: str, data: Dict[str, Any] = None, channel: str = "general", user_id: Optional[UUID] = None) -> None:
        """Send notification to channel or specific user."""
        notification = {
            "type": "notification",
            "notification_type": notification_type,
            "title": title,
            "message": message,
            "data": data or {},
            "timestamp": datetime.utcnow().isoformat(),
            "id": str(uuid4())
        }
        
        # Store in history
        self.notification_history.append(notification)
        if len(self.notification_history) > 1000:
            self.notification_history = self.notification_history[-1000:]
        
        if user_id:
            # Send to specific user
            await self.send_to_user(user_id, notification)
        else:
            # Broadcast to channel
            await self.broadcast_to_channel(channel, notification)

    async def broadcast_to_channel(self, channel: str, message: Dict[str, Any]) -> int:
        """Broadcast message to all subscribers of a channel."""
        if channel not in self.channel_subscriptions:
            return 0
        
        sent_count = 0
        connections = list(self.channel_subscriptions[channel])
        
        for connection_id in connections:
            if await self.send_personal_message(connection_id, {**message, "channel": channel}):
                sent_count += 1
        
        return sent_count

    async def disconnect(self, connection_id: str) -> None:
        """Handle disconnection and cleanup subscriptions."""
        # Remove from all channel subscriptions
        for channel in list(self.channel_subscriptions.keys()):
            self.channel_subscriptions[channel].discard(connection_id)
            if not self.channel_subscriptions[channel]:
                del self.channel_subscriptions[channel]
        
        await super().disconnect(connection_id)


# Initialize global managers
generation_manager = GenerationProgressManager()
collaboration_manager = CollaborationManager()
notification_manager = NotificationManager()


@router.websocket("/generation/{job_id}")
async def websocket_generation_progress(
    websocket: WebSocket,
    job_id: UUID,
    token: str = Query(..., description="Authentication token")
):
    """
    WebSocket endpoint for real-time generation progress updates.
    
    Provides live updates for document processing and slide generation jobs.
    """
    connection_id = str(uuid4())
    
    try:
        # Authenticate user
        user = await get_current_user_websocket(token)
        
        # Connect to generation manager
        await generation_manager.connect(websocket, connection_id, user.id, {
            "type": "generation",
            "job_id": str(job_id)
        })
        
        # Subscribe to job progress
        await generation_manager.subscribe_to_job(connection_id, job_id)
        
        # Send initial status
        await generation_manager.send_personal_message(connection_id, {
            "type": "connected",
            "job_id": str(job_id),
            "message": "Connected to generation progress updates",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Handle incoming messages
        while True:
            try:
                message_text = await websocket.receive_text()
                message_data = json.loads(message_text)
                message_type = message_data.get("type")
                
                if message_type == "ping":
                    # Update last ping time
                    if connection_id in generation_manager.connection_metadata:
                        generation_manager.connection_metadata[connection_id]["last_ping"] = datetime.utcnow()
                    
                    await generation_manager.send_personal_message(connection_id, {
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                elif message_type == "subscribe_job":
                    # Subscribe to additional job
                    additional_job_id = UUID(message_data.get("job_id"))
                    await generation_manager.subscribe_to_job(connection_id, additional_job_id)
                
                elif message_type == "unsubscribe_job":
                    # Unsubscribe from job
                    unsubscribe_job_id = UUID(message_data.get("job_id"))
                    await generation_manager.unsubscribe_from_job(connection_id, unsubscribe_job_id)
                
                else:
                    await generation_manager.send_personal_message(connection_id, {
                        "type": "error",
                        "message": f"Unknown message type: {message_type}",
                        "timestamp": datetime.utcnow().isoformat()
                    })
            
            except json.JSONDecodeError:
                await generation_manager.send_personal_message(connection_id, {
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.error(f"Error handling generation WebSocket message: {e}")
                await generation_manager.send_personal_message(connection_id, {
                    "type": "error",
                    "message": "Internal error processing message",
                    "timestamp": datetime.utcnow().isoformat()
                })
    
    except WebSocketDisconnect:
        logger.info(f"Generation WebSocket client disconnected: {connection_id}")
    except HTTPException as e:
        logger.warning(f"Generation WebSocket authentication failed: {e.detail}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    except Exception as e:
        logger.error(f"Generation WebSocket error: {e}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
    finally:
        await generation_manager.disconnect(connection_id)


@router.websocket("/collaboration/{presentation_id}")
async def websocket_collaboration(
    websocket: WebSocket,
    presentation_id: UUID,
    token: str = Query(..., description="Authentication token"),
    db: AsyncSession = Depends(get_db)
):
    """
    WebSocket endpoint for live collaboration features.
    
    Provides real-time collaboration including presence, editing, and synchronization.
    """
    connection_id = str(uuid4())
    
    try:
        # Authenticate user
        user = await get_current_user_websocket(token)
        
        # Verify access to presentation
        presentation_repo = PresentationRepository(db)
        presentation = await presentation_repo.get(presentation_id)
        
        if not presentation:
            await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
            return
        
        # Check permissions (owner, collaborator, or public)
        if presentation.owner_id != user.id and not presentation.is_public:
            # TODO: Check if user is collaborator
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        
        # Connect to collaboration manager
        await collaboration_manager.connect(websocket, connection_id, user.id, {
            "type": "collaboration",
            "presentation_id": str(presentation_id)
        })
        
        # Join presentation session
        await collaboration_manager.join_presentation(
            connection_id, presentation_id, user.id, user.full_name, user.email
        )
        
        # Handle incoming messages
        while True:
            try:
                message_text = await websocket.receive_text()
                message_data = json.loads(message_text)
                message_type = message_data.get("type")
                
                if message_type == "ping":
                    # Update presence and respond with pong
                    await collaboration_manager.update_user_presence(
                        presentation_id, user.id, "online"
                    )
                    await collaboration_manager.send_personal_message(connection_id, {
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                elif message_type == "presence_update":
                    # Update user presence
                    status_update = message_data.get("status", "online")
                    current_slide = message_data.get("current_slide")
                    cursor_position = message_data.get("cursor_position")
                    
                    await collaboration_manager.update_user_presence(
                        presentation_id, user.id, status_update, current_slide, cursor_position
                    )
                
                elif message_type == "edit_operation":
                    # Handle edit operation
                    operation_data = message_data.get("operation", {})
                    operation = EditOperation(
                        **operation_data,
                        user_id=user.id,
                        timestamp=datetime.utcnow()
                    )
                    await collaboration_manager.handle_edit_operation(presentation_id, operation)
                
                elif message_type == "lock_slide":
                    # Lock slide for editing
                    slide_id = UUID(message_data.get("slide_id"))
                    success = await collaboration_manager.lock_slide(
                        presentation_id, slide_id, user.id, user.full_name
                    )
                    
                    await collaboration_manager.send_personal_message(connection_id, {
                        "type": "lock_response",
                        "slide_id": str(slide_id),
                        "success": success,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                elif message_type == "unlock_slide":
                    # Unlock slide
                    slide_id = UUID(message_data.get("slide_id"))
                    await collaboration_manager.unlock_slide(presentation_id, slide_id, user.id)
                
                elif message_type == "cursor_update":
                    # Real-time cursor position update
                    cursor_data = message_data.get("cursor", {})
                    await collaboration_manager.broadcast_to_presentation(presentation_id, {
                        "type": "cursor_update",
                        "user_id": str(user.id),
                        "cursor": cursor_data,
                        "timestamp": datetime.utcnow().isoformat()
                    }, exclude_user=user.id)
                
                else:
                    await collaboration_manager.send_personal_message(connection_id, {
                        "type": "error",
                        "message": f"Unknown message type: {message_type}",
                        "timestamp": datetime.utcnow().isoformat()
                    })
            
            except json.JSONDecodeError:
                await collaboration_manager.send_personal_message(connection_id, {
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.error(f"Error handling collaboration WebSocket message: {e}")
                await collaboration_manager.send_personal_message(connection_id, {
                    "type": "error",
                    "message": "Internal error processing message",
                    "timestamp": datetime.utcnow().isoformat()
                })
    
    except WebSocketDisconnect:
        logger.info(f"Collaboration WebSocket client disconnected: {connection_id}")
    except HTTPException as e:
        logger.warning(f"Collaboration WebSocket authentication failed: {e.detail}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    except Exception as e:
        logger.error(f"Collaboration WebSocket error: {e}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
    finally:
        await collaboration_manager.disconnect(connection_id)


@router.websocket("/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: str = Query(..., description="Authentication token")
):
    """
    WebSocket endpoint for real-time notifications and system messages.
    
    Provides system-wide notifications, user-specific alerts, and announcements.
    """
    connection_id = str(uuid4())
    
    try:
        # Authenticate user
        user = await get_current_user_websocket(token)
        
        # Connect to notification manager
        await notification_manager.connect(websocket, connection_id, user.id, {
            "type": "notifications"
        })
        
        # Auto-subscribe to user-specific and general channels
        await notification_manager.subscribe_to_channel(connection_id, "general")
        await notification_manager.subscribe_to_channel(connection_id, f"user_{user.id}")
        
        # Send welcome message
        await notification_manager.send_personal_message(connection_id, {
            "type": "connected",
            "message": "Connected to notification system",
            "subscribed_channels": ["general", f"user_{user.id}"],
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Handle incoming messages
        while True:
            try:
                message_text = await websocket.receive_text()
                message_data = json.loads(message_text)
                message_type = message_data.get("type")
                
                if message_type == "ping":
                    await notification_manager.send_personal_message(connection_id, {
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                elif message_type == "subscribe_channel":
                    # Subscribe to additional channel
                    channel = message_data.get("channel")
                    if channel:
                        await notification_manager.subscribe_to_channel(connection_id, channel)
                        await notification_manager.send_personal_message(connection_id, {
                            "type": "subscribed",
                            "channel": channel,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                
                elif message_type == "unsubscribe_channel":
                    # Unsubscribe from channel
                    channel = message_data.get("channel")
                    if channel and channel not in ["general", f"user_{user.id}"]:  # Can't unsubscribe from core channels
                        await notification_manager.unsubscribe_from_channel(connection_id, channel)
                        await notification_manager.send_personal_message(connection_id, {
                            "type": "unsubscribed",
                            "channel": channel,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                
                elif message_type == "mark_read":
                    # Mark notification as read (could be stored in database)
                    notification_id = message_data.get("notification_id")
                    # TODO: Implement notification read tracking
                    await notification_manager.send_personal_message(connection_id, {
                        "type": "marked_read",
                        "notification_id": notification_id,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                else:
                    await notification_manager.send_personal_message(connection_id, {
                        "type": "error",
                        "message": f"Unknown message type: {message_type}",
                        "timestamp": datetime.utcnow().isoformat()
                    })
            
            except json.JSONDecodeError:
                await notification_manager.send_personal_message(connection_id, {
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.error(f"Error handling notification WebSocket message: {e}")
                await notification_manager.send_personal_message(connection_id, {
                    "type": "error",
                    "message": "Internal error processing message",
                    "timestamp": datetime.utcnow().isoformat()
                })
    
    except WebSocketDisconnect:
        logger.info(f"Notification WebSocket client disconnected: {connection_id}")
    except HTTPException as e:
        logger.warning(f"Notification WebSocket authentication failed: {e.detail}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    except Exception as e:
        logger.error(f"Notification WebSocket error: {e}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
    finally:
        await notification_manager.disconnect(connection_id)


# Server-Sent Events (SSE) Endpoints for browser compatibility

@router.get("/sse/generation/{job_id}")
async def sse_generation_progress(
    request: Request,
    job_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """
    Server-Sent Events endpoint for generation progress updates.
    
    Provides progress updates using SSE for clients that can't use WebSocket.
    """
    async def event_stream():
        try:
            # Send initial connection event
            yield f"data: {json.dumps({'type': 'connected', 'job_id': str(job_id), 'timestamp': datetime.utcnow().isoformat()})}\n\n"
            
            # Check for job progress updates
            last_update = time.time()
            
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break
                
                # Get current job status
                if job_id in generation_manager.active_jobs:
                    job_data = generation_manager.active_jobs[job_id]
                    yield f"data: {json.dumps({'type': 'job_progress', 'job_id': str(job_id), 'data': job_data, 'timestamp': datetime.utcnow().isoformat()})}\n\n"
                    
                    # Stop if job is complete
                    if job_data.get("status") in ["completed", "failed", "cancelled"]:
                        break
                
                # Send keepalive every 30 seconds
                current_time = time.time()
                if current_time - last_update > 30:
                    yield f": keepalive\n\n"
                    last_update = current_time
                
                await asyncio.sleep(1)
        
        except Exception as e:
            logger.error(f"SSE generation stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e), 'timestamp': datetime.utcnow().isoformat()})}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )


@router.get("/sse/notifications")
async def sse_notifications(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Server-Sent Events endpoint for real-time notifications.
    
    Provides notifications using SSE for clients that can't use WebSocket.
    """
    async def event_stream():
        try:
            # Send initial connection event
            yield f"data: {json.dumps({'type': 'connected', 'message': 'Connected to notifications', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
            
            # Send recent notifications
            for notification in notification_manager.notification_history[-10:]:
                yield f"data: {json.dumps(notification)}\n\n"
            
            last_keepalive = time.time()
            
            # Keep connection alive and send new notifications
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break
                
                # Send keepalive every 30 seconds
                current_time = time.time()
                if current_time - last_keepalive > 30:
                    yield f": keepalive\n\n"
                    last_keepalive = current_time
                
                await asyncio.sleep(1)
        
        except Exception as e:
            logger.error(f"SSE notification stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e), 'timestamp': datetime.utcnow().isoformat()})}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )


# API endpoints for managing real-time features

@router.get("/stats")
async def get_realtime_stats(current_user: User = Depends(get_current_user)):
    """Get real-time system statistics."""
    return {
        "generation_manager": generation_manager.get_stats(),
        "collaboration_manager": collaboration_manager.get_stats(),
        "notification_manager": notification_manager.get_stats(),
        "active_presentations": len(collaboration_manager.presentation_sessions),
        "active_jobs": len(generation_manager.active_jobs),
        "total_edit_operations": sum(
            len(ops) for ops in collaboration_manager.edit_operations.values()
        ),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/notify")
async def send_notification_api(
    notification_type: str,
    title: str,
    message: str,
    channel: str = "general",
    user_id: Optional[UUID] = None,
    data: Dict[str, Any] = None,
    current_user: User = Depends(get_current_user)
):
    """Send notification via API (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    await notification_manager.send_notification(
        notification_type, title, message, data or {}, channel, user_id
    )
    
    return {"status": "notification_sent", "timestamp": datetime.utcnow().isoformat()}


# Utility functions for external service integration

async def broadcast_generation_progress(job_id: UUID, progress_data: Dict[str, Any]) -> None:
    """Utility function for external services to broadcast generation progress."""
    await generation_manager.update_job_progress(job_id, progress_data)


async def complete_generation_job(job_id: UUID, result_data: Dict[str, Any]) -> None:
    """Utility function to mark generation job as complete."""
    await generation_manager.complete_job(job_id, result_data)


async def send_user_notification(user_id: UUID, notification_type: str, title: str, message: str, data: Dict[str, Any] = None) -> None:
    """Utility function to send notification to specific user."""
    await notification_manager.send_notification(
        notification_type, title, message, data or {}, user_id=user_id
    )


async def broadcast_system_notification(notification_type: str, title: str, message: str, data: Dict[str, Any] = None) -> None:
    """Utility function to broadcast system-wide notification."""
    await notification_manager.send_notification(
        notification_type, title, message, data or {}, channel="general"
    )


# Background tasks for cleanup and maintenance

async def cleanup_stale_connections():
    """Background task to clean up stale connections."""
    while True:
        try:
            current_time = datetime.utcnow()
            
            # Clean up stale connections in all managers
            for manager in [generation_manager, collaboration_manager, notification_manager]:
                stale_connections = []
                
                for connection_id, metadata in manager.connection_metadata.items():
                    last_ping = metadata.get("last_ping", metadata.get("connected_at"))
                    if isinstance(last_ping, str):
                        last_ping = datetime.fromisoformat(last_ping)
                    
                    # Remove connections idle for more than 10 minutes
                    if current_time - last_ping > timedelta(minutes=10):
                        stale_connections.append(connection_id)
                
                for connection_id in stale_connections:
                    await manager.disconnect(connection_id)
                    logger.info(f"Cleaned up stale connection: {connection_id}")
            
            # Clean up expired slide locks
            for presentation_id, locks in collaboration_manager.presentation_locks.items():
                expired_locks = []
                for slide_id, lock_info in locks.items():
                    lock_time = datetime.fromisoformat(lock_info["locked_at"])
                    if current_time - lock_time > timedelta(minutes=5):
                        expired_locks.append(slide_id)
                
                for slide_id in expired_locks:
                    del locks[slide_id]
            
            await asyncio.sleep(60)  # Run every minute
        
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")
            await asyncio.sleep(60)


# Start background tasks
@router.on_event("startup")
async def start_background_tasks():
    """Start background maintenance tasks."""
    asyncio.create_task(cleanup_stale_connections())
    logger.info("Real-time system background tasks started")