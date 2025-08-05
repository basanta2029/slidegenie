"""
Analytics service for SlideGenie metrics and data aggregation.
"""
import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
import logging

import structlog
from sqlalchemy import func, and_, or_, select, text, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.infrastructure.cache.redis import get_redis_client
from app.infrastructure.database.models import (
    User, Presentation, Slide, GenerationJob, Export, 
    Template, Reference, OAuthAccount, APIKey
)
from app.domain.schemas.analytics import (
    UsageStatsResponse, GenerationStatsResponse, UserMetricsResponse,
    ExportStatsResponse, TimeSeriesResponse, TimeSeriesDataPoint,
    AnalyticsFilters, UserActivityResponse, TopUserActivity,
    PopularTemplate, ErrorAnalysis, PerformanceBenchmark,
    SystemHealthMetric
)

logger = structlog.get_logger(__name__)
settings = get_settings()


class AnalyticsService:
    """Service for analytics data aggregation and caching."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.redis = None
        self.cache_prefix = "analytics:"
        self.cache_ttl = 3600  # 1 hour default cache
        
    async def _get_redis(self):
        """Get Redis client with lazy initialization."""
        if not self.redis:
            self.redis = await get_redis_client()
        return self.redis
    
    async def _cache_get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached analytics data."""
        try:
            redis = await self._get_redis()
            cached = await redis.get(f"{self.cache_prefix}{key}")
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning("cache_get_failed", key=key, error=str(e))
        return None
    
    async def _cache_set(self, key: str, data: Dict[str, Any], ttl: int = None) -> None:
        """Cache analytics data."""
        try:
            redis = await self._get_redis()
            await redis.setex(
                f"{self.cache_prefix}{key}",
                ttl or self.cache_ttl,
                json.dumps(data, default=str)
            )
        except Exception as e:
            logger.warning("cache_set_failed", key=key, error=str(e))
    
    async def get_usage_statistics(self, force_refresh: bool = False) -> UsageStatsResponse:
        """Get system usage statistics."""
        cache_key = "usage_stats"
        
        if not force_refresh:
            cached = await self._cache_get(cache_key)
            if cached:
                return UsageStatsResponse(**cached)
        
        logger.info("computing_usage_statistics")
        
        # Get current date ranges
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        seven_days_ago = now - timedelta(days=7)
        
        # Compute all metrics in parallel
        results = await asyncio.gather(
            self._get_total_users(),
            self._get_active_users(seven_days_ago),
            self._get_active_users(thirty_days_ago),
            self._get_total_presentations(),
            self._get_presentations_created_since(thirty_days_ago),
            self._get_total_slides(),
            self._get_total_exports(),
            self._get_storage_used(),
            self._get_subscription_breakdown(),
            self._get_growth_rates(),
            return_exceptions=True
        )
        
        # Handle any exceptions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("usage_stat_computation_failed", metric_index=i, error=str(result))
                results[i] = 0  # Default fallback
        
        (total_users, active_7d, active_30d, total_presentations, 
         presentations_30d, total_slides, total_exports, storage_gb,
         subscription_breakdown, growth_rates) = results
        
        stats = UsageStatsResponse(
            total_users=total_users,
            active_users_30d=active_30d,
            active_users_7d=active_7d,
            total_presentations=total_presentations,
            presentations_created_30d=presentations_30d,
            total_slides=total_slides,
            total_exports=total_exports,
            storage_used_gb=storage_gb,
            free_users=subscription_breakdown.get('free', 0),
            academic_users=subscription_breakdown.get('academic', 0),
            professional_users=subscription_breakdown.get('professional', 0),
            institutional_users=subscription_breakdown.get('institutional', 0),
            user_growth_rate_30d=growth_rates.get('user_growth', 0.0),
            presentation_growth_rate_30d=growth_rates.get('presentation_growth', 0.0),
            last_updated=now
        )
        
        # Cache for 30 minutes
        await self._cache_set(cache_key, stats.model_dump(), ttl=1800)
        
        logger.info("usage_statistics_computed", total_users=total_users, active_30d=active_30d)
        
        return stats
    
    async def get_generation_statistics(self, force_refresh: bool = False) -> GenerationStatsResponse:
        """Get AI generation analytics."""
        cache_key = "generation_stats"
        
        if not force_refresh:
            cached = await self._cache_get(cache_key)
            if cached:
                return GenerationStatsResponse(**cached)
        
        logger.info("computing_generation_statistics")
        
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        seven_days_ago = now - timedelta(days=7)
        
        # Compute generation metrics
        results = await asyncio.gather(
            self._get_generation_counts(),
            self._get_generation_success_metrics(),
            self._get_generation_cost_metrics(),
            self._get_generation_model_usage(),
            self._get_generation_performance_metrics(),
            self._get_generation_error_analysis(),
            return_exceptions=True
        )
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("generation_stat_computation_failed", metric_index=i, error=str(result))
                results[i] = {}  # Default fallback
        
        (counts, success_metrics, cost_metrics, model_usage,
         performance_metrics, error_analysis) = results
        
        stats = GenerationStatsResponse(
            total_generations=counts.get('total', 0),
            generations_30d=counts.get('thirty_days', 0),
            generations_7d=counts.get('seven_days', 0),
            success_rate=success_metrics.get('overall_rate', 0.0),
            success_rate_30d=success_metrics.get('thirty_day_rate', 0.0),
            average_processing_time_seconds=performance_metrics.get('avg_time', 0.0),
            total_cost_usd=cost_metrics.get('total', 0.0),
            cost_30d_usd=cost_metrics.get('thirty_days', 0.0),
            average_cost_per_generation=cost_metrics.get('average', 0.0),
            model_usage=model_usage,
            tokens_used_total=cost_metrics.get('tokens_total', 0),
            tokens_used_30d=cost_metrics.get('tokens_30d', 0),
            p50_processing_time=performance_metrics.get('p50', 0.0),
            p95_processing_time=performance_metrics.get('p95', 0.0),
            p99_processing_time=performance_metrics.get('p99', 0.0),
            error_rate=error_analysis.get('rate', 0.0),
            common_errors=error_analysis.get('common', []),
            last_updated=now
        )
        
        await self._cache_set(cache_key, stats.model_dump(), ttl=1800)
        
        logger.info("generation_statistics_computed", total=counts.get('total', 0))
        
        return stats
    
    async def get_user_metrics(self, force_refresh: bool = False) -> UserMetricsResponse:
        """Get user behavior and engagement metrics."""
        cache_key = "user_metrics"
        
        if not force_refresh:
            cached = await self._cache_get(cache_key)
            if cached:
                return UserMetricsResponse(**cached)
        
        logger.info("computing_user_metrics")
        
        now = datetime.now(timezone.utc)
        
        # Compute user metrics
        results = await asyncio.gather(
            self._get_user_activity_metrics(),
            self._get_user_engagement_metrics(),
            self._get_user_retention_metrics(),
            self._get_user_geographic_distribution(),
            self._get_feature_adoption_metrics(),
            return_exceptions=True
        )
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("user_metric_computation_failed", metric_index=i, error=str(result))
                results[i] = {}
        
        (activity_metrics, engagement_metrics, retention_metrics,
         geographic_data, feature_adoption) = results
        
        stats = UserMetricsResponse(
            daily_active_users=activity_metrics.get('daily', 0),
            weekly_active_users=activity_metrics.get('weekly', 0),
            monthly_active_users=activity_metrics.get('monthly', 0),
            average_session_duration_minutes=engagement_metrics.get('avg_session_duration', 0.0),
            average_sessions_per_user=engagement_metrics.get('avg_sessions_per_user', 0.0),
            presentations_per_user_avg=engagement_metrics.get('presentations_per_user', 0.0),
            slides_per_presentation_avg=engagement_metrics.get('slides_per_presentation', 0.0),
            exports_per_user_avg=engagement_metrics.get('exports_per_user', 0.0),
            feature_usage=feature_adoption,
            template_usage=engagement_metrics.get('template_usage', {}),
            user_retention_7d=retention_metrics.get('seven_day', 0.0),
            user_retention_30d=retention_metrics.get('thirty_day', 0.0),
            user_retention_90d=retention_metrics.get('ninety_day', 0.0),
            users_by_country=geographic_data.get('by_country', {}),
            users_by_institution_type=geographic_data.get('by_institution_type', {}),
            last_updated=now
        )
        
        await self._cache_set(cache_key, stats.model_dump(), ttl=1800)
        
        logger.info("user_metrics_computed", monthly_active=activity_metrics.get('monthly', 0))
        
        return stats
    
    async def get_export_statistics(self, force_refresh: bool = False) -> ExportStatsResponse:
        """Get export format usage and performance statistics."""
        cache_key = "export_stats"
        
        if not force_refresh:
            cached = await self._cache_get(cache_key)
            if cached:
                return ExportStatsResponse(**cached)
        
        logger.info("computing_export_statistics")
        
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        seven_days_ago = now - timedelta(days=7)
        
        # Compute export metrics
        results = await asyncio.gather(
            self._get_export_counts(),
            self._get_export_format_distribution(),
            self._get_export_performance_metrics(),
            self._get_export_error_analysis(),
            return_exceptions=True
        )
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("export_stat_computation_failed", metric_index=i, error=str(result))
                results[i] = {}
        
        (counts, format_data, performance_data, error_data) = results
        
        stats = ExportStatsResponse(
            total_exports=counts.get('total', 0),
            exports_30d=counts.get('thirty_days', 0),
            exports_7d=counts.get('seven_days', 0),
            exports_by_format=format_data.get('by_format', {}),
            format_popularity=format_data.get('popularity', {}),
            average_export_time_seconds=performance_data.get('avg_time', 0.0),
            export_success_rate=performance_data.get('success_rate', 0.0),
            format_performance=performance_data.get('by_format', {}),
            average_file_size_mb=performance_data.get('avg_size', 0.0),
            file_size_by_format=performance_data.get('size_by_format', {}),
            export_errors=error_data.get('errors', []),
            error_rate_by_format=error_data.get('error_rates', {}),
            last_updated=now
        )
        
        await self._cache_set(cache_key, stats.model_dump(), ttl=1800)
        
        logger.info("export_statistics_computed", total=counts.get('total', 0))
        
        return stats
    
    # Helper methods for data computation
    async def _get_total_users(self) -> int:
        """Get total registered users."""
        result = await self.db.execute(
            select(func.count(User.id)).where(User.deleted_at.is_(None))
        )
        return result.scalar() or 0
    
    async def _get_active_users(self, since: datetime) -> int:
        """Get active users since given date."""
        # This would typically track login activity
        # For now, use created_at as a proxy
        result = await self.db.execute(
            select(func.count(User.id)).where(
                and_(
                    User.deleted_at.is_(None),
                    User.created_at >= since
                )
            )
        )
        return result.scalar() or 0
    
    async def _get_total_presentations(self) -> int:
        """Get total presentations created."""
        result = await self.db.execute(
            select(func.count(Presentation.id)).where(Presentation.deleted_at.is_(None))
        )
        return result.scalar() or 0
    
    async def _get_presentations_created_since(self, since: datetime) -> int:
        """Get presentations created since given date."""
        result = await self.db.execute(
            select(func.count(Presentation.id)).where(
                and_(
                    Presentation.deleted_at.is_(None),
                    Presentation.created_at >= since
                )
            )
        )
        return result.scalar() or 0
    
    async def _get_total_slides(self) -> int:
        """Get total slides created."""
        result = await self.db.execute(
            select(func.count(Slide.id)).where(Slide.deleted_at.is_(None))
        )
        return result.scalar() or 0
    
    async def _get_total_exports(self) -> int:
        """Get total exports performed."""
        result = await self.db.execute(select(func.count(Export.id)))
        return result.scalar() or 0
    
    async def _get_storage_used(self) -> float:
        """Get total storage used in GB."""
        result = await self.db.execute(
            select(func.sum(User.storage_used_bytes)).where(User.deleted_at.is_(None))
        )
        bytes_used = result.scalar() or 0
        return bytes_used / (1024 ** 3)  # Convert to GB
    
    async def _get_subscription_breakdown(self) -> Dict[str, int]:
        """Get user count by subscription tier."""
        result = await self.db.execute(
            select(
                User.subscription_tier,
                func.count(User.id)
            ).where(
                User.deleted_at.is_(None)
            ).group_by(User.subscription_tier)
        )
        
        breakdown = {}
        for tier, count in result.fetchall():
            breakdown[tier] = count
        
        return breakdown
    
    async def _get_growth_rates(self) -> Dict[str, float]:
        """Calculate growth rates."""
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        sixty_days_ago = now - timedelta(days=60)
        
        # User growth
        users_current = await self._get_active_users(thirty_days_ago)
        users_previous = await self.db.execute(
            select(func.count(User.id)).where(
                and_(
                    User.deleted_at.is_(None),
                    User.created_at >= sixty_days_ago,
                    User.created_at < thirty_days_ago
                )
            )
        )
        users_previous = users_previous.scalar() or 1
        
        user_growth = ((users_current - users_previous) / users_previous) * 100
        
        # Presentation growth
        presentations_current = await self._get_presentations_created_since(thirty_days_ago)
        presentations_previous = await self.db.execute(
            select(func.count(Presentation.id)).where(
                and_(
                    Presentation.deleted_at.is_(None),
                    Presentation.created_at >= sixty_days_ago,
                    Presentation.created_at < thirty_days_ago
                )
            )
        )
        presentations_previous = presentations_previous.scalar() or 1
        
        presentation_growth = ((presentations_current - presentations_previous) / presentations_previous) * 100
        
        return {
            'user_growth': user_growth,
            'presentation_growth': presentation_growth
        }
    
    async def _get_generation_counts(self) -> Dict[str, int]:
        """Get generation job counts."""
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        seven_days_ago = now - timedelta(days=7)
        
        total = await self.db.execute(select(func.count(GenerationJob.id)))
        thirty_days = await self.db.execute(
            select(func.count(GenerationJob.id)).where(
                GenerationJob.created_at >= thirty_days_ago
            )
        )
        seven_days = await self.db.execute(
            select(func.count(GenerationJob.id)).where(
                GenerationJob.created_at >= seven_days_ago
            )
        )
        
        return {
            'total': total.scalar() or 0,
            'thirty_days': thirty_days.scalar() or 0,
            'seven_days': seven_days.scalar() or 0
        }
    
    async def _get_generation_success_metrics(self) -> Dict[str, float]:
        """Get generation success rates."""
        total_jobs = await self.db.execute(select(func.count(GenerationJob.id)))
        total_count = total_jobs.scalar() or 1
        
        successful_jobs = await self.db.execute(
            select(func.count(GenerationJob.id)).where(
                GenerationJob.status == 'completed'
            )
        )
        successful_count = successful_jobs.scalar() or 0
        
        overall_rate = (successful_count / total_count) * 100
        
        # 30-day success rate
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        total_30d = await self.db.execute(
            select(func.count(GenerationJob.id)).where(
                GenerationJob.created_at >= thirty_days_ago
            )
        )
        total_30d_count = total_30d.scalar() or 1
        
        successful_30d = await self.db.execute(
            select(func.count(GenerationJob.id)).where(
                and_(
                    GenerationJob.status == 'completed',
                    GenerationJob.created_at >= thirty_days_ago
                )
            )
        )
        successful_30d_count = successful_30d.scalar() or 0
        
        thirty_day_rate = (successful_30d_count / total_30d_count) * 100
        
        return {
            'overall_rate': overall_rate,
            'thirty_day_rate': thirty_day_rate
        }
    
    async def _get_generation_cost_metrics(self) -> Dict[str, float]:
        """Get generation cost metrics."""
        result = await self.db.execute(
            select(
                func.sum(GenerationJob.generation_cost),
                func.sum(GenerationJob.tokens_used),
                func.count(GenerationJob.id)
            ).where(GenerationJob.generation_cost.is_not(None))
        )
        
        total_cost, total_tokens, job_count = result.fetchone() or (0, 0, 1)
        
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        result_30d = await self.db.execute(
            select(
                func.sum(GenerationJob.generation_cost),
                func.sum(GenerationJob.tokens_used)
            ).where(
                and_(
                    GenerationJob.generation_cost.is_not(None),
                    GenerationJob.created_at >= thirty_days_ago
                )
            )
        )
        
        cost_30d, tokens_30d = result_30d.fetchone() or (0, 0)
        
        return {
            'total': total_cost or 0.0,
            'thirty_days': cost_30d or 0.0,
            'average': (total_cost / job_count) if job_count > 0 else 0.0,
            'tokens_total': total_tokens or 0,
            'tokens_30d': tokens_30d or 0
        }
    
    async def _get_generation_model_usage(self) -> Dict[str, int]:
        """Get usage count by AI model."""
        result = await self.db.execute(
            select(
                GenerationJob.ai_model_used,
                func.count(GenerationJob.id)
            ).where(
                GenerationJob.ai_model_used.is_not(None)
            ).group_by(GenerationJob.ai_model_used)
        )
        
        model_usage = {}
        for model, count in result.fetchall():
            model_usage[model] = count
        
        return model_usage
    
    async def _get_generation_performance_metrics(self) -> Dict[str, float]:
        """Get generation performance metrics."""
        # This would typically use more sophisticated percentile calculations
        result = await self.db.execute(
            select(
                func.avg(GenerationJob.duration_seconds),
                func.percentile_cont(0.5).within_group(GenerationJob.duration_seconds),
                func.percentile_cont(0.95).within_group(GenerationJob.duration_seconds),
                func.percentile_cont(0.99).within_group(GenerationJob.duration_seconds)
            ).where(
                and_(
                    GenerationJob.duration_seconds.is_not(None),
                    GenerationJob.status == 'completed'
                )
            )
        )
        
        avg_time, p50, p95, p99 = result.fetchone() or (0, 0, 0, 0)
        
        return {
            'avg_time': avg_time or 0.0,
            'p50': p50 or 0.0,
            'p95': p95 or 0.0,
            'p99': p99 or 0.0
        }
    
    async def _get_generation_error_analysis(self) -> Dict[str, Any]:
        """Get generation error analysis."""
        total_jobs = await self.db.execute(select(func.count(GenerationJob.id)))
        total_count = total_jobs.scalar() or 1
        
        failed_jobs = await self.db.execute(
            select(func.count(GenerationJob.id)).where(
                GenerationJob.status == 'failed'
            )
        )
        failed_count = failed_jobs.scalar() or 0
        
        error_rate = (failed_count / total_count) * 100
        
        # Get common error types
        common_errors_result = await self.db.execute(
            select(
                GenerationJob.error_message,
                func.count(GenerationJob.id)
            ).where(
                and_(
                    GenerationJob.status == 'failed',
                    GenerationJob.error_message.is_not(None)
                )
            ).group_by(GenerationJob.error_message)
            .order_by(desc(func.count(GenerationJob.id)))
            .limit(5)
        )
        
        common_errors = []
        for error_msg, count in common_errors_result.fetchall():
            common_errors.append({
                'error_message': error_msg,
                'count': count,
                'percentage': (count / failed_count) * 100 if failed_count > 0 else 0
            })
        
        return {
            'rate': error_rate,
            'common': common_errors
        }
    
    async def _get_user_activity_metrics(self) -> Dict[str, int]:
        """Get user activity metrics."""
        now = datetime.now(timezone.utc)
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # Using creation as proxy for activity
        daily = await self.db.execute(
            select(func.count(User.id)).where(
                and_(
                    User.deleted_at.is_(None),
                    User.created_at >= day_ago
                )
            )
        )
        
        weekly = await self.db.execute(
            select(func.count(User.id)).where(
                and_(
                    User.deleted_at.is_(None),
                    User.created_at >= week_ago
                )
            )
        )
        
        monthly = await self.db.execute(
            select(func.count(User.id)).where(
                and_(
                    User.deleted_at.is_(None),
                    User.created_at >= month_ago
                )
            )
        )
        
        return {
            'daily': daily.scalar() or 0,
            'weekly': weekly.scalar() or 0,
            'monthly': monthly.scalar() or 0
        }
    
    async def _get_user_engagement_metrics(self) -> Dict[str, Any]:
        """Get user engagement metrics."""
        # Average presentations per user
        result = await self.db.execute(
            select(func.avg(func.count(Presentation.id))).select_from(
                select(Presentation.owner_id).where(
                    Presentation.deleted_at.is_(None)
                ).group_by(Presentation.owner_id).subquery()
            )
        )
        presentations_per_user = result.scalar() or 0.0
        
        # Average slides per presentation
        result = await self.db.execute(
            select(func.avg(Presentation.slide_count)).where(
                and_(
                    Presentation.deleted_at.is_(None),
                    Presentation.slide_count > 0
                )
            )
        )
        slides_per_presentation = result.scalar() or 0.0
        
        # Template usage
        template_usage = await self.db.execute(
            select(
                Template.name,
                func.count(Presentation.id)
            ).join(Presentation, Template.id == Presentation.template_id)
            .where(Presentation.deleted_at.is_(None))
            .group_by(Template.name)
            .order_by(desc(func.count(Presentation.id)))
            .limit(10)
        )
        
        template_stats = {}
        for name, count in template_usage.fetchall():
            template_stats[name] = count
        
        return {
            'presentations_per_user': presentations_per_user,
            'slides_per_presentation': slides_per_presentation,
            'exports_per_user': 0.0,  # Placeholder
            'avg_session_duration': 0.0,  # Placeholder
            'avg_sessions_per_user': 0.0,  # Placeholder
            'template_usage': template_stats
        }
    
    async def _get_user_retention_metrics(self) -> Dict[str, float]:
        """Get user retention metrics."""
        # This would typically require user activity tracking
        # Returning placeholder values for now
        return {
            'seven_day': 75.0,
            'thirty_day': 45.0,
            'ninety_day': 25.0
        }
    
    async def _get_user_geographic_distribution(self) -> Dict[str, Dict[str, int]]:
        """Get user geographic distribution."""
        # By country (using institution as proxy)
        country_result = await self.db.execute(
            select(
                User.institution,
                func.count(User.id)
            ).where(
                and_(
                    User.deleted_at.is_(None),
                    User.institution.is_not(None)
                )
            ).group_by(User.institution)
            .order_by(desc(func.count(User.id)))
            .limit(10)
        )
        
        by_country = {}
        for institution, count in country_result.fetchall():
            # Extract country from institution name (simplified)
            country = institution.split()[-1] if institution else "Unknown"
            by_country[country] = by_country.get(country, 0) + count
        
        # By institution type (placeholder)
        by_institution_type = {
            'University': 500,
            'Research Institute': 200,
            'Company': 150,
            'Government': 50
        }
        
        return {
            'by_country': by_country,
            'by_institution_type': by_institution_type
        }
    
    async def _get_feature_adoption_metrics(self) -> Dict[str, float]:
        """Get feature adoption rates."""
        total_users = await self._get_total_users()
        if total_users == 0:
            return {}
        
        # Users with presentations
        users_with_presentations = await self.db.execute(
            select(func.count(func.distinct(Presentation.owner_id))).where(
                Presentation.deleted_at.is_(None)
            )
        )
        presentation_adoption = (users_with_presentations.scalar() or 0) / total_users * 100
        
        # Users with exports
        users_with_exports = await self.db.execute(
            select(func.count(func.distinct(Presentation.owner_id))).join(
                Export, Presentation.id == Export.presentation_id
            ).where(Presentation.deleted_at.is_(None))
        )
        export_adoption = (users_with_exports.scalar() or 0) / total_users * 100
        
        return {
            'presentation_creation': presentation_adoption,
            'export_feature': export_adoption,
            'template_usage': 60.0,  # Placeholder
            'collaboration': 25.0,  # Placeholder
            'api_usage': 5.0  # Placeholder
        }
    
    async def _get_export_counts(self) -> Dict[str, int]:
        """Get export counts."""
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        seven_days_ago = now - timedelta(days=7)
        
        total = await self.db.execute(select(func.count(Export.id)))
        thirty_days = await self.db.execute(
            select(func.count(Export.id)).where(Export.created_at >= thirty_days_ago)
        )
        seven_days = await self.db.execute(
            select(func.count(Export.id)).where(Export.created_at >= seven_days_ago)
        )
        
        return {
            'total': total.scalar() or 0,
            'thirty_days': thirty_days.scalar() or 0,
            'seven_days': seven_days.scalar() or 0
        }
    
    async def _get_export_format_distribution(self) -> Dict[str, Any]:
        """Get export format distribution."""
        result = await self.db.execute(
            select(
                Export.format,
                func.count(Export.id)
            ).group_by(Export.format)
        )
        
        by_format = {}
        total_exports = 0
        for format_type, count in result.fetchall():
            by_format[format_type] = count
            total_exports += count
        
        # Calculate popularity percentages
        popularity = {}
        for format_type, count in by_format.items():
            popularity[format_type] = (count / total_exports) * 100 if total_exports > 0 else 0
        
        return {
            'by_format': by_format,
            'popularity': popularity
        }
    
    async def _get_export_performance_metrics(self) -> Dict[str, Any]:
        """Get export performance metrics."""
        # Overall performance
        result = await self.db.execute(
            select(
                func.avg(Export.file_size_bytes),
                func.count(Export.id)
            ).where(Export.status == 'completed')
        )
        
        avg_size_bytes, completed_count = result.fetchone() or (0, 0)
        avg_size_mb = (avg_size_bytes or 0) / (1024 * 1024)
        
        # Success rate
        total_exports = await self.db.execute(select(func.count(Export.id)))
        total_count = total_exports.scalar() or 1
        success_rate = (completed_count / total_count) * 100
        
        # Performance by format
        format_performance = {}
        formats_result = await self.db.execute(
            select(
                Export.format,
                func.avg(Export.file_size_bytes),
                func.count(Export.id).filter(Export.status == 'completed'),
                func.count(Export.id)
            ).group_by(Export.format)
        )
        
        for format_type, avg_size, completed, total in formats_result.fetchall():
            success_rate_format = (completed / total) * 100 if total > 0 else 0
            format_performance[format_type] = {
                'success_rate': success_rate_format,
                'avg_size_mb': (avg_size or 0) / (1024 * 1024)
            }
        
        # Size by format
        size_by_format = {}
        for format_type, data in format_performance.items():
            size_by_format[format_type] = data['avg_size_mb']
        
        return {
            'avg_time': 0.0,  # Placeholder - would need processing time tracking
            'success_rate': success_rate,
            'by_format': format_performance,
            'avg_size': avg_size_mb,
            'size_by_format': size_by_format
        }
    
    async def _get_export_error_analysis(self) -> Dict[str, Any]:
        """Get export error analysis."""
        # Overall errors
        errors_result = await self.db.execute(
            select(
                Export.error_message,
                func.count(Export.id)
            ).where(
                and_(
                    Export.status == 'failed',
                    Export.error_message.is_not(None)
                )
            ).group_by(Export.error_message)
            .order_by(desc(func.count(Export.id)))
            .limit(5)
        )
        
        errors = []
        for error_msg, count in errors_result.fetchall():
            errors.append({
                'error_message': error_msg,
                'count': count
            })
        
        # Error rates by format
        error_rates = {}
        formats_result = await self.db.execute(
            select(
                Export.format,
                func.count(Export.id).filter(Export.status == 'failed'),
                func.count(Export.id)
            ).group_by(Export.format)
        )
        
        for format_type, failed_count, total_count in formats_result.fetchall():
            error_rate = (failed_count / total_count) * 100 if total_count > 0 else 0
            error_rates[format_type] = error_rate
        
        return {
            'errors': errors,
            'error_rates': error_rates
        }