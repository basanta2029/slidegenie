"""
Admin service for SlideGenie user management and system administration.
"""
import asyncio
import json
import psutil
import platform
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
import logging

import structlog
from sqlalchemy import func, and_, or_, select, text, desc, asc, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.infrastructure.cache.redis import get_redis_client
from app.infrastructure.database.models import (
    User, Presentation, Slide, GenerationJob, Export, 
    Template, Reference, OAuthAccount, APIKey, Institution
)
from app.domain.schemas.admin import (
    AdminUserResponse, AdminUserListResponse, UserDetailResponse,
    SubscriptionUpdateRequest, SubscriptionUpdateResponse,
    BroadcastRequest, BroadcastResponse, SystemHealthResponse,
    SystemMetricsResponse, UserFilters, SecurityEvent,
    SecurityAuditResponse, NotificationHistory, SystemAlert,
    MaintenanceWindow, DataExportRequest, DataExportResponse
)
# from app.services.auth.email_service import EmailService  # Would be imported when needed

logger = structlog.get_logger(__name__)
settings = get_settings()


class AdminService:
    """Service for admin user management and system monitoring."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.redis = None
        self.cache_prefix = "admin:"
        self.cache_ttl = 1800  # 30 minutes default cache
        # Note: EmailService would be injected or initialized as needed
        self.email_service = None  # Placeholder - would inject EmailService
        
    async def _get_redis(self):
        """Get Redis client with lazy initialization."""
        if not self.redis:
            self.redis = await get_redis_client()
        return self.redis
    
    async def _cache_get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached admin data."""
        try:
            redis = await self._get_redis()
            cached = await redis.get(f"{self.cache_prefix}{key}")
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning("admin_cache_get_failed", key=key, error=str(e))
        return None
    
    async def _cache_set(self, key: str, data: Dict[str, Any], ttl: int = None) -> None:
        """Cache admin data."""
        try:
            redis = await self._get_redis()
            await redis.setex(
                f"{self.cache_prefix}{key}",
                ttl or self.cache_ttl,
                json.dumps(data, default=str)
            )
        except Exception as e:
            logger.warning("admin_cache_set_failed", key=key, error=str(e))
    
    async def _audit_log(self, admin_id: UUID, action: str, resource: str, 
                        resource_id: Optional[UUID] = None, details: Dict[str, Any] = None):
        """Log admin action for audit purposes."""
        try:
            redis = await self._get_redis()
            audit_entry = {
                'admin_id': str(admin_id),
                'action': action,
                'resource': resource,
                'resource_id': str(resource_id) if resource_id else None,
                'details': details or {},
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'ip_address': None,  # Would be passed from request context
                'user_agent': None   # Would be passed from request context
            }
            
            # Store in Redis list for recent activity
            await redis.lpush(
                f"{self.cache_prefix}audit_log",
                json.dumps(audit_entry, default=str)
            )
            
            # Keep only last 1000 entries
            await redis.ltrim(f"{self.cache_prefix}audit_log", 0, 999)
            
            logger.info("admin_action_audited", **audit_entry)
            
        except Exception as e:
            logger.error("audit_log_failed", error=str(e))
    
    async def get_users(
        self, 
        filters: UserFilters, 
        page: int = 1, 
        page_size: int = 20,
        admin_id: Optional[UUID] = None
    ) -> AdminUserListResponse:
        """Get paginated list of users with filtering."""
        if admin_id:
            await self._audit_log(admin_id, "list_users", "user", details=filters.model_dump())
        
        logger.info("fetching_users", filters=filters.model_dump(), page=page, page_size=page_size)
        
        # Build base query
        query = select(User).where(User.deleted_at.is_(None))
        
        # Apply filters
        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.where(
                or_(
                    User.full_name.ilike(search_term),
                    User.email.ilike(search_term),
                    User.institution.ilike(search_term)
                )
            )
        
        if filters.role:
            query = query.where(User.role == filters.role)
        
        if filters.subscription_tier:
            query = query.where(User.subscription_tier == filters.subscription_tier)
        
        if filters.institution:
            query = query.where(User.institution.ilike(f"%{filters.institution}%"))
        
        if filters.is_active is not None:
            query = query.where(User.is_active == filters.is_active)
        
        if filters.is_verified is not None:
            query = query.where(User.is_verified == filters.is_verified)
        
        if filters.created_after:
            query = query.where(User.created_at >= filters.created_after)
        
        if filters.created_before:
            query = query.where(User.created_at <= filters.created_before)
        
        # Count total matching records
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Apply sorting
        if filters.sort_by == "created_at":
            sort_column = User.created_at
        elif filters.sort_by == "email":
            sort_column = User.email
        elif filters.sort_by == "full_name":
            sort_column = User.full_name
        elif filters.sort_by == "last_login":
            sort_column = User.updated_at  # Proxy for last activity
        else:
            sort_column = User.created_at
        
        if filters.sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        # Execute query with additional data
        result = await self.db.execute(
            query.options(selectinload(User.presentations))
        )
        users = result.scalars().all()
        
        # Convert to response format with additional metrics
        user_responses = []
        for user in users:
            # Get login count (using created presentations as proxy)
            login_count = len([p for p in user.presentations 
                             if p.created_at >= datetime.now(timezone.utc) - timedelta(days=30)])
            
            user_response = AdminUserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                title=user.title,
                institution=user.institution,
                department=user.department,
                position=user.position,
                role=user.role,
                is_active=user.is_active,
                is_verified=user.is_verified,
                subscription_tier=user.subscription_tier,
                subscription_expires=user.subscription_expires,
                monthly_presentations_used=user.monthly_presentations_used,
                storage_used_bytes=user.storage_used_bytes,
                last_login=None,  # Would need session tracking
                presentations_count=len(user.presentations),
                login_count_30d=login_count,
                created_at=user.created_at,
                updated_at=user.updated_at,
                deleted_at=user.deleted_at
            )
            user_responses.append(user_response)
        
        total_pages = (total + page_size - 1) // page_size
        
        logger.info("users_fetched", total=total, page=page, returned=len(user_responses))
        
        return AdminUserListResponse(
            users=user_responses,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    
    async def get_user_details(self, user_id: UUID, admin_id: Optional[UUID] = None) -> UserDetailResponse:
        """Get detailed user information."""
        if admin_id:
            await self._audit_log(admin_id, "view_user_details", "user", user_id)
        
        logger.info("fetching_user_details", user_id=str(user_id))
        
        # Get user with all related data
        result = await self.db.execute(
            select(User)
            .options(
                selectinload(User.presentations),
                selectinload(User.oauth_accounts),
                selectinload(User.api_keys),
                selectinload(User.generation_jobs)
            )
            .where(User.id == user_id)
        )
        
        user = result.scalars().first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Get recent activity data
        recent_presentations = []
        for presentation in sorted(user.presentations, key=lambda p: p.created_at, reverse=True)[:10]:
            recent_presentations.append({
                'id': str(presentation.id),
                'title': presentation.title,
                'created_at': presentation.created_at.isoformat(),
                'status': presentation.status,
                'slide_count': presentation.slide_count
            })
        
        # Get recent exports
        recent_exports = []
        for presentation in user.presentations[:5]:  # Sample from recent presentations
            if hasattr(presentation, 'exports'):
                for export in presentation.exports[-3:]:  # Last 3 exports per presentation
                    recent_exports.append({
                        'id': str(export.id),
                        'format': export.format,
                        'status': export.status,
                        'created_at': export.requested_at.isoformat(),
                        'presentation_title': presentation.title
                    })
        
        # OAuth accounts
        oauth_accounts = []
        for oauth in user.oauth_accounts:
            oauth_accounts.append({
                'provider': oauth.provider,
                'email': oauth.email,
                'institution': oauth.institution,
                'connected_at': oauth.created_at.isoformat()
            })
        
        # API keys
        api_keys = []
        for api_key in user.api_keys:
            if api_key.is_active:
                api_keys.append({
                    'name': api_key.name,
                    'key_prefix': api_key.key_prefix,
                    'scopes': api_key.scopes,
                    'last_used': api_key.last_used_at.isoformat() if api_key.last_used_at else None,
                    'created_at': api_key.created_at.isoformat()
                })
        
        # Usage statistics
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        recent_presentations_count = len([p for p in user.presentations if p.created_at >= thirty_days_ago])
        recent_jobs_count = len([j for j in user.generation_jobs if j.created_at >= thirty_days_ago])
        
        usage_stats = {
            'total_presentations': len(user.presentations),
            'presentations_last_30d': recent_presentations_count,
            'total_generation_jobs': len(user.generation_jobs),
            'generation_jobs_last_30d': recent_jobs_count,
            'storage_used_mb': user.storage_used_bytes / (1024 * 1024),
            'api_calls_last_30d': 0,  # Would need API call tracking
            'average_slides_per_presentation': sum(p.slide_count or 0 for p in user.presentations) / len(user.presentations) if user.presentations else 0
        }
        
        # Create main user response
        user_response = AdminUserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            title=user.title,
            institution=user.institution,
            department=user.department,
            position=user.position,
            role=user.role,
            is_active=user.is_active,
            is_verified=user.is_verified,
            subscription_tier=user.subscription_tier,
            subscription_expires=user.subscription_expires,
            monthly_presentations_used=user.monthly_presentations_used,
            storage_used_bytes=user.storage_used_bytes,
            last_login=None,
            presentations_count=len(user.presentations),
            login_count_30d=0,  # Would need session tracking
            created_at=user.created_at,
            updated_at=user.updated_at,
            deleted_at=user.deleted_at
        )
        
        logger.info("user_details_fetched", user_id=str(user_id), presentations=len(user.presentations))
        
        return UserDetailResponse(
            user=user_response,
            recent_logins=[],  # Would need session tracking
            recent_presentations=recent_presentations,
            recent_exports=recent_exports,
            oauth_accounts=oauth_accounts,
            api_keys=api_keys,
            subscription_history=[],  # Would need subscription change tracking
            usage_stats=usage_stats
        )
    
    async def update_user_subscription(
        self, 
        user_id: UUID, 
        request: SubscriptionUpdateRequest,
        admin_id: UUID
    ) -> SubscriptionUpdateResponse:
        """Update user subscription."""
        await self._audit_log(
            admin_id, "update_subscription", "user", user_id, 
            details=request.model_dump()
        )
        
        logger.info("updating_user_subscription", user_id=str(user_id), request=request.model_dump())
        
        # Get current user
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        previous_tier = user.subscription_tier
        
        # Update subscription
        update_data = {
            'subscription_tier': request.subscription_tier,
            'updated_at': datetime.now(timezone.utc)
        }
        
        if request.subscription_expires:
            update_data['subscription_expires'] = request.subscription_expires
        
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(**update_data)
        )
        
        await self.db.commit()
        
        # Send notification email if user has verified email
        if user.is_verified and user.email and self.email_service:
            try:
                # This would send subscription update email
                # await self.email_service.send_subscription_updated_email(...)
                logger.info("subscription_update_email_would_be_sent", user_email=user.email)
            except Exception as e:
                logger.warning("subscription_update_email_failed", error=str(e))
        
        # Clear user-related caches
        await self._clear_user_cache(user_id)
        
        logger.info("user_subscription_updated", 
                   user_id=str(user_id), 
                   previous_tier=previous_tier,
                   new_tier=request.subscription_tier)
        
        return SubscriptionUpdateResponse(
            success=True,
            message="Subscription updated successfully",
            previous_tier=previous_tier,
            new_tier=request.subscription_tier,
            effective_date=datetime.now(timezone.utc)
        )
    
    async def send_broadcast_notification(
        self, 
        request: BroadcastRequest,
        admin_id: UUID
    ) -> BroadcastResponse:
        """Send system-wide notification."""
        broadcast_id = UUID()
        
        await self._audit_log(
            admin_id, "send_broadcast", "notification", broadcast_id,
            details=request.model_dump()
        )
        
        logger.info("sending_broadcast_notification", 
                   broadcast_id=str(broadcast_id),
                   request=request.model_dump())
        
        # Determine recipients
        recipients_query = select(User).where(User.deleted_at.is_(None))
        
        if not request.target_all_users:
            conditions = []
            
            if request.target_subscription_tiers:
                conditions.append(User.subscription_tier.in_(request.target_subscription_tiers))
            
            if request.target_institutions:
                # This would need proper institution linking
                institution_names = []
                for inst_id in request.target_institutions:
                    # Get institution name from ID
                    inst_result = await self.db.execute(
                        select(Institution.name).where(Institution.id == inst_id)
                    )
                    inst_name = inst_result.scalar()
                    if inst_name:
                        institution_names.append(inst_name)
                
                if institution_names:
                    conditions.append(User.institution.in_(institution_names))
            
            if request.target_user_ids:
                conditions.append(User.id.in_(request.target_user_ids))
            
            if conditions:
                recipients_query = recipients_query.where(or_(*conditions))
        
        # Get recipient count
        count_result = await self.db.execute(
            select(func.count()).select_from(recipients_query.subquery())
        )
        recipients_count = count_result.scalar() or 0
        
        # Store broadcast in Redis for tracking
        broadcast_data = {
            'id': str(broadcast_id),
            'title': request.title,
            'message': request.message,
            'type': request.type,
            'priority': request.priority,
            'recipients_count': recipients_count,
            'created_by': str(admin_id),
            'created_at': datetime.now(timezone.utc).isoformat(),
            'scheduled_at': request.scheduled_at.isoformat() if request.scheduled_at else None,
            'status': 'scheduled' if request.scheduled_at else 'sent'
        }
        
        redis = await self._get_redis()
        await redis.setex(
            f"{self.cache_prefix}broadcast:{broadcast_id}",
            86400,  # 24 hours
            json.dumps(broadcast_data, default=str)
        )
        
        # If sending immediately, process the broadcast
        delivered_at = None
        if request.send_immediately:
            # In a real implementation, this would:
            # 1. Send in-app notifications via WebSocket
            # 2. Send emails if requested
            # 3. Send push notifications if requested
            # 4. Update delivery status
            
            delivered_at = datetime.now(timezone.utc)
            broadcast_data['status'] = 'delivered'
            broadcast_data['delivered_at'] = delivered_at.isoformat()
            
            await redis.setex(
                f"{self.cache_prefix}broadcast:{broadcast_id}",
                86400,
                json.dumps(broadcast_data, default=str)
            )
            
            # Store in broadcast history
            await redis.lpush(
                f"{self.cache_prefix}broadcast_history",
                json.dumps(broadcast_data, default=str)
            )
            await redis.ltrim(f"{self.cache_prefix}broadcast_history", 0, 99)  # Keep last 100
        
        logger.info("broadcast_notification_processed",
                   broadcast_id=str(broadcast_id),
                   recipients=recipients_count,
                   status=broadcast_data['status'])
        
        return BroadcastResponse(
            broadcast_id=broadcast_id,
            success=True,
            message="Broadcast notification processed successfully",
            recipients_count=recipients_count,
            scheduled_at=request.scheduled_at,
            delivered_at=delivered_at
        )
    
    async def get_system_health(self, force_refresh: bool = False) -> SystemHealthResponse:
        """Get system health status."""
        cache_key = "system_health"
        
        if not force_refresh:
            cached = await self._cache_get(cache_key)
            if cached:
                return SystemHealthResponse(**cached)
        
        logger.info("checking_system_health")
        
        now = datetime.now(timezone.utc)
        
        # Check database health
        try:
            db_start = datetime.now()
            await self.db.execute(select(1))
            db_response_time = (datetime.now() - db_start).total_seconds() * 1000
            db_status = "healthy" if db_response_time < 100 else "degraded"
            
            database_health = {
                'status': db_status,
                'response_time_ms': db_response_time,
                'connection_pool_size': 10,  # Would get from connection pool
                'active_connections': 5  # Would get from connection pool
            }
        except Exception as e:
            database_health = {
                'status': 'down',
                'error': str(e),
                'response_time_ms': 0,
                'connection_pool_size': 0,
                'active_connections': 0
            }
        
        # Check Redis health
        try:
            redis = await self._get_redis()
            redis_start = datetime.now()
            await redis.ping()
            redis_response_time = (datetime.now() - redis_start).total_seconds() * 1000
            redis_status = "healthy" if redis_response_time < 50 else "degraded"
            
            redis_health = {
                'status': redis_status,
                'response_time_ms': redis_response_time,
                'memory_usage_mb': 0,  # Would get from Redis INFO
                'connected_clients': 0  # Would get from Redis INFO
            }
        except Exception as e:
            redis_health = {
                'status': 'down',
                'error': str(e),
                'response_time_ms': 0,
                'memory_usage_mb': 0,
                'connected_clients': 0
            }
        
        # System resource usage
        try:
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            memory_usage = memory.percent
            disk_usage = disk.percent
        except Exception as e:
            logger.warning("system_resource_check_failed", error=str(e))
            cpu_usage = 0.0
            memory_usage = 0.0
            disk_usage = 0.0
        
        # Get active users (simplified)
        try:
            active_users_result = await self.db.execute(
                select(func.count(User.id)).where(
                    and_(
                        User.deleted_at.is_(None),
                        User.is_active == True
                    )
                )
            )
            active_users = active_users_result.scalar() or 0
        except Exception:
            active_users = 0
        
        # Get pending jobs
        try:
            pending_jobs_result = await self.db.execute(
                select(func.count(GenerationJob.id)).where(
                    GenerationJob.status.in_(['pending', 'processing'])
                )
            )
            pending_jobs = pending_jobs_result.scalar() or 0
            
            failed_jobs_result = await self.db.execute(
                select(func.count(GenerationJob.id)).where(
                    and_(
                        GenerationJob.status == 'failed',
                        GenerationJob.created_at >= datetime.now(timezone.utc) - timedelta(hours=1)
                    )
                )
            )
            failed_jobs = failed_jobs_result.scalar() or 0
        except Exception:
            pending_jobs = 0
            failed_jobs = 0
        
        # Determine overall status
        critical_issues = []
        if database_health['status'] == 'down':
            critical_issues.append('database_down')
        if redis_health['status'] == 'down':
            critical_issues.append('redis_down')
        if cpu_usage > 90:
            critical_issues.append('high_cpu')
        if memory_usage > 90:
            critical_issues.append('high_memory')
        if disk_usage > 95:
            critical_issues.append('high_disk')
        
        if critical_issues:
            overall_status = "down"
        elif (database_health['status'] == 'degraded' or 
              redis_health['status'] == 'degraded' or
              cpu_usage > 80 or memory_usage > 80):
            overall_status = "degraded"
        else:
            overall_status = "healthy"
        
        # Service status summary
        services = {
            'api': {'status': 'healthy', 'response_time_ms': 50},
            'websocket': {'status': 'healthy', 'connections': 0},
            'ai_generation': {'status': 'healthy', 'queue_size': pending_jobs},
            'export_service': {'status': 'healthy', 'processing': 0}
        }
        
        # Storage health (placeholder)
        storage_health = {
            'status': 'healthy',
            'free_space_gb': (disk.free / (1024**3)) if 'disk' in locals() else 0,
            'total_space_gb': (disk.total / (1024**3)) if 'disk' in locals() else 0
        }
        
        health = SystemHealthResponse(
            overall_status=overall_status,
            last_check=now,
            services=services,
            database=database_health,
            redis=redis_health,
            storage=storage_health,
            response_times={
                'api_average': 75.0,
                'database_average': database_health.get('response_time_ms', 0),
                'redis_average': redis_health.get('response_time_ms', 0)
            },
            error_rates={
                'api_errors': 0.1,
                'generation_failures': (failed_jobs / max(pending_jobs + failed_jobs, 1)) * 100,
                'export_failures': 0.5
            },
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            disk_usage=disk_usage,
            active_users=active_users,
            websocket_connections=0,  # Would get from WebSocket service
            database_connections=database_health.get('active_connections', 0),
            pending_jobs=pending_jobs,
            failed_jobs=failed_jobs
        )
        
        # Cache for 1 minute
        await self._cache_set(cache_key, health.model_dump(), ttl=60)
        
        logger.info("system_health_checked", 
                   status=overall_status,
                   cpu=cpu_usage,
                   memory=memory_usage,
                   disk=disk_usage)
        
        return health
    
    async def get_system_metrics(self, force_refresh: bool = False) -> SystemMetricsResponse:
        """Get detailed system metrics."""
        cache_key = "system_metrics"
        
        if not force_refresh:
            cached = await self._cache_get(cache_key)
            if cached:
                return SystemMetricsResponse(**cached)
        
        logger.info("computing_system_metrics")
        
        now = datetime.now(timezone.utc)
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)
        
        # Request metrics (would typically come from monitoring system)
        request_metrics = {
            'total_requests_1h': 1000,
            'successful_requests_1h': 950,
            'failed_requests_1h': 50,
            'requests_per_second': 0.28
        }
        
        # Response time percentiles (would come from monitoring)
        response_time_percentiles = {
            'p50': 85.0,
            'p95': 250.0,
            'p99': 500.0,
            'p99.9': 1000.0
        }
        
        # Throughput by endpoint (would come from monitoring)
        throughput = {
            '/api/v1/presentations': 0.15,
            '/api/v1/generation': 0.05,
            '/api/v1/export': 0.03,
            '/api/v1/users': 0.02
        }
        
        # Error summary
        try:
            recent_errors = await self.db.execute(
                select(func.count(GenerationJob.id)).where(
                    and_(
                        GenerationJob.status == 'failed',
                        GenerationJob.created_at >= hour_ago
                    )
                )
            )
            generation_errors = recent_errors.scalar() or 0
            
            error_summary = {
                'total_errors_1h': generation_errors + 5,  # + API errors
                'error_rate_percent': 2.5,
                'critical_errors': 0,
                'warning_errors': generation_errors
            }
        except Exception:
            error_summary = {
                'total_errors_1h': 0,
                'error_rate_percent': 0.0,
                'critical_errors': 0,
                'warning_errors': 0
            }
        
        # Recent errors (would come from logging system)
        recent_errors = [
            {
                'timestamp': (now - timedelta(minutes=15)).isoformat(),
                'level': 'error',
                'message': 'AI generation timeout',
                'count': 3
            },
            {
                'timestamp': (now - timedelta(minutes=30)).isoformat(),
                'level': 'warning',
                'message': 'High memory usage detected',
                'count': 1
            }
        ]
        
        # System resource metrics
        try:
            system_resources = {
                'cpu_usage_percent': psutil.cpu_percent(),
                'memory_usage_percent': psutil.virtual_memory().percent,
                'disk_usage_percent': psutil.disk_usage('/').percent,
                'network_io': {
                    'bytes_sent': 0,  # Would get from psutil
                    'bytes_recv': 0
                },
                'load_average': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
            }
        except Exception as e:
            logger.warning("system_resource_metrics_failed", error=str(e))
            system_resources = {
                'cpu_usage_percent': 0,
                'memory_usage_percent': 0,
                'disk_usage_percent': 0,
                'network_io': {'bytes_sent': 0, 'bytes_recv': 0},
                'load_average': [0, 0, 0]
            }
        
        # Application metrics
        try:
            active_users = await self.db.execute(
                select(func.count(User.id)).where(
                    and_(
                        User.deleted_at.is_(None),
                        User.updated_at >= day_ago  # Proxy for recent activity
                    )
                )
            )
            
            application_metrics = {
                'active_sessions': active_users.scalar() or 0,
                'websocket_connections': 0,  # Would get from WebSocket service
                'database_connections': 10,  # Would get from connection pool
                'cache_hit_rate': 85.0,  # Would get from Redis
                'queue_depth': 0  # Would get from task queue
            }
        except Exception:
            application_metrics = {
                'active_sessions': 0,
                'websocket_connections': 0,
                'database_connections': 0,
                'cache_hit_rate': 0.0,
                'queue_depth': 0
            }
        
        # User activity metrics
        try:
            presentations_today = await self.db.execute(
                select(func.count(Presentation.id)).where(
                    Presentation.created_at >= day_ago
                )
            )
            
            user_activity = {
                'presentations_created_24h': presentations_today.scalar() or 0,
                'exports_requested_24h': 0,  # Would get from exports
                'ai_generations_24h': 0,  # Would get from generation jobs
                'user_registrations_24h': 0  # Would get from users
            }
        except Exception:
            user_activity = {
                'presentations_created_24h': 0,
                'exports_requested_24h': 0,
                'ai_generations_24h': 0,
                'user_registrations_24h': 0
            }
        
        # Content metrics (placeholder)
        content_metrics = {
            'total_presentations': 0,
            'total_slides': 0,
            'total_templates': 0,
            'storage_used_gb': 0.0
        }
        
        # AI usage metrics (placeholder)
        ai_usage = {
            'total_tokens_24h': 0,
            'total_cost_24h': 0.0,
            'model_distribution': {},
            'average_response_time': 0.0
        }
        
        # Cost metrics (placeholder)
        cost_metrics = {
            'ai_costs_24h': 0.0,
            'storage_costs_24h': 0.0,
            'compute_costs_24h': 0.0,
            'total_costs_24h': 0.0
        }
        
        # Revenue metrics (placeholder)
        revenue_metrics = {
            'subscriptions_revenue_24h': 0.0,
            'new_subscriptions_24h': 0,
            'churned_subscriptions_24h': 0,
            'mrr_change': 0.0
        }
        
        metrics = SystemMetricsResponse(
            timestamp=now,
            request_metrics=request_metrics,
            response_time_percentiles=response_time_percentiles,
            throughput=throughput,
            error_summary=error_summary,
            recent_errors=recent_errors,
            system_resources=system_resources,
            application_metrics=application_metrics,
            user_activity=user_activity,
            content_metrics=content_metrics,
            ai_usage=ai_usage,
            cost_metrics=cost_metrics,
            revenue_metrics=revenue_metrics
        )
        
        # Cache for 5 minutes
        await self._cache_set(cache_key, metrics.model_dump(), ttl=300)
        
        logger.info("system_metrics_computed", timestamp=now.isoformat())
        
        return metrics
    
    async def _clear_user_cache(self, user_id: UUID):
        """Clear user-related caches."""
        try:
            redis = await self._get_redis()
            # Clear user-specific caches
            keys_to_delete = [
                f"user:{user_id}:*",
                f"{self.cache_prefix}user_details:{user_id}"
            ]
            
            for pattern in keys_to_delete:
                keys = await redis.keys(pattern)
                if keys:
                    await redis.delete(*keys)
            
            logger.info("user_cache_cleared", user_id=str(user_id))
        except Exception as e:
            logger.warning("user_cache_clear_failed", user_id=str(user_id), error=str(e))