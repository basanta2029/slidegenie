"""
Integration utilities for connecting real-time features with existing SlideGenie services.

This module provides integration points and examples for connecting the real-time
WebSocket/SSE system with generation, document processing, and other services.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.services.realtime_service import realtime_service

logger = logging.getLogger(__name__)


class GenerationProgressIntegration:
    """Integration for generation service with real-time progress updates."""
    
    @staticmethod
    async def on_job_started(job_id: UUID, user_id: UUID, job_type: str) -> None:
        """Called when a generation job starts."""
        await realtime_service.update_generation_progress(
            job_id=job_id,
            status="processing",
            progress=0.0,
            current_step="Initializing",
            message=f"Starting {job_type} generation"
        )
        
        # Send user notification
        await realtime_service.send_user_notification(
            user_id=user_id,
            notification_type="info",
            title="Generation Started",
            message="Your presentation generation has started.",
            data={"job_id": str(job_id), "job_type": job_type},
            category="generation"
        )

    @staticmethod
    async def on_parsing_progress(job_id: UUID, progress: float, message: str) -> None:
        """Called during document parsing phase."""
        await realtime_service.update_generation_progress(
            job_id=job_id,
            status="processing",
            progress=min(progress * 0.3, 0.3),  # Parsing is 30% of total
            current_step="Parsing Document",
            message=message
        )

    @staticmethod
    async def on_content_extraction(job_id: UUID, progress: float, extracted_elements: Dict[str, int]) -> None:
        """Called during content extraction phase."""
        element_summary = ", ".join([f"{count} {element_type}" for element_type, count in extracted_elements.items()])
        
        await realtime_service.update_generation_progress(
            job_id=job_id,
            status="processing",
            progress=0.3 + (progress * 0.3),  # Extraction is 30% of total (30-60%)
            current_step="Extracting Content",
            message=f"Extracted: {element_summary}"
        )

    @staticmethod
    async def on_slide_generation_start(job_id: UUID, total_slides: int) -> None:
        """Called when slide generation begins."""
        await realtime_service.update_generation_progress(
            job_id=job_id,
            status="processing",
            progress=0.6,
            current_step="Generating Slides",
            message=f"Generating {total_slides} slides"
        )

    @staticmethod
    async def on_slide_generated(job_id: UUID, slide_number: int, total_slides: int, slide_title: str) -> None:
        """Called when each slide is generated."""
        slide_progress = slide_number / total_slides
        total_progress = 0.6 + (slide_progress * 0.3)  # Slides are 30% of total (60-90%)
        
        await realtime_service.update_generation_progress(
            job_id=job_id,
            status="processing",
            progress=total_progress,
            current_step="Generating Slides",
            message=f"Generated slide {slide_number}/{total_slides}: {slide_title}"
        )

    @staticmethod
    async def on_finalization(job_id: UUID, message: str) -> None:
        """Called during finalization phase."""
        await realtime_service.update_generation_progress(
            job_id=job_id,
            status="processing",
            progress=0.95,
            current_step="Finalizing",
            message=message
        )

    @staticmethod
    async def on_job_completed(job_id: UUID, user_id: UUID, presentation_id: UUID, slide_count: int) -> None:
        """Called when generation job completes successfully."""
        result_data = {
            "presentation_id": str(presentation_id),
            "slide_count": slide_count,
            "completed_at": datetime.utcnow().isoformat()
        }
        
        await realtime_service.complete_generation_job(job_id, result_data, user_id)

    @staticmethod
    async def on_job_failed(job_id: UUID, user_id: UUID, error: str, error_details: Optional[Dict[str, Any]] = None) -> None:
        """Called when generation job fails."""
        await realtime_service.fail_generation_job(job_id, error, error_details, user_id)


class DocumentProcessingIntegration:
    """Integration for document processing with real-time updates."""
    
    @staticmethod
    async def on_upload_started(job_id: UUID, user_id: UUID, filename: str, file_size: int) -> None:
        """Called when document upload starts."""
        await realtime_service.send_user_notification(
            user_id=user_id,
            notification_type="info",
            title="Upload Started",
            message=f"Uploading {filename}",
            data={"job_id": str(job_id), "filename": filename, "file_size": file_size},
            category="upload"
        )

    @staticmethod
    async def on_upload_progress(job_id: UUID, user_id: UUID, progress: float, bytes_uploaded: int, total_bytes: int) -> None:
        """Called during upload progress."""
        # You could integrate this with a separate upload progress WebSocket if needed
        pass

    @staticmethod
    async def on_processing_started(job_id: UUID, user_id: UUID, filename: str) -> None:
        """Called when document processing starts."""
        await realtime_service.update_generation_progress(
            job_id=job_id,
            status="processing",
            progress=0.0,
            current_step="Processing Document",
            message=f"Processing {filename}"
        )

    @staticmethod
    async def on_security_scan_complete(job_id: UUID, scan_results: Dict[str, Any]) -> None:
        """Called when security scanning completes."""
        status = "clean" if scan_results.get("threats_found", 0) == 0 else "threats_detected"
        
        await realtime_service.update_generation_progress(
            job_id=job_id,
            status="processing",
            progress=0.1,
            current_step="Security Check",
            message=f"Security scan: {status}"
        )

    @staticmethod
    async def on_content_analysis_complete(job_id: UUID, analysis_results: Dict[str, Any]) -> None:
        """Called when content analysis completes."""
        content_type = analysis_results.get("content_type", "unknown")
        page_count = analysis_results.get("page_count", 0)
        
        await realtime_service.update_generation_progress(
            job_id=job_id,
            status="processing",
            progress=0.2,
            current_step="Content Analysis",
            message=f"Analyzed {content_type} document with {page_count} pages"
        )


class CollaborationIntegration:
    """Integration for collaboration features with presentations and slides."""
    
    @staticmethod
    async def on_presentation_created(presentation_id: UUID, owner_id: UUID, title: str) -> None:
        """Called when a new presentation is created."""
        await realtime_service.send_user_notification(
            user_id=owner_id,
            notification_type="success",
            title="Presentation Created",
            message=f"'{title}' has been created successfully.",
            data={"presentation_id": str(presentation_id)},
            category="presentation",
            action_url=f"/presentations/{presentation_id}",
            action_text="Open Presentation"
        )

    @staticmethod
    async def on_presentation_shared(presentation_id: UUID, presentation_title: str, shared_by: UUID, shared_with: List[UUID]) -> None:
        """Called when a presentation is shared with collaborators."""
        # Get user name (in real implementation, you'd fetch from user service)
        shared_by_name = "User"  # TODO: Get actual user name
        
        for user_id in shared_with:
            await realtime_service.send_user_notification(
                user_id=user_id,
                notification_type="info",
                title="Presentation Shared",
                message=f"'{presentation_title}' has been shared with you by {shared_by_name}.",
                data={
                    "presentation_id": str(presentation_id),
                    "shared_by": str(shared_by)
                },
                category="collaboration",
                action_url=f"/presentations/{presentation_id}",
                action_text="View Presentation"
            )

    @staticmethod
    async def on_slide_updated(presentation_id: UUID, slide_number: int, updated_by: UUID, collaborators: List[UUID]) -> None:
        """Called when a slide is updated during collaboration."""
        # This would be handled through the real-time edit operations
        # But we can also send notifications for major updates
        pass

    @staticmethod
    async def on_comment_added(presentation_id: UUID, slide_number: int, comment: str, author_id: UUID, collaborators: List[UUID]) -> None:
        """Called when a comment is added to a slide."""
        author_name = "User"  # TODO: Get actual user name
        
        for user_id in collaborators:
            if user_id != author_id:  # Don't notify the author
                await realtime_service.send_user_notification(
                    user_id=user_id,
                    notification_type="info",
                    title="New Comment",
                    message=f"{author_name} commented on slide {slide_number}",
                    data={
                        "presentation_id": str(presentation_id),
                        "slide_number": slide_number,
                        "comment": comment[:100] + "..." if len(comment) > 100 else comment,
                        "author_id": str(author_id)
                    },
                    category="collaboration",
                    action_url=f"/presentations/{presentation_id}/slides/{slide_number}",
                    action_text="View Comment"
                )


class ExportIntegration:
    """Integration for export service with real-time progress updates."""
    
    @staticmethod
    async def on_export_started(export_id: UUID, user_id: UUID, presentation_id: UUID, format: str) -> None:
        """Called when export starts."""
        await realtime_service.send_user_notification(
            user_id=user_id,
            notification_type="info",
            title="Export Started",
            message=f"Exporting presentation to {format.upper()}",
            data={
                "export_id": str(export_id),
                "presentation_id": str(presentation_id),
                "format": format
            },
            category="export"
        )

    @staticmethod
    async def on_export_progress(export_id: UUID, progress: float, message: str) -> None:
        """Called during export progress."""
        # Could use the generation progress system for exports too
        pass

    @staticmethod
    async def on_export_completed(export_id: UUID, user_id: UUID, download_url: str, file_size: int) -> None:
        """Called when export completes."""
        await realtime_service.send_user_notification(
            user_id=user_id,
            notification_type="success",
            title="Export Complete",
            message="Your export is ready for download",
            data={
                "export_id": str(export_id),
                "download_url": download_url,
                "file_size": file_size
            },
            category="export",
            action_url=download_url,
            action_text="Download"
        )

    @staticmethod
    async def on_export_failed(export_id: UUID, user_id: UUID, error: str) -> None:
        """Called when export fails."""
        await realtime_service.send_user_notification(
            user_id=user_id,
            notification_type="error",
            title="Export Failed",
            message=f"Export failed: {error}",
            data={"export_id": str(export_id), "error": error},
            category="export"
        )


class SystemIntegration:
    """Integration for system-wide events and maintenance."""
    
    @staticmethod
    async def on_maintenance_scheduled(start_time: datetime, duration_minutes: int, message: str) -> None:
        """Called when maintenance is scheduled."""
        await realtime_service.broadcast_notification(
            notification_type="warning",
            title="Scheduled Maintenance",
            message=f"System maintenance scheduled for {start_time.strftime('%Y-%m-%d %H:%M')} UTC ({duration_minutes} minutes). {message}",
            data={
                "start_time": start_time.isoformat(),
                "duration_minutes": duration_minutes
            },
            channel="system",
            priority="high",
            category="maintenance"
        )

    @staticmethod
    async def on_system_error(error_type: str, error_message: str, affected_users: Optional[List[UUID]] = None) -> None:
        """Called when system errors occur."""
        if affected_users:
            # Send to specific users
            for user_id in affected_users:
                await realtime_service.send_user_notification(
                    user_id=user_id,
                    notification_type="error",
                    title="System Error",
                    message=f"A system error occurred: {error_message}",
                    data={"error_type": error_type},
                    category="system",
                    priority="high"
                )
        else:
            # Broadcast to all users
            await realtime_service.broadcast_notification(
                notification_type="error",
                title="System Error",
                message=f"A system error occurred: {error_message}",
                data={"error_type": error_type},
                channel="system",
                priority="high",
                category="system"
            )

    @staticmethod
    async def on_feature_announcement(title: str, message: str, feature_url: Optional[str] = None) -> None:
        """Called when announcing new features."""
        await realtime_service.broadcast_notification(
            notification_type="info",
            title=title,
            message=message,
            data={"feature_url": feature_url} if feature_url else {},
            channel="announcements",
            category="feature",
            action_url=feature_url,
            action_text="Learn More" if feature_url else None
        )


# Utility functions to register integration handlers

async def setup_integrations():
    """Set up all integration handlers with the real-time service."""
    try:
        await realtime_service.initialize()
        
        # Register generation progress handlers
        async def generation_handler(job_id: UUID, progress_data: Dict[str, Any]):
            logger.info(f"Generation progress for job {job_id}: {progress_data}")
        
        realtime_service.register_generation_handler(generation_handler)
        
        # Register collaboration handlers  
        async def collaboration_handler(event_type: str, event_data: Dict[str, Any]):
            logger.info(f"Collaboration event {event_type}: {event_data}")
        
        realtime_service.register_collaboration_handler(collaboration_handler)
        
        # Register notification handlers
        async def notification_handler(notification_data: Dict[str, Any]):
            logger.info(f"Notification sent: {notification_data}")
        
        realtime_service.register_notification_handler(notification_handler)
        
        logger.info("Real-time integrations set up successfully")
        
    except Exception as e:
        logger.error(f"Failed to set up real-time integrations: {e}")
        raise


# Example usage functions for testing and demonstration

async def demo_generation_flow(job_id: UUID, user_id: UUID):
    """Demonstrate a complete generation flow with real-time updates."""
    integration = GenerationProgressIntegration()
    
    # Start job
    await integration.on_job_started(job_id, user_id, "presentation")
    await asyncio.sleep(1)
    
    # Parsing phase
    await integration.on_parsing_progress(job_id, 0.5, "Parsing document structure")
    await asyncio.sleep(1)
    await integration.on_parsing_progress(job_id, 1.0, "Document parsing complete")
    await asyncio.sleep(1)
    
    # Content extraction
    await integration.on_content_extraction(job_id, 0.3, {"text_blocks": 15, "images": 3, "tables": 2})
    await asyncio.sleep(1)
    await integration.on_content_extraction(job_id, 1.0, {"text_blocks": 25, "images": 5, "tables": 3})
    await asyncio.sleep(1)
    
    # Slide generation
    await integration.on_slide_generation_start(job_id, 12)
    await asyncio.sleep(1)
    
    for i in range(1, 13):
        await integration.on_slide_generated(job_id, i, 12, f"Slide {i} Title")
        await asyncio.sleep(0.5)
    
    # Finalization
    await integration.on_finalization(job_id, "Applying formatting and styles")
    await asyncio.sleep(1)
    
    # Completion
    presentation_id = UUID("12345678-1234-1234-1234-123456789012")
    await integration.on_job_completed(job_id, user_id, presentation_id, 12)


async def demo_collaboration_flow(presentation_id: UUID, user1_id: UUID, user2_id: UUID):
    """Demonstrate collaboration features."""
    integration = CollaborationIntegration()
    
    # Create presentation
    await integration.on_presentation_created(presentation_id, user1_id, "Demo Presentation")
    await asyncio.sleep(1)
    
    # Share with collaborator
    await integration.on_presentation_shared(presentation_id, "Demo Presentation", user1_id, [user2_id])
    await asyncio.sleep(1)
    
    # Add comment
    await integration.on_comment_added(presentation_id, 3, "This slide needs more details", user2_id, [user1_id])


# Export integration functions for use by other services

def get_generation_integration() -> GenerationProgressIntegration:
    """Get generation integration instance."""
    return GenerationProgressIntegration()


def get_document_processing_integration() -> DocumentProcessingIntegration:
    """Get document processing integration instance."""
    return DocumentProcessingIntegration()


def get_collaboration_integration() -> CollaborationIntegration:
    """Get collaboration integration instance."""
    return CollaborationIntegration()


def get_export_integration() -> ExportIntegration:
    """Get export integration instance."""
    return ExportIntegration()


def get_system_integration() -> SystemIntegration:
    """Get system integration instance."""
    return SystemIntegration()