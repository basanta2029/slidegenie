"""
Analytics endpoints for SlideGenie metrics and data insights.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user
from app.services.auth.authorization.decorators import require_permissions
from app.services.auth.authorization.permissions import PermissionAction, ResourceType
from app.services.analytics_service import AnalyticsService
from app.domain.schemas.analytics import (
    UsageStatsResponse, GenerationStatsResponse, UserMetricsResponse,
    ExportStatsResponse, TimeSeriesResponse, AnalyticsFilters,
    UserActivityResponse, TopUserActivity, PopularTemplate,
    ErrorAnalysis, PerformanceBenchmark, SystemHealthMetric
)
from app.infrastructure.database.models import User
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/usage", response_model=UsageStatsResponse)
@require_permissions("read:analytics")
async def get_usage_statistics(
    force_refresh: bool = Query(False, description="Force refresh cached data"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> UsageStatsResponse:
    """
    Get system usage statistics and metrics.
    
    Returns comprehensive usage analytics including:
    - Total and active user counts
    - Presentation creation metrics
    - Storage usage statistics
    - Subscription tier distribution
    - Growth rate calculations
    
    Requires admin or analytics read permissions.
    """
    logger.info("usage_statistics_requested", 
               user_id=str(current_user.id),
               force_refresh=force_refresh)
    
    try:
        analytics_service = AnalyticsService(db)
        stats = await analytics_service.get_usage_statistics(force_refresh=force_refresh)
        
        logger.info("usage_statistics_retrieved",
                   total_users=stats.total_users,
                   active_users_30d=stats.active_users_30d)
        
        return stats
        
    except Exception as e:
        logger.error("usage_statistics_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve usage statistics"
        )


@router.get("/generation-stats", response_model=GenerationStatsResponse)
@require_permissions("read:analytics")
async def get_generation_statistics(
    force_refresh: bool = Query(False, description="Force refresh cached data"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> GenerationStatsResponse:
    """
    Get AI generation analytics and performance metrics.
    
    Returns detailed generation analytics including:
    - Generation job counts and success rates
    - AI model usage distribution
    - Token consumption and costs
    - Performance percentiles
    - Error analysis and common issues
    
    Requires admin or analytics read permissions.
    """
    logger.info("generation_statistics_requested",
               user_id=str(current_user.id),
               force_refresh=force_refresh)
    
    try:
        analytics_service = AnalyticsService(db)
        stats = await analytics_service.get_generation_statistics(force_refresh=force_refresh)
        
        logger.info("generation_statistics_retrieved",
                   total_generations=stats.total_generations,
                   success_rate=stats.success_rate)
        
        return stats
        
    except Exception as e:
        logger.error("generation_statistics_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve generation statistics"
        )


@router.get("/user-metrics", response_model=UserMetricsResponse)
@require_permissions("read:analytics")
async def get_user_metrics(
    force_refresh: bool = Query(False, description="Force refresh cached data"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> UserMetricsResponse:
    """
    Get user behavior and engagement metrics.
    
    Returns comprehensive user analytics including:
    - Daily, weekly, and monthly active users
    - Session duration and frequency metrics
    - Content creation patterns
    - Feature adoption rates
    - User retention metrics
    - Geographic distribution
    
    Requires admin or analytics read permissions.
    """
    logger.info("user_metrics_requested",
               user_id=str(current_user.id),
               force_refresh=force_refresh)
    
    try:
        analytics_service = AnalyticsService(db)
        metrics = await analytics_service.get_user_metrics(force_refresh=force_refresh)
        
        logger.info("user_metrics_retrieved",
                   monthly_active_users=metrics.monthly_active_users,
                   retention_30d=metrics.user_retention_30d)
        
        return metrics
        
    except Exception as e:
        logger.error("user_metrics_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user metrics"
        )


@router.get("/export-stats", response_model=ExportStatsResponse)
@require_permissions("read:analytics")
async def get_export_statistics(
    force_refresh: bool = Query(False, description="Force refresh cached data"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ExportStatsResponse:
    """
    Get export format usage and performance statistics.
    
    Returns export analytics including:
    - Export counts by format and time period
    - Format popularity and usage patterns
    - Export performance metrics
    - File size statistics
    - Error rates and common issues
    
    Requires admin or analytics read permissions.
    """
    logger.info("export_statistics_requested",
               user_id=str(current_user.id),
               force_refresh=force_refresh)
    
    try:
        analytics_service = AnalyticsService(db)
        stats = await analytics_service.get_export_statistics(force_refresh=force_refresh)
        
        logger.info("export_statistics_retrieved",
                   total_exports=stats.total_exports,
                   success_rate=stats.export_success_rate)
        
        return stats
        
    except Exception as e:
        logger.error("export_statistics_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve export statistics"
        )


@router.get("/time-series/{metric}")
@require_permissions("read:analytics")
async def get_time_series_data(
    metric: str,
    start_date: Optional[datetime] = Query(None, description="Start date for time series"),
    end_date: Optional[datetime] = Query(None, description="End date for time series"),
    granularity: str = Query("day", description="Time granularity (hour, day, week, month)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get time series data for a specific metric.
    
    Available metrics:
    - user_registrations
    - presentation_creations
    - generation_jobs
    - export_requests
    - active_users
    - storage_usage
    - api_requests
    - error_rate
    
    Requires admin or analytics read permissions.
    """
    logger.info("time_series_requested",
               user_id=str(current_user.id),
               metric=metric,
               granularity=granularity)
    
    # Validate metric name
    valid_metrics = [
        "user_registrations", "presentation_creations", "generation_jobs",
        "export_requests", "active_users", "storage_usage", 
        "api_requests", "error_rate"
    ]
    
    if metric not in valid_metrics:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid metric. Must be one of: {', '.join(valid_metrics)}"
        )
    
    # Set default date range if not provided
    if not end_date:
        end_date = datetime.now(timezone.utc)
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    # Validate date range
    if start_date >= end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date must be before end date"
        )
    
    if (end_date - start_date).days > 365:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date range cannot exceed 365 days"
        )
    
    try:
        analytics_service = AnalyticsService(db)
        
        # This would typically be implemented in the analytics service
        # For now, return a placeholder response
        from app.domain.schemas.analytics import TimeSeriesDataPoint
        
        # Generate sample data points
        data_points = []
        current_date = start_date
        delta = timedelta(days=1) if granularity == "day" else timedelta(hours=1)
        
        while current_date <= end_date:
            # Generate sample value based on metric
            if metric == "user_registrations":
                value = 5.0 + (current_date.day % 10)
            elif metric == "presentation_creations":
                value = 15.0 + (current_date.day % 20)
            elif metric == "active_users":
                value = 100.0 + (current_date.weekday() * 20)
            else:
                value = 10.0 + (current_date.day % 15)
            
            data_points.append(TimeSeriesDataPoint(
                timestamp=current_date,
                value=value,
                metadata={"source": "analytics_service"}
            ))
            
            current_date += delta
        
        response = TimeSeriesResponse(
            metric_name=metric,
            data_points=data_points,
            total_points=len(data_points),
            start_date=start_date,
            end_date=end_date,
            granularity=granularity
        )
        
        logger.info("time_series_retrieved",
                   metric=metric,
                   points=len(data_points),
                   granularity=granularity)
        
        return response
        
    except Exception as e:
        logger.error("time_series_failed", metric=metric, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve time series data"
        )


