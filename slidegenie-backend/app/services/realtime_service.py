"""
Real-time service for integrating WebSocket and SSE functionality with existing services.

This service provides a bridge between the real-time components and the rest of the application,
handling events, notifications, and coordination between different systems.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.domain.schemas.realtime import (
    EditOperation,
    GenerationProgressUpdate,
    Notification,
    UserPresence,
)

logger = logging.getLogger(__name__)


class RealtimeService:
    """
    Service for managing real-time features and integration with existing systems.
    
    This service acts as a coordination layer between real-time managers and
    the rest of the application, ensuring consistent state and proper event handling.
    """
    
    def __init__(self):
        self.generation_manager = None
        self.collaboration_manager = None
        self.notification_manager = None
        self._initialized = False
        
        # Event handlers
        self._generation_handlers: List[callable] = []
        self._collaboration_handlers: List[callable] = []
        self._notification_handlers: List[callable] = []

    async def initialize(self):
        """Initialize the real-time service and its dependencies."""
        if self._initialized:
            return
        
        try:
            # Import managers here to avoid circular imports
            from app.api.v1.endpoints.realtime import (
                generation_manager,
                collaboration_manager,
                notification_manager
            )
            
            self.generation_manager = generation_manager
            self.collaboration_manager = collaboration_manager
            self.notification_manager = notification_manager
            
            self._initialized = True
            logger.info("Real-time service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize real-time service: {e}")
            raise

    def ensure_initialized(self):
        """Ensure the service is initialized."""
        if not self._initialized:
            raise RuntimeError("RealtimeService not initialized. Call initialize() first.")

    # Generation Progress Methods

    async def update_generation_progress(
        self,
        job_id: UUID,
        status: str,
        progress: float,
        current_step: str,
        message: Optional[str] = None,
        estimated_completion: Optional[datetime] = None,
        error_message: Optional[str] = None,
        result_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update generation job progress and broadcast to subscribers."""
        self.ensure_initialized()
        
        progress_data = {
            "status": status,
            "progress": progress,
            "current_step": current_step,
            "message": message,
            "estimated_completion": estimated_completion.isoformat() if estimated_completion else None,
            "error_message": error_message,
            "result_data": result_data,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        await self.generation_manager.update_job_progress(job_id, progress_data)
        
        # Call registered handlers
        for handler in self._generation_handlers:
            try:
                await handler(job_id, progress_data)
            except Exception as e:
                logger.error(f"Error in generation progress handler: {e}")

    async def complete_generation_job(
        self,
        job_id: UUID,
        result_data: Dict[str, Any],
        user_id: Optional[UUID] = None
    ) -> None:
        """Mark generation job as complete and send notifications."""
        self.ensure_initialized()
        
        await self.generation_manager.complete_job(job_id, result_data)
        
        # Send completion notification
        if user_id:
            await self.send_user_notification(
                user_id=user_id,
                notification_type="success",
                title="Generation Complete",
                message=f"Your presentation has been successfully generated.",
                data={"job_id": str(job_id), **result_data}
            )

    async def fail_generation_job(
        self,
        job_id: UUID,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None,
        user_id: Optional[UUID] = None
    ) -> None:
        """Mark generation job as failed and send error notification."""
        self.ensure_initialized()
        
        await self.update_generation_progress(
            job_id=job_id,
            status="failed",
            progress=0.0,
            current_step="Failed",
            error_message=error_message,
            result_data=error_details
        )
        
        # Send error notification
        if user_id:
            await self.send_user_notification(
                user_id=user_id,
                notification_type="error",
                title="Generation Failed",
                message=f"Generation failed: {error_message}",
                data={"job_id": str(job_id), "error": error_message}
            )

    # Collaboration Methods

    async def handle_user_join_presentation(
        self,
        presentation_id: UUID,
        user_id: UUID,
        user_name: str,
        email: str
    ) -> None:
        """Handle user joining a presentation for collaboration."""
        self.ensure_initialized()
        
        # This would be called by the WebSocket handler
        # The actual joining is handled in the collaboration manager
        
        # Call registered handlers
        for handler in self._collaboration_handlers:
            try:
                await handler("user_joined", {
                    "presentation_id": presentation_id,
                    "user_id": user_id,
                    "user_name": user_name,
                    "email": email
                })
            except Exception as e:
                logger.error(f"Error in collaboration handler: {e}")

    async def handle_edit_operation(
        self,
        presentation_id: UUID,
        operation: EditOperation
    ) -> bool:
        """
        Handle edit operation and resolve conflicts.
        
        Returns:
            bool: True if operation was applied successfully, False if conflicts occurred
        """
        self.ensure_initialized()
        
        # Check for conflicts with recent operations
        conflicts = await self._check_edit_conflicts(presentation_id, operation)
        
        if conflicts:
            # Handle conflicts - for now, we'll reject conflicting operations
            logger.warning(f"Edit operation {operation.operation_id} has conflicts: {conflicts}")
            operation.applied = False
            operation.conflicts = conflicts
        else:
            operation.applied = True
        
        # Broadcast the operation (whether successful or conflicted)
        await self.collaboration_manager.handle_edit_operation(presentation_id, operation)
        
        return operation.applied

    async def _check_edit_conflicts(
        self,
        presentation_id: UUID,
        operation: EditOperation
    ) -> List[str]:
        """Check for conflicts with recent edit operations."""
        conflicts = []
        
        if presentation_id not in self.collaboration_manager.edit_operations:
            return conflicts
        
        recent_operations = self.collaboration_manager.edit_operations[presentation_id]
        
        # Check for conflicts in the last 10 seconds
        cutoff_time = datetime.utcnow() - timedelta(seconds=10)
        
        for recent_op in recent_operations:
            if recent_op.timestamp < cutoff_time:
                continue
            
            if recent_op.user_id == operation.user_id:
                continue  # Skip own operations
            
            # Check for same element conflicts
            if (recent_op.slide_id == operation.slide_id and 
                recent_op.element_id == operation.element_id):
                conflicts.append(f"Concurrent edit on same element by {recent_op.user_name}")
            
            # Check for overlapping position conflicts
            if (recent_op.slide_id == operation.slide_id and
                operation.position and recent_op.position):
                if self._positions_overlap(recent_op.position, operation.position):
                    conflicts.append(f"Overlapping edit position with {recent_op.user_name}")
        
        return conflicts

    def _positions_overlap(self, pos1: Dict[str, Any], pos2: Dict[str, Any]) -> bool:
        """Check if two edit positions overlap."""
        # Simple overlap detection - can be made more sophisticated
        try:
            if "line" in pos1 and "line" in pos2:
                return abs(pos1["line"] - pos2["line"]) <= 1
            
            if "x" in pos1 and "x" in pos2 and "y" in pos1 and "y" in pos2:
                distance = ((pos1["x"] - pos2["x"]) ** 2 + (pos1["y"] - pos2["y"]) ** 2) ** 0.5
                return distance < 50  # Within 50 pixels
            
            return False
        except (KeyError, TypeError):
            return False

    async def update_user_presence(
        self,
        presentation_id: UUID,
        user_id: UUID,
        status: str,
        current_slide: Optional[int] = None,
        cursor_position: Optional[Dict[str, Any]] = None,
        active_section: Optional[str] = None
    ) -> None:
        """Update user presence information."""
        self.ensure_initialized()
        
        await self.collaboration_manager.update_user_presence(
            presentation_id, user_id, status, current_slide, cursor_position
        )

    async def lock_slide_for_editing(
        self,
        presentation_id: UUID,
        slide_id: UUID,
        user_id: UUID,
        user_name: str
    ) -> bool:
        """
        Lock a slide for editing to prevent conflicts.
        
        Returns:
            bool: True if lock was acquired, False if slide is already locked
        """
        self.ensure_initialized()
        
        return await self.collaboration_manager.lock_slide(
            presentation_id, slide_id, user_id, user_name
        )

    async def unlock_slide(
        self,
        presentation_id: UUID,
        slide_id: UUID,
        user_id: UUID
    ) -> None:
        """Unlock a slide."""
        self.ensure_initialized()
        
        await self.collaboration_manager.unlock_slide(presentation_id, slide_id, user_id)

    # Notification Methods

    async def send_user_notification(
        self,
        user_id: UUID,
        notification_type: str,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        priority: str = "normal",
        category: str = "general",
        action_url: Optional[str] = None,
        action_text: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> None:
        """Send notification to a specific user."""
        self.ensure_initialized()
        
        await self.notification_manager.send_notification(
            notification_type=notification_type,
            title=title,
            message=message,
            data=data or {},
            user_id=user_id
        )

    async def broadcast_notification(
        self,
        notification_type: str,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        channel: str = "general",
        priority: str = "normal",
        category: str = "general"
    ) -> None:
        """Broadcast notification to all users in a channel."""
        self.ensure_initialized()
        
        await self.notification_manager.send_notification(
            notification_type=notification_type,
            title=title,
            message=message,
            data=data or {},
            channel=channel
        )

    async def send_presentation_update_notification(
        self,
        presentation_id: UUID,
        presentation_title: str,
        update_type: str,
        updated_by: str,
        collaborators: List[UUID]
    ) -> None:
        """Send notification about presentation updates to collaborators."""
        self.ensure_initialized()
        
        message = f"'{presentation_title}' was {update_type} by {updated_by}"
        
        for user_id in collaborators:
            await self.send_user_notification(
                user_id=user_id,
                notification_type="info",
                title="Presentation Updated",
                message=message,
                data={
                    "presentation_id": str(presentation_id),
                    "update_type": update_type,
                    "updated_by": updated_by
                },
                category="collaboration",
                action_url=f"/presentations/{presentation_id}",
                action_text="View Presentation"
            )

    # Event Handler Registration

    def register_generation_handler(self, handler: callable) -> None:
        """Register a handler for generation progress events."""
        self._generation_handlers.append(handler)

    def register_collaboration_handler(self, handler: callable) -> None:
        """Register a handler for collaboration events."""
        self._collaboration_handlers.append(handler)

    def register_notification_handler(self, handler: callable) -> None:
        """Register a handler for notification events."""
        self._notification_handlers.append(handler)

    # System Health and Monitoring

    async def get_system_health(self) -> Dict[str, Any]:
        """Get real-time system health information."""
        self.ensure_initialized()
        
        generation_stats = self.generation_manager.get_stats()
        collaboration_stats = self.collaboration_manager.get_stats()
        notification_stats = self.notification_manager.get_stats()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "generation_manager": {
                **generation_stats,
                "active_jobs": len(self.generation_manager.active_jobs),
                "job_subscribers": len(self.generation_manager.job_subscribers)
            },
            "collaboration_manager": {
                **collaboration_stats,
                "active_presentations": len(self.collaboration_manager.presentation_sessions),
                "active_users_in_presentations": sum(
                    len(users) for users in self.collaboration_manager.user_presence.values()
                ),
                "locked_slides": sum(
                    len(locks) for locks in self.collaboration_manager.presentation_locks.values()
                )
            },
            "notification_manager": {
                **notification_stats,
                "channels": len(self.notification_manager.channel_subscriptions),
                "notification_history_size": len(self.notification_manager.notification_history)
            }
        }

    async def cleanup_stale_data(self) -> Dict[str, int]:
        """Clean up stale data and return cleanup statistics."""
        self.ensure_initialized()
        
        cleanup_stats = {
            "expired_locks": 0,
            "old_operations": 0,
            "stale_presence": 0
        }
        
        current_time = datetime.utcnow()
        
        # Clean up expired slide locks
        for presentation_id, locks in self.collaboration_manager.presentation_locks.items():
            expired_slides = []
            for slide_id, lock_info in locks.items():
                lock_time = datetime.fromisoformat(lock_info["locked_at"])
                if current_time - lock_time > timedelta(minutes=5):
                    expired_slides.append(slide_id)
            
            for slide_id in expired_slides:
                del locks[slide_id]
                cleanup_stats["expired_locks"] += 1
        
        # Clean up old edit operations (keep only last 24 hours)
        cutoff_time = current_time - timedelta(hours=24)
        for presentation_id, operations in self.collaboration_manager.edit_operations.items():
            initial_count = len(operations)
            self.collaboration_manager.edit_operations[presentation_id] = [
                op for op in operations if op.timestamp >= cutoff_time
            ]
            cleanup_stats["old_operations"] += initial_count - len(self.collaboration_manager.edit_operations[presentation_id])
        
        # Clean up stale user presence (users inactive for more than 1 hour)
        presence_cutoff = current_time - timedelta(hours=1)
        for presentation_id, users in self.collaboration_manager.user_presence.items():
            stale_users = []
            for user_id, presence in users.items():
                if presence.last_seen < presence_cutoff:
                    stale_users.append(user_id)
            
            for user_id in stale_users:
                del users[user_id]
                cleanup_stats["stale_presence"] += 1
        
        logger.info(f"Cleanup completed: {cleanup_stats}")
        return cleanup_stats


# Global service instance
realtime_service = RealtimeService()


# Utility functions for external service integration

async def notify_generation_progress(
    job_id: UUID,
    status: str,
    progress: float,
    current_step: str,
    message: Optional[str] = None,
    user_id: Optional[UUID] = None
) -> None:
    """Utility function to notify generation progress from external services."""
    await realtime_service.update_generation_progress(
        job_id, status, progress, current_step, message
    )


async def notify_generation_complete(
    job_id: UUID,
    result_data: Dict[str, Any],
    user_id: Optional[UUID] = None
) -> None:
    """Utility function to notify generation completion from external services."""
    await realtime_service.complete_generation_job(job_id, result_data, user_id)


async def notify_generation_failed(
    job_id: UUID,
    error_message: str,
    error_details: Optional[Dict[str, Any]] = None,
    user_id: Optional[UUID] = None
) -> None:
    """Utility function to notify generation failure from external services."""
    await realtime_service.fail_generation_job(job_id, error_message, error_details, user_id)


async def send_notification_to_user(
    user_id: UUID,
    notification_type: str,
    title: str,
    message: str,
    data: Optional[Dict[str, Any]] = None
) -> None:
    """Utility function to send notification to user from external services."""
    await realtime_service.send_user_notification(
        user_id, notification_type, title, message, data
    )


async def broadcast_system_notification(
    notification_type: str,
    title: str,
    message: str,
    data: Optional[Dict[str, Any]] = None
) -> None:
    """Utility function to broadcast system notification from external services."""
    await realtime_service.broadcast_notification(
        notification_type, title, message, data
    )