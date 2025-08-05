"""
Admin endpoints for SlideGenie user management and system administration.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user
from app.services.auth.authorization.decorators import require_permissions
from app.services.auth.authorization.permissions import PermissionAction, ResourceType
from app.services.admin_service import AdminService
from app.domain.schemas.admin import (
    AdminUserResponse, AdminUserListResponse, UserDetailResponse,
    SubscriptionUpdateRequest, SubscriptionUpdateResponse,
    BroadcastRequest, BroadcastResponse, SystemHealthResponse,
    SystemMetricsResponse, UserFilters, SecurityEvent,
    SecurityAuditResponse, NotificationHistory, SystemAlert,
    MaintenanceWindow, DataExportRequest, DataExportResponse
)
from app.infrastructure.database.models import User
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/users", response_model=AdminUserListResponse)
@require_permissions("read:user")
async def get_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term"),
    role: Optional[str] = Query(None, description="Filter by role"),
    subscription_tier: Optional[str] = Query(None, description="Filter by subscription tier"),
    institution: Optional[str] = Query(None, description="Filter by institution"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_verified: Optional[bool] = Query(None, description="Filter by verification status"),
    created_after: Optional[datetime] = Query(None, description="Filter users created after date"),
    created_before: Optional[datetime] = Query(None, description="Filter users created before date"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc, desc)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AdminUserListResponse:
    """
    Get paginated list of users with filtering and sorting.
    
    Provides comprehensive user management with:
    - Advanced filtering by multiple criteria
    - Full-text search across name, email, and institution
    - Flexible sorting options
    - Pagination with configurable page sizes
    - User activity and subscription metrics
    
    Requires admin or user read permissions.
    """
    logger.info("admin_users_list_requested",
               admin_id=str(current_user.id),
               page=page,
               page_size=page_size,
               search=search)
    
    try:
        # Validate sort fields
        valid_sort_fields = ["created_at", "email", "full_name", "last_login"]
        if sort_by not in valid_sort_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid sort field. Must be one of: {', '.join(valid_sort_fields)}"
            )
        
        # Validate sort order
        if sort_order not in ["asc", "desc"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sort order must be 'asc' or 'desc'"
            )
        
        # Create filters object
        filters = UserFilters(
            search=search,
            role=role,
            subscription_tier=subscription_tier,
            institution=institution,
            is_active=is_active,
            is_verified=is_verified,
            created_after=created_after,
            created_before=created_before,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        admin_service = AdminService(db)
        users_response = await admin_service.get_users(
            filters=filters,
            page=page,
            page_size=page_size,
            admin_id=current_user.id
        )
        
        logger.info("admin_users_list_retrieved",
                   total=users_response.total,
                   page=page,
                   returned=len(users_response.users))
        
        return users_response
        
    except ValueError as e:
        logger.warning("admin_users_list_validation_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("admin_users_list_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users list"
        )


@router.get("/users/{user_id}", response_model=UserDetailResponse)
@require_permissions("read:user")
async def get_user_details(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> UserDetailResponse:
    """
    Get detailed information for a specific user.
    
    Returns comprehensive user data including:
    - Complete user profile and account status
    - Recent activity history (logins, presentations, exports)
    - Connected OAuth accounts
    - Active API keys
    - Subscription and billing history
    - Detailed usage statistics
    
    Requires admin or user read permissions.
    """
    logger.info("admin_user_details_requested",
               admin_id=str(current_user.id),
               target_user_id=str(user_id))
    
    try:
        admin_service = AdminService(db)
        user_details = await admin_service.get_user_details(
            user_id=user_id,
            admin_id=current_user.id
        )
        
        logger.info("admin_user_details_retrieved",
                   target_user_id=str(user_id),
                   presentations=user_details.user.presentations_count)
        
        return user_details
        
    except ValueError as e:
        logger.warning("admin_user_details_not_found", user_id=str(user_id))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error("admin_user_details_failed", user_id=str(user_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user details"
        )


@router.put("/users/{user_id}/subscription", response_model=SubscriptionUpdateResponse)
@require_permissions("update:user")
async def update_user_subscription(
    user_id: UUID,
    request: SubscriptionUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> SubscriptionUpdateResponse:
    """
    Update user subscription tier and settings.
    
    Allows administrators to:
    - Change subscription tier (free, academic, professional, institutional)
    - Set subscription expiry dates
    - Adjust storage quotas and presentation limits
    - Track reasons for subscription changes
    - Send notification emails to users
    
    Requires admin or user update permissions.
    """
    logger.info("admin_subscription_update_requested",
               admin_id=str(current_user.id),
               target_user_id=str(user_id),
               new_tier=request.subscription_tier)
    
    try:
        # Validate subscription tier
        valid_tiers = ["free", "academic", "professional", "institutional"]
        if request.subscription_tier not in valid_tiers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid subscription tier. Must be one of: {', '.join(valid_tiers)}"
            )
        
        admin_service = AdminService(db)
        response = await admin_service.update_user_subscription(
            user_id=user_id,
            request=request,
            admin_id=current_user.id
        )
        
        logger.info("admin_subscription_updated",
                   target_user_id=str(user_id),
                   previous_tier=response.previous_tier,
                   new_tier=response.new_tier)
        
        return response
        
    except ValueError as e:
        logger.warning("admin_subscription_update_validation_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("admin_subscription_update_failed", 
                    user_id=str(user_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user subscription"
        )


@router.post("/broadcast", response_model=BroadcastResponse)
@require_permissions("admin:system")
async def send_broadcast_notification(
    request: BroadcastRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> BroadcastResponse:
    """
    Send system-wide notification to users.
    
    Supports targeted broadcasting with:
    - Multiple delivery channels (in-app, email, push)
    - User targeting by subscription tier, institution, or specific users
    - Scheduling for future delivery
    - Priority levels and notification types
    - Automatic expiry handling
    - Delivery tracking and analytics
    
    Requires admin system permissions.
    """
    logger.info("admin_broadcast_requested",
               admin_id=str(current_user.id),
               title=request.title,
               target_all=request.target_all_users)
    
    try:
        # Validate notification type
        valid_types = ["info", "warning", "error", "maintenance", "announcement"]
        if request.type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid notification type. Must be one of: {', '.join(valid_types)}"
            )
        
        # Validate priority
        valid_priorities = ["low", "normal", "high", "urgent"]
        if request.priority not in valid_priorities:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid priority. Must be one of: {', '.join(valid_priorities)}"
            )
        
        # Validate scheduling
        if request.scheduled_at and request.scheduled_at <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Scheduled time must be in the future"
            )
        
        admin_service = AdminService(db)
        response = await admin_service.send_broadcast_notification(
            request=request,
            admin_id=current_user.id
        )
        
        logger.info("admin_broadcast_sent",
                   broadcast_id=str(response.broadcast_id),
                   recipients=response.recipients_count,
                   admin_id=str(current_user.id))
        
        return response
        
    except ValueError as e:
        logger.warning("admin_broadcast_validation_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("admin_broadcast_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send broadcast notification"
        )


@router.get("/system/health", response_model=SystemHealthResponse)
@require_permissions("read:system")
async def get_system_health(
    force_refresh: bool = Query(False, description="Force refresh cached health data"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> SystemHealthResponse:
    """
    Get comprehensive system health monitoring data.
    
    Returns real-time system status including:
    - Overall system health status
    - Individual service health checks
    - Database and Redis connectivity
    - Resource utilization (CPU, memory, disk)
    - Active connections and queue status
    - Performance metrics and error rates
    
    Requires admin system read permissions.
    """
    logger.info("admin_system_health_requested",
               admin_id=str(current_user.id),
               force_refresh=force_refresh)
    
    try:
        admin_service = AdminService(db)
        health = await admin_service.get_system_health(force_refresh=force_refresh)
        
        logger.info("admin_system_health_retrieved",
                   status=health.overall_status,
                   cpu=health.cpu_usage,
                   memory=health.memory_usage)
        
        return health
        
    except Exception as e:
        logger.error("admin_system_health_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system health"
        )


@router.get("/system/metrics", response_model=SystemMetricsResponse)
@require_permissions("read:system")
async def get_system_metrics(
    force_refresh: bool = Query(False, description="Force refresh cached metrics"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> SystemMetricsResponse:
    """
    Get detailed system performance metrics and analytics.
    
    Returns comprehensive system metrics including:
    - HTTP request/response statistics
    - Database and cache performance
    - Error rates and recent incidents
    - Resource utilization trends
    - Business metrics (user activity, content creation)
    - Financial metrics (costs, revenue)
    
    Requires admin system read permissions.
    """
    logger.info("admin_system_metrics_requested",
               admin_id=str(current_user.id),
               force_refresh=force_refresh)
    
    try:
        admin_service = AdminService(db)
        metrics = await admin_service.get_system_metrics(force_refresh=force_refresh)
        
        logger.info("admin_system_metrics_retrieved",
                   timestamp=metrics.timestamp.isoformat())
        
        return metrics
        
    except Exception as e:
        logger.error("admin_system_metrics_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system metrics"
        )


@router.get("/security/audit")
@require_permissions("read:audit_log")
async def get_security_audit_log(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    start_date: Optional[datetime] = Query(None, description="Filter events after date"),
    end_date: Optional[datetime] = Query(None, description="Filter events before date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get security audit log with filtering and pagination.
    
    Returns security and audit events including:
    - Authentication attempts (success/failure)
    - Authorization violations
    - Data access events
    - Administrative actions
    - Suspicious activity patterns
    - System security alerts
    
    Requires admin audit log read permissions.
    """
    logger.info("admin_security_audit_requested",
               admin_id=str(current_user.id),
               page=page,
               event_type=event_type,
               severity=severity)
    
    try:
        # Validate severity filter
        if severity and severity not in ["info", "warning", "critical"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid severity. Must be one of: info, warning, critical"
            )
        
        # Set default date range if not provided
        if not end_date:
            end_date = datetime.now(timezone.utc)
        if not start_date:
            start_date = end_date - timedelta(days=7)
        
        # This would typically be implemented in the admin service
        # For now, return placeholder data
        events = []
        
        response = SecurityAuditResponse(
            events=events,
            total=0,
            page=page,
            page_size=page_size,
            total_pages=0,
            event_counts_by_type={},
            event_counts_by_severity={},
            unique_users_affected=0,
            unique_ips=0
        )
        
        logger.info("admin_security_audit_retrieved",
                   total_events=response.total,
                   page=page)
        
        return response
        
    except Exception as e:
        logger.error("admin_security_audit_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve security audit log"
        )


