"""
Admin schemas for SlideGenie administration and management.
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class AdminUserResponse(BaseModel):
    """Admin user management response."""
    id: UUID = Field(..., description="User ID")
    email: EmailStr = Field(..., description="User email")
    full_name: Optional[str] = Field(None, description="Full name")
    title: Optional[str] = Field(None, description="Academic title")
    institution: Optional[str] = Field(None, description="Institution")
    department: Optional[str] = Field(None, description="Department")
    position: Optional[str] = Field(None, description="Position")
    
    # Account status
    role: str = Field(..., description="User role")
    is_active: bool = Field(..., description="Account active status")
    is_verified: bool = Field(..., description="Email verification status")
    
    # Subscription info
    subscription_tier: str = Field(..., description="Subscription tier")
    subscription_expires: Optional[datetime] = Field(None, description="Subscription expiry")
    monthly_presentations_used: int = Field(..., description="Presentations used this month")
    storage_used_bytes: int = Field(..., description="Storage used in bytes")
    
    # Activity metrics
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    presentations_count: int = Field(..., description="Total presentations")
    login_count_30d: int = Field(..., description="Logins in last 30 days")
    
    # Account timestamps
    created_at: datetime = Field(..., description="Account creation date")
    updated_at: datetime = Field(..., description="Last update date")
    deleted_at: Optional[datetime] = Field(None, description="Deletion date if soft-deleted")
    
    class Config:
        from_attributes = True


class AdminUserListResponse(BaseModel):
    """Admin user list response with pagination."""
    users: List[AdminUserResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")


class UserDetailResponse(BaseModel):
    """Detailed user information for admin."""
    user: AdminUserResponse = Field(..., description="User information")
    
    # Activity history
    recent_logins: List[Dict[str, Any]] = Field(..., description="Recent login history")
    recent_presentations: List[Dict[str, Any]] = Field(..., description="Recent presentations")
    recent_exports: List[Dict[str, Any]] = Field(..., description="Recent exports")
    
    # OAuth accounts
    oauth_accounts: List[Dict[str, Any]] = Field(..., description="Connected OAuth accounts")
    
    # API keys
    api_keys: List[Dict[str, Any]] = Field(..., description="Active API keys")
    
    # Subscription history
    subscription_history: List[Dict[str, Any]] = Field(..., description="Subscription change history")
    
    # Usage statistics
    usage_stats: Dict[str, Any] = Field(..., description="Detailed usage statistics")


class SubscriptionUpdateRequest(BaseModel):
    """Request to update user subscription."""
    subscription_tier: str = Field(..., description="New subscription tier")
    subscription_expires: Optional[datetime] = Field(None, description="Expiry date")
    storage_quota_mb: Optional[int] = Field(None, description="Storage quota in MB")
    monthly_presentation_limit: Optional[int] = Field(None, description="Monthly presentation limit")
    reason: Optional[str] = Field(None, description="Reason for change")


class SubscriptionUpdateResponse(BaseModel):
    """Response from subscription update."""
    success: bool = Field(..., description="Update success status")
    message: str = Field(..., description="Status message")
    previous_tier: str = Field(..., description="Previous subscription tier")
    new_tier: str = Field(..., description="New subscription tier")
    effective_date: datetime = Field(..., description="When change takes effect")


class BroadcastRequest(BaseModel):
    """Request to send system-wide notification."""
    title: str = Field(..., min_length=1, max_length=200, description="Notification title")
    message: str = Field(..., min_length=1, max_length=2000, description="Notification message")
    type: str = Field(default="info", description="Notification type (info, warning, error, maintenance)")
    priority: str = Field(default="normal", description="Priority (low, normal, high, urgent)")
    
    # Targeting options
    target_all_users: bool = Field(default=True, description="Send to all users")
    target_subscription_tiers: Optional[List[str]] = Field(None, description="Target specific subscription tiers")
    target_institutions: Optional[List[UUID]] = Field(None, description="Target specific institutions")
    target_user_ids: Optional[List[UUID]] = Field(None, description="Target specific users")
    
    # Scheduling
    send_immediately: bool = Field(default=True, description="Send immediately")
    scheduled_at: Optional[datetime] = Field(None, description="Schedule for later")
    expires_at: Optional[datetime] = Field(None, description="Notification expiry")
    
    # Channels
    send_email: bool = Field(default=False, description="Send via email")
    send_in_app: bool = Field(default=True, description="Show in app")
    send_push: bool = Field(default=False, description="Send push notification")


class BroadcastResponse(BaseModel):
    """Response from broadcast notification."""
    broadcast_id: UUID = Field(..., description="Broadcast identifier")
    success: bool = Field(..., description="Broadcast success status")
    message: str = Field(..., description="Status message")
    recipients_count: int = Field(..., description="Number of recipients")
    scheduled_at: Optional[datetime] = Field(None, description="Scheduled delivery time")
    delivered_at: Optional[datetime] = Field(None, description="Actual delivery time")


class SystemHealthResponse(BaseModel):
    """System health monitoring response."""
    overall_status: str = Field(..., description="Overall system status (healthy, degraded, down)")
    last_check: datetime = Field(..., description="Last health check timestamp")
    
    # Service status
    services: Dict[str, Dict[str, Any]] = Field(..., description="Individual service status")
    
    # Infrastructure health
    database: Dict[str, Any] = Field(..., description="Database health metrics")
    redis: Dict[str, Any] = Field(..., description="Redis health metrics")
    storage: Dict[str, Any] = Field(..., description="Storage health metrics")
    
    # Performance metrics
    response_times: Dict[str, float] = Field(..., description="Average response times by endpoint")
    error_rates: Dict[str, float] = Field(..., description="Error rates by service")
    
    # Resource usage
    cpu_usage: float = Field(..., description="CPU usage percentage")
    memory_usage: float = Field(..., description="Memory usage percentage")
    disk_usage: float = Field(..., description="Disk usage percentage")
    
    # Active connections
    active_users: int = Field(..., description="Currently active users")
    websocket_connections: int = Field(..., description="Active WebSocket connections")
    database_connections: int = Field(..., description="Active database connections")
    
    # Queue status
    pending_jobs: int = Field(..., description="Pending background jobs")
    failed_jobs: int = Field(..., description="Recently failed jobs")


class SystemMetricsResponse(BaseModel):
    """Detailed system metrics response."""
    timestamp: datetime = Field(..., description="Metrics timestamp")
    
    # Performance metrics
    request_metrics: Dict[str, Any] = Field(..., description="HTTP request metrics")
    response_time_percentiles: Dict[str, float] = Field(..., description="Response time percentiles")
    throughput: Dict[str, float] = Field(..., description="Requests per second by endpoint")
    
    # Error tracking
    error_summary: Dict[str, Any] = Field(..., description="Error rate summary")
    recent_errors: List[Dict[str, Any]] = Field(..., description="Recent error occurrences")
    
    # Resource utilization
    system_resources: Dict[str, Any] = Field(..., description="System resource usage")
    application_metrics: Dict[str, Any] = Field(..., description="Application-specific metrics")
    
    # Business metrics
    user_activity: Dict[str, Any] = Field(..., description="User activity metrics")
    content_metrics: Dict[str, Any] = Field(..., description="Content creation metrics")
    ai_usage: Dict[str, Any] = Field(..., description="AI service usage metrics")
    
    # Financial metrics
    cost_metrics: Dict[str, Any] = Field(..., description="Operational cost metrics")
    revenue_metrics: Dict[str, Any] = Field(..., description="Revenue-related metrics")


class UserFilters(BaseModel):
    """Filters for user management queries."""
    search: Optional[str] = Field(None, description="Search term for name/email")
    role: Optional[str] = Field(None, description="Filter by user role")
    subscription_tier: Optional[str] = Field(None, description="Filter by subscription tier")
    institution: Optional[str] = Field(None, description="Filter by institution")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    is_verified: Optional[bool] = Field(None, description="Filter by verification status")
    created_after: Optional[datetime] = Field(None, description="Created after date")
    created_before: Optional[datetime] = Field(None, description="Created before date")
    last_login_after: Optional[datetime] = Field(None, description="Last login after date")
    last_login_before: Optional[datetime] = Field(None, description="Last login before date")
    sort_by: str = Field(default="created_at", description="Sort field")
    sort_order: str = Field(default="desc", description="Sort order (asc, desc)")


class SecurityEvent(BaseModel):
    """Security audit event."""
    event_id: UUID = Field(..., description="Event identifier")
    event_type: str = Field(..., description="Type of security event")
    severity: str = Field(..., description="Event severity (info, warning, critical)")
    user_id: Optional[UUID] = Field(None, description="Associated user ID")
    ip_address: Optional[str] = Field(None, description="Source IP address")
    user_agent: Optional[str] = Field(None, description="User agent string")
    resource: Optional[str] = Field(None, description="Affected resource")
    action: Optional[str] = Field(None, description="Action attempted")
    result: str = Field(..., description="Event result (success, failure, blocked)")
    details: Dict[str, Any] = Field(..., description="Additional event details")
    timestamp: datetime = Field(..., description="Event timestamp")


class SecurityAuditResponse(BaseModel):
    """Security audit log response."""
    events: List[SecurityEvent] = Field(..., description="Security events")
    total: int = Field(..., description="Total number of events")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Page size")
    total_pages: int = Field(..., description="Total pages")
    
    # Summary statistics
    event_counts_by_type: Dict[str, int] = Field(..., description="Event counts by type")
    event_counts_by_severity: Dict[str, int] = Field(..., description="Event counts by severity")
    unique_users_affected: int = Field(..., description="Number of unique users in events")
    unique_ips: int = Field(..., description="Number of unique IP addresses")


class NotificationHistory(BaseModel):
    """Notification broadcast history."""
    broadcast_id: UUID = Field(..., description="Broadcast identifier")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    type: str = Field(..., description="Notification type")
    priority: str = Field(..., description="Notification priority")
    
    # Delivery stats
    recipients_targeted: int = Field(..., description="Number of users targeted")
    recipients_delivered: int = Field(..., description="Number successfully delivered")
    recipients_opened: int = Field(..., description="Number who opened notification")
    recipients_clicked: int = Field(..., description="Number who clicked notification")
    
    # Timing
    created_at: datetime = Field(..., description="Creation timestamp")
    scheduled_at: Optional[datetime] = Field(None, description="Scheduled delivery time")
    delivered_at: Optional[datetime] = Field(None, description="Actual delivery time")
    expires_at: Optional[datetime] = Field(None, description="Expiry time")
    
    # Status
    status: str = Field(..., description="Broadcast status")
    created_by: UUID = Field(..., description="Admin who created broadcast")


class SystemAlert(BaseModel):
    """System alert/warning."""
    alert_id: UUID = Field(..., description="Alert identifier")
    alert_type: str = Field(..., description="Type of alert")
    severity: str = Field(..., description="Alert severity")
    title: str = Field(..., description="Alert title")
    description: str = Field(..., description="Alert description")
    
    # Metrics
    threshold_value: Optional[float] = Field(None, description="Threshold that was exceeded")
    current_value: Optional[float] = Field(None, description="Current metric value")
    
    # Status
    status: str = Field(..., description="Alert status (active, resolved, acknowledged)")
    first_triggered: datetime = Field(..., description="When alert first triggered")
    last_triggered: datetime = Field(..., description="Most recent trigger")
    resolved_at: Optional[datetime] = Field(None, description="When alert was resolved")
    acknowledged_by: Optional[UUID] = Field(None, description="Admin who acknowledged")
    
    # Actions
    auto_resolved: bool = Field(..., description="Whether alert auto-resolved")
    requires_action: bool = Field(..., description="Whether manual action is required")
    suggested_actions: List[str] = Field(..., description="Suggested remediation actions")


class MaintenanceWindow(BaseModel):
    """Scheduled maintenance window."""
    maintenance_id: UUID = Field(..., description="Maintenance identifier")
    title: str = Field(..., description="Maintenance title")
    description: str = Field(..., description="Maintenance description")
    
    # Scheduling
    scheduled_start: datetime = Field(..., description="Scheduled start time")
    scheduled_end: datetime = Field(..., description="Scheduled end time")
    actual_start: Optional[datetime] = Field(None, description="Actual start time")
    actual_end: Optional[datetime] = Field(None, description="Actual end time")
    
    # Impact
    affected_services: List[str] = Field(..., description="Services affected")
    impact_level: str = Field(..., description="Impact level (low, medium, high)")
    user_facing: bool = Field(..., description="Whether users will be affected")
    
    # Status
    status: str = Field(..., description="Maintenance status")
    created_by: UUID = Field(..., description="Admin who scheduled maintenance")
    notification_sent: bool = Field(..., description="Whether users were notified")


class DataExportRequest(BaseModel):
    """Request for data export."""
    export_type: str = Field(..., description="Type of data to export")
    format: str = Field(..., description="Export format (csv, json, xlsx)")
    filters: Optional[Dict[str, Any]] = Field(None, description="Data filters")
    date_range_start: Optional[datetime] = Field(None, description="Start date for data")
    date_range_end: Optional[datetime] = Field(None, description="End date for data")
    include_pii: bool = Field(default=False, description="Include personally identifiable information")


class DataExportResponse(BaseModel):
    """Response from data export request."""
    export_id: UUID = Field(..., description="Export job identifier")
    status: str = Field(..., description="Export status")
    download_url: Optional[str] = Field(None, description="Download URL when ready")
    file_size_bytes: Optional[int] = Field(None, description="File size in bytes")
    expires_at: Optional[datetime] = Field(None, description="Download link expiry")
    created_at: datetime = Field(..., description="Export creation time")
    completed_at: Optional[datetime] = Field(None, description="Export completion time")