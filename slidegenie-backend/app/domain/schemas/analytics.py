"""
Analytics schemas for SlideGenie analytics and metrics data.
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from pydantic import BaseModel, Field


class UsageStatsResponse(BaseModel):
    """System usage statistics response."""
    total_users: int = Field(..., description="Total number of registered users")
    active_users_30d: int = Field(..., description="Active users in last 30 days")
    active_users_7d: int = Field(..., description="Active users in last 7 days")
    total_presentations: int = Field(..., description="Total presentations created")
    presentations_created_30d: int = Field(..., description="Presentations created in last 30 days")
    total_slides: int = Field(..., description="Total slides generated")
    total_exports: int = Field(..., description="Total exports performed")
    storage_used_gb: float = Field(..., description="Total storage used in GB")
    
    # Subscription metrics
    free_users: int = Field(..., description="Number of free tier users")
    academic_users: int = Field(..., description="Number of academic tier users")
    professional_users: int = Field(..., description="Number of professional tier users")
    institutional_users: int = Field(..., description="Number of institutional tier users")
    
    # Growth metrics
    user_growth_rate_30d: float = Field(..., description="User growth rate over 30 days (%)")
    presentation_growth_rate_30d: float = Field(..., description="Presentation growth rate over 30 days (%)")
    
    last_updated: datetime = Field(..., description="When statistics were last updated")


class GenerationStatsResponse(BaseModel):
    """AI generation analytics response."""
    total_generations: int = Field(..., description="Total generation jobs completed")
    generations_30d: int = Field(..., description="Generations in last 30 days")
    generations_7d: int = Field(..., description="Generations in last 7 days")
    
    # Success metrics
    success_rate: float = Field(..., description="Overall success rate (%)")
    success_rate_30d: float = Field(..., description="Success rate in last 30 days (%)")
    average_processing_time_seconds: float = Field(..., description="Average processing time")
    
    # Cost metrics
    total_cost_usd: float = Field(..., description="Total AI generation costs")
    cost_30d_usd: float = Field(..., description="Costs in last 30 days")
    average_cost_per_generation: float = Field(..., description="Average cost per generation")
    
    # Model usage
    model_usage: Dict[str, int] = Field(..., description="Usage count by AI model")
    tokens_used_total: int = Field(..., description="Total tokens consumed")
    tokens_used_30d: int = Field(..., description="Tokens used in last 30 days")
    
    # Performance metrics
    p50_processing_time: float = Field(..., description="50th percentile processing time")
    p95_processing_time: float = Field(..., description="95th percentile processing time")
    p99_processing_time: float = Field(..., description="99th percentile processing time")
    
    # Error analysis
    error_rate: float = Field(..., description="Overall error rate (%)")
    common_errors: List[Dict[str, Any]] = Field(..., description="Most common error types")
    
    last_updated: datetime = Field(..., description="When statistics were last updated")


class UserMetricsResponse(BaseModel):
    """User behavior and engagement metrics response."""
    # Engagement metrics
    daily_active_users: int = Field(..., description="Daily active users")
    weekly_active_users: int = Field(..., description="Weekly active users")
    monthly_active_users: int = Field(..., description="Monthly active users")
    
    # Session metrics
    average_session_duration_minutes: float = Field(..., description="Average session duration")
    average_sessions_per_user: float = Field(..., description="Average sessions per user")
    
    # Usage patterns
    presentations_per_user_avg: float = Field(..., description="Average presentations per user")
    slides_per_presentation_avg: float = Field(..., description="Average slides per presentation")
    exports_per_user_avg: float = Field(..., description="Average exports per user")
    
    # Feature adoption
    feature_usage: Dict[str, float] = Field(..., description="Feature adoption rates (%)")
    template_usage: Dict[str, int] = Field(..., description="Template usage statistics")
    
    # Retention metrics
    user_retention_7d: float = Field(..., description="7-day user retention rate (%)")
    user_retention_30d: float = Field(..., description="30-day user retention rate (%)")
    user_retention_90d: float = Field(..., description="90-day user retention rate (%)")
    
    # Geographic distribution
    users_by_country: Dict[str, int] = Field(..., description="User distribution by country")
    users_by_institution_type: Dict[str, int] = Field(..., description="Users by institution type")
    
    last_updated: datetime = Field(..., description="When metrics were last updated")


class ExportStatsResponse(BaseModel):
    """Export format usage and performance statistics."""
    total_exports: int = Field(..., description="Total exports performed")
    exports_30d: int = Field(..., description="Exports in last 30 days")
    exports_7d: int = Field(..., description="Exports in last 7 days")
    
    # Format distribution
    exports_by_format: Dict[str, int] = Field(..., description="Export count by format")
    format_popularity: Dict[str, float] = Field(..., description="Format popularity (%)")
    
    # Performance metrics
    average_export_time_seconds: float = Field(..., description="Average export processing time")
    export_success_rate: float = Field(..., description="Export success rate (%)")
    
    # Performance by format
    format_performance: Dict[str, Dict[str, float]] = Field(
        ..., 
        description="Performance metrics by format (time, success rate)"
    )
    
    # File size statistics
    average_file_size_mb: float = Field(..., description="Average export file size")
    file_size_by_format: Dict[str, float] = Field(..., description="Average file size by format")
    
    # Error analysis
    export_errors: List[Dict[str, Any]] = Field(..., description="Common export errors")
    error_rate_by_format: Dict[str, float] = Field(..., description="Error rate by format (%)")
    
    last_updated: datetime = Field(..., description="When statistics were last updated")


class TimeSeriesDataPoint(BaseModel):
    """Time series data point."""
    timestamp: datetime = Field(..., description="Data point timestamp")
    value: float = Field(..., description="Metric value")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class TimeSeriesResponse(BaseModel):
    """Time series analytics response."""
    metric_name: str = Field(..., description="Name of the metric")
    data_points: List[TimeSeriesDataPoint] = Field(..., description="Time series data")
    total_points: int = Field(..., description="Total number of data points")
    start_date: datetime = Field(..., description="Start of time range")
    end_date: datetime = Field(..., description="End of time range")
    granularity: str = Field(..., description="Data granularity (hour, day, week, month)")


class AnalyticsFilters(BaseModel):
    """Filters for analytics queries."""
    start_date: Optional[datetime] = Field(None, description="Start date filter")
    end_date: Optional[datetime] = Field(None, description="End date filter")
    user_id: Optional[UUID] = Field(None, description="Filter by specific user")
    institution_id: Optional[UUID] = Field(None, description="Filter by institution")
    subscription_tier: Optional[str] = Field(None, description="Filter by subscription tier")
    presentation_type: Optional[str] = Field(None, description="Filter by presentation type")
    template_id: Optional[UUID] = Field(None, description="Filter by template")
    granularity: str = Field(default="day", description="Time granularity")


class UserActivityResponse(BaseModel):
    """User activity analytics response."""
    user_id: UUID = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    full_name: Optional[str] = Field(None, description="User full name")
    institution: Optional[str] = Field(None, description="User institution")
    
    # Activity metrics
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    login_count_30d: int = Field(..., description="Login count in last 30 days")
    session_count_30d: int = Field(..., description="Session count in last 30 days")
    total_session_time_minutes_30d: float = Field(..., description="Total session time in last 30 days")
    
    # Content metrics
    presentations_created: int = Field(..., description="Total presentations created")
    presentations_created_30d: int = Field(..., description="Presentations created in last 30 days")
    slides_created: int = Field(..., description="Total slides created")
    exports_performed: int = Field(..., description="Total exports performed")
    
    # Engagement metrics
    most_used_template: Optional[str] = Field(None, description="Most frequently used template")
    preferred_export_format: Optional[str] = Field(None, description="Most used export format")
    average_presentation_length: float = Field(..., description="Average number of slides per presentation")
    
    # Subscription info
    subscription_tier: str = Field(..., description="Current subscription tier")
    subscription_expires: Optional[datetime] = Field(None, description="Subscription expiry date")
    storage_used_mb: float = Field(..., description="Storage used in MB")


class SystemHealthMetric(BaseModel):
    """System health metric."""
    name: str = Field(..., description="Metric name")
    value: float = Field(..., description="Current value")
    unit: str = Field(..., description="Unit of measurement")
    status: str = Field(..., description="Health status (healthy, warning, critical)")
    threshold_warning: Optional[float] = Field(None, description="Warning threshold")
    threshold_critical: Optional[float] = Field(None, description="Critical threshold")
    last_updated: datetime = Field(..., description="Last update timestamp")


class TopUserActivity(BaseModel):
    """Top user activity summary."""
    user_id: UUID = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    full_name: Optional[str] = Field(None, description="User full name")
    institution: Optional[str] = Field(None, description="Institution")
    activity_score: float = Field(..., description="Activity score")
    presentations_count: int = Field(..., description="Number of presentations")
    last_active: datetime = Field(..., description="Last activity timestamp")


class PopularTemplate(BaseModel):
    """Popular template statistics."""
    template_id: UUID = Field(..., description="Template ID")
    name: str = Field(..., description="Template name")
    category: str = Field(..., description="Template category")
    usage_count: int = Field(..., description="Number of times used")
    usage_count_30d: int = Field(..., description="Usage in last 30 days")
    average_rating: Optional[float] = Field(None, description="Average user rating")


class ErrorAnalysis(BaseModel):
    """Error analysis data."""
    error_type: str = Field(..., description="Type of error")
    error_count: int = Field(..., description="Number of occurrences")
    error_rate: float = Field(..., description="Error rate percentage")
    affected_users: int = Field(..., description="Number of affected users")
    first_occurrence: datetime = Field(..., description="First time this error occurred")
    last_occurrence: datetime = Field(..., description="Most recent occurrence")
    sample_message: str = Field(..., description="Sample error message")


class PerformanceBenchmark(BaseModel):
    """Performance benchmark data."""
    operation: str = Field(..., description="Operation name")
    p50_ms: float = Field(..., description="50th percentile response time (ms)")
    p95_ms: float = Field(..., description="95th percentile response time (ms)")
    p99_ms: float = Field(..., description="99th percentile response time (ms)")
    average_ms: float = Field(..., description="Average response time (ms)")
    throughput_per_second: float = Field(..., description="Operations per second")
    error_rate: float = Field(..., description="Error rate percentage")
    sample_size: int = Field(..., description="Number of samples")
    measurement_period: str = Field(..., description="Measurement time period")