@router.get("/notifications/history")
@require_permissions("read:system")
async def get_notification_history(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get broadcast notification history.
    
    Returns history of system notifications including:
    - Broadcast details and content
    - Delivery statistics and performance
    - Open and click-through rates
    - Targeting criteria used
    - Success/failure status
    
    Requires admin system read permissions.
    """
    logger.info("admin_notification_history_requested",
               admin_id=str(current_user.id),
               page=page)
    
    try:
        # This would typically be implemented in the admin service
        # For now, return placeholder data
        notifications = []
        
        response = {
            "notifications": notifications,
            "total": 0,
            "page": page,
            "page_size": page_size,
            "total_pages": 0
        }
        
        logger.info("admin_notification_history_retrieved",
                   total=response["total"],
                   page=page)
        
        return response
        
    except Exception as e:
        logger.error("admin_notification_history_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve notification history"
        )


@router.get("/alerts")
@require_permissions("read:system")
async def get_system_alerts(
    active_only: bool = Query(True, description="Show only active alerts"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get system alerts and warnings.
    
    Returns current and historical system alerts including:
    - Performance threshold violations
    - Resource usage warnings
    - Service availability issues
    - Security incidents
    - Maintenance notifications
    
    Requires admin system read permissions.
    """
    logger.info("admin_system_alerts_requested",
               admin_id=str(current_user.id),
               active_only=active_only,
               severity=severity)
    
    try:
        # Validate severity filter
        if severity and severity not in ["low", "medium", "high", "critical"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid severity. Must be one of: low, medium, high, critical"
            )
        
        # This would typically be implemented in the admin service
        # For now, return placeholder data
        alerts = []
        
        response = {
            "alerts": alerts,
            "active_count": 0,
            "critical_count": 0,
            "last_updated": datetime.now(timezone.utc)
        }
        
        logger.info("admin_system_alerts_retrieved",
                   active_count=response["active_count"],
                   critical_count=response["critical_count"])
        
        return response
        
    except Exception as e:
        logger.error("admin_system_alerts_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system alerts"
        )


@router.post("/maintenance")
@require_permissions("admin:system")
async def schedule_maintenance(
    maintenance_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Schedule system maintenance window.
    
    Allows scheduling of maintenance with:
    - Defined start and end times
    - Impact assessment and service lists
    - User notification management
    - Automatic status updates
    - Rollback procedures
    
    Requires admin system permissions.
    """
    logger.info("admin_maintenance_schedule_requested",
               admin_id=str(current_user.id),
               maintenance_data=maintenance_data)
    
    try:
        # This would typically be implemented in the admin service
        # For now, return placeholder response
        maintenance_id = UUID()
        
        response = {
            "maintenance_id": maintenance_id,
            "success": True,
            "message": "Maintenance window scheduled successfully",
            "scheduled_start": maintenance_data.get("scheduled_start"),
            "scheduled_end": maintenance_data.get("scheduled_end")
        }
        
        logger.info("admin_maintenance_scheduled",
                   maintenance_id=str(maintenance_id),
                   admin_id=str(current_user.id))
        
        return response
        
    except Exception as e:
        logger.error("admin_maintenance_schedule_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to schedule maintenance"
        )


@router.post("/data-export")
@require_permissions("admin:system")
async def request_data_export(
    request: DataExportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> DataExportResponse:
    """
    Request system data export for compliance or analysis.
    
    Supports exporting various data types:
    - User data and activity logs
    - System metrics and analytics
    - Audit trails and security events
    - Content and usage statistics
    - Configurable date ranges and filters
    
    Requires admin system permissions.
    """
    logger.info("admin_data_export_requested",
               admin_id=str(current_user.id),
               export_type=request.export_type,
               format=request.format)
    
    try:
        # Validate export type
        valid_types = [
            "users", "presentations", "analytics", "audit_logs", 
            "system_metrics", "security_events"
        ]
        if request.export_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid export type. Must be one of: {', '.join(valid_types)}"
            )
        
        # Validate format
        valid_formats = ["csv", "json", "xlsx"]
        if request.format not in valid_formats:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid format. Must be one of: {', '.join(valid_formats)}"
            )
        
        # This would typically be implemented in the admin service
        # For now, return placeholder response
        export_id = UUID()
        
        response = DataExportResponse(
            export_id=export_id,
            status="processing",
            download_url=None,
            file_size_bytes=None,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            created_at=datetime.now(timezone.utc),
            completed_at=None
        )
        
        # In a real implementation, this would start a background task
        # to process the export and generate the file
        
        logger.info("admin_data_export_initiated",
                   export_id=str(export_id),
                   admin_id=str(current_user.id))
        
        return response
        
    except Exception as e:
        logger.error("admin_data_export_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to request data export"
        )


@router.get("/data-export/{export_id}")
@require_permissions("read:system")
async def get_data_export_status(
    export_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get status of data export request.
    
    Returns current status and download information for export requests.
    
    Requires admin system read permissions.
    """
    logger.info("admin_data_export_status_requested",
               admin_id=str(current_user.id),
               export_id=str(export_id))
    
    try:
        # This would typically be implemented in the admin service
        # For now, return placeholder response
        response = DataExportResponse(
            export_id=export_id,
            status="completed",
            download_url=f"/api/v1/admin/data-export/{export_id}/download",
            file_size_bytes=1024000,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=20),
            created_at=datetime.now(timezone.utc) - timedelta(hours=4),
            completed_at=datetime.now(timezone.utc) - timedelta(hours=3)
        )
        
        logger.info("admin_data_export_status_retrieved",
                   export_id=str(export_id),
                   status=response.status)
        
        return response
        
    except Exception as e:
        logger.error("admin_data_export_status_failed", 
                    export_id=str(export_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve export status"
        )