@router.get("/top-users")
@require_permissions("read:analytics")
async def get_top_active_users(
    limit: int = Query(10, ge=1, le=100, description="Number of top users to return"),
    period_days: int = Query(30, ge=1, le=365, description="Period in days for activity calculation"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get top active users by activity score.
    
    Activity score is calculated based on:
    - Number of presentations created
    - Number of exports performed
    - Login frequency
    - Time spent in application
    
    Requires admin or analytics read permissions.
    """
    logger.info("top_users_requested",
               user_id=str(current_user.id),
               limit=limit,
               period_days=period_days)
    
    try:
        # This would typically be implemented in the analytics service
        # For now, return placeholder data
        top_users = []
        
        # In a real implementation, this would query the database
        # and calculate activity scores based on multiple factors
        
        return {
            "top_users": top_users,
            "period_days": period_days,
            "calculated_at": datetime.now(timezone.utc),
            "total_analyzed": 0
        }
        
    except Exception as e:
        logger.error("top_users_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve top users"
        )


@router.get("/popular-templates")
@require_permissions("read:analytics")
async def get_popular_templates(
    limit: int = Query(10, ge=1, le=50, description="Number of templates to return"),
    period_days: int = Query(30, ge=1, le=365, description="Period in days for usage calculation"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get most popular templates by usage count.
    
    Returns templates ranked by:
    - Total usage count
    - Recent usage (within specified period)
    - User ratings (if available)
    
    Requires admin or analytics read permissions.
    """
    logger.info("popular_templates_requested",
               user_id=str(current_user.id),
               limit=limit,
               period_days=period_days)
    
    try:
        # This would typically be implemented in the analytics service
        # For now, return placeholder data
        popular_templates = []
        
        return {
            "popular_templates": popular_templates,
            "period_days": period_days,
            "calculated_at": datetime.now(timezone.utc),
            "total_templates": 0
        }
        
    except Exception as e:
        logger.error("popular_templates_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve popular templates"
        )


@router.get("/error-analysis")
@require_permissions("read:analytics")
async def get_error_analysis(
    period_hours: int = Query(24, ge=1, le=168, description="Period in hours for error analysis"),
    limit: int = Query(20, ge=1, le=100, description="Number of error types to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get error analysis and common failure patterns.
    
    Returns analysis of:
    - Most common error types
    - Error frequency and trends
    - Affected user counts
    - Error rate by service/component
    
    Requires admin or analytics read permissions.
    """
    logger.info("error_analysis_requested",
               user_id=str(current_user.id),
               period_hours=period_hours,
               limit=limit)
    
    try:
        # This would typically be implemented in the analytics service
        # For now, return placeholder data
        error_analysis = []
        
        return {
            "error_analysis": error_analysis,
            "period_hours": period_hours,
            "analyzed_at": datetime.now(timezone.utc),
            "total_errors": 0
        }
        
    except Exception as e:
        logger.error("error_analysis_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve error analysis"
        )


@router.get("/performance-benchmarks")
@require_permissions("read:analytics")
async def get_performance_benchmarks(
    period_hours: int = Query(24, ge=1, le=168, description="Period in hours for performance analysis"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get performance benchmarks and response time analysis.
    
    Returns performance metrics for:
    - API endpoints response times
    - Database query performance
    - AI generation processing times
    - Export generation times
    - Cache hit rates
    
    Requires admin or analytics read permissions.
    """
    logger.info("performance_benchmarks_requested",
               user_id=str(current_user.id),
               period_hours=period_hours)
    
    try:
        # This would typically be implemented in the analytics service
        # For now, return placeholder data
        benchmarks = []
        
        return {
            "benchmarks": benchmarks,
            "period_hours": period_hours,
            "measured_at": datetime.now(timezone.utc),
            "total_operations": 0
        }
        
    except Exception as e:
        logger.error("performance_benchmarks_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve performance benchmarks"
        )


@router.post("/refresh-cache")
@require_permissions("admin:analytics")
async def refresh_analytics_cache(
    cache_keys: Optional[list[str]] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Refresh analytics cache data.
    
    Refreshes cached analytics data to ensure fresh metrics.
    Can refresh specific cache keys or all analytics caches.
    
    Requires admin permissions.
    """
    logger.info("analytics_cache_refresh_requested",
               user_id=str(current_user.id),
               cache_keys=cache_keys)
    
    try:
        analytics_service = AnalyticsService(db)
        
        refreshed_caches = []
        
        # If no specific keys provided, refresh all main caches
        if not cache_keys:
            cache_keys = ["usage_stats", "generation_stats", "user_metrics", "export_stats"]
        
        for cache_key in cache_keys:
            if cache_key == "usage_stats":
                await analytics_service.get_usage_statistics(force_refresh=True)
                refreshed_caches.append("usage_stats")
            elif cache_key == "generation_stats":
                await analytics_service.get_generation_statistics(force_refresh=True)
                refreshed_caches.append("generation_stats")
            elif cache_key == "user_metrics":
                await analytics_service.get_user_metrics(force_refresh=True)
                refreshed_caches.append("user_metrics")
            elif cache_key == "export_stats":
                await analytics_service.get_export_statistics(force_refresh=True)
                refreshed_caches.append("export_stats")
        
        logger.info("analytics_cache_refreshed",
                   refreshed_caches=refreshed_caches,
                   admin_id=str(current_user.id))
        
        return {
            "success": True,
            "message": "Analytics cache refreshed successfully",
            "refreshed_caches": refreshed_caches,
            "refreshed_at": datetime.now(timezone.utc)
        }
        
    except Exception as e:
        logger.error("analytics_cache_refresh_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh analytics cache"
        )