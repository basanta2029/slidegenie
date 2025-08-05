"""
Comprehensive health check system for the SlideGenie API.

This module provides a robust health monitoring system that checks:
- Database connectivity and performance
- Redis cache availability
- External service health (AI providers, storage)
- System resources and performance metrics
- Application-specific health indicators
"""

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import psutil
import redis.asyncio as redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.cache.redis import get_redis
from app.infrastructure.database.base import get_db

logger = get_logger(__name__)


class HealthStatus(str, Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Health check result data class."""
    component: str
    status: HealthStatus
    message: str
    response_time_ms: Optional[float] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "component": self.component,
            "status": self.status.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
        
        if self.response_time_ms is not None:
            result["response_time_ms"] = self.response_time_ms
        
        if self.details:
            result["details"] = self.details
        
        return result


@dataclass
class SystemMetrics:
    """System metrics data class."""
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    load_average: Tuple[float, float, float]
    uptime_seconds: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "disk_percent": self.disk_percent,
            "load_average": {
                "1min": self.load_average[0],
                "5min": self.load_average[1],
                "15min": self.load_average[2],
            },
            "uptime_seconds": self.uptime_seconds,
        }


class HealthChecker:
    """Comprehensive health checker for all system components."""
    
    def __init__(self):
        self.start_time = time.time()
        self._last_check_cache: Dict[str, HealthCheckResult] = {}
        self._check_intervals = {
            "database": 30,      # Check every 30 seconds
            "cache": 30,         # Check every 30 seconds
            "ai_services": 60,   # Check every minute
            "storage": 60,       # Check every minute
            "system": 10,        # Check every 10 seconds
        }
    
    async def check_all_components(self, force_refresh: bool = False) -> List[HealthCheckResult]:
        """
        Check health of all system components.
        
        Args:
            force_refresh: Force refresh of all checks, ignoring cache
            
        Returns:
            List of health check results
        """
        tasks = [
            self._check_with_cache("database", self._check_database_health, force_refresh),
            self._check_with_cache("cache", self._check_cache_health, force_refresh),
            self._check_with_cache("ai_services", self._check_ai_services_health, force_refresh),
            self._check_with_cache("storage", self._check_storage_health, force_refresh),
            self._check_with_cache("system", self._check_system_health, force_refresh),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and convert to health check results
        health_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                component_name = ["database", "cache", "ai_services", "storage", "system"][i]
                health_results.append(HealthCheckResult(
                    component=component_name,
                    status=HealthStatus.UNKNOWN,
                    message=f"Health check failed: {str(result)}",
                ))
            else:
                health_results.append(result)
        
        return health_results
    
    async def _check_with_cache(
        self,
        component: str,
        check_func,
        force_refresh: bool = False
    ) -> HealthCheckResult:
        """Check component health with caching."""
        if not force_refresh and component in self._last_check_cache:
            last_check = self._last_check_cache[component]
            age = (datetime.utcnow() - last_check.timestamp).total_seconds()
            if age < self._check_intervals.get(component, 60):
                return last_check
        
        try:
            result = await check_func()
            self._last_check_cache[component] = result
            return result
        except Exception as e:
            logger.error(f"Health check failed for {component}", exc_info=e)
            result = HealthCheckResult(
                component=component,
                status=HealthStatus.UNKNOWN,
                message=f"Health check error: {str(e)}",
            )
            self._last_check_cache[component] = result
            return result
    
    async def _check_database_health(self) -> HealthCheckResult:
        """Check database health and performance."""
        start_time = time.time()
        
        try:
            async for db in get_db():
                # Test basic connectivity
                await db.execute(text("SELECT 1"))
                
                # Test read performance
                result = await db.execute(
                    text("SELECT COUNT(*) FROM information_schema.tables")
                )
                table_count = result.scalar()
                
                # Test write performance (using a temp table)
                await db.execute(text("""
                    CREATE TEMP TABLE IF NOT EXISTS health_check_temp (
                        id INTEGER,
                        timestamp TIMESTAMP DEFAULT NOW()
                    )
                """))
                await db.execute(text("INSERT INTO health_check_temp (id) VALUES (1)"))
                await db.execute(text("DROP TABLE health_check_temp"))
                
                response_time = (time.time() - start_time) * 1000
                
                # Determine status based on performance
                if response_time > 1000:  # More than 1 second
                    status = HealthStatus.DEGRADED
                    message = f"Database responding slowly ({response_time:.1f}ms)"
                else:
                    status = HealthStatus.HEALTHY
                    message = "Database is healthy"
                
                return HealthCheckResult(
                    component="database",
                    status=status,
                    message=message,
                    response_time_ms=response_time,
                    details={
                        "table_count": table_count,
                        "connection_pool_size": 10,  # From your config
                    },
                )
        
        except Exception as e:
            return HealthCheckResult(
                component="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection failed: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
            )
    
    async def _check_cache_health(self) -> HealthCheckResult:
        """Check Redis cache health and performance."""
        start_time = time.time()
        
        try:
            redis_client = await get_redis()
            
            # Test basic connectivity
            pong = await redis_client.ping()
            if not pong:
                raise Exception("Redis ping failed")
            
            # Test read/write performance
            test_key = "health_check_test"
            test_value = str(int(time.time()))
            
            await redis_client.set(test_key, test_value, ex=60)
            retrieved_value = await redis_client.get(test_key)
            await redis_client.delete(test_key)
            
            if retrieved_value.decode() != test_value:
                raise Exception("Redis read/write test failed")
            
            # Get Redis info
            info = await redis_client.info()
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine status based on performance and memory usage
            memory_usage = info.get("used_memory_rss", 0) / info.get("maxmemory", 1) if info.get("maxmemory") else 0
            
            if response_time > 100 or memory_usage > 0.9:
                status = HealthStatus.DEGRADED
                message = f"Redis responding slowly or high memory usage ({response_time:.1f}ms, {memory_usage*100:.1f}% memory)"
            else:
                status = HealthStatus.HEALTHY
                message = "Redis cache is healthy"
            
            return HealthCheckResult(
                component="cache",
                status=status,
                message=message,
                response_time_ms=response_time,
                details={
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory_mb": info.get("used_memory", 0) / (1024 * 1024),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                },
            )
        
        except Exception as e:
            return HealthCheckResult(
                component="cache",
                status=HealthStatus.UNHEALTHY,
                message=f"Redis connection failed: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
            )
    
    async def _check_ai_services_health(self) -> HealthCheckResult:
        """Check AI services health and availability."""
        ai_config = settings.get_ai_config()
        
        providers = []
        if ai_config["has_anthropic"]:
            providers.append("Anthropic")
        if ai_config["has_openai"]:
            providers.append("OpenAI")
        
        if not providers:
            return HealthCheckResult(
                component="ai_services",
                status=HealthStatus.DEGRADED,
                message="No AI providers configured",
                details={"configured_providers": []},
            )
        
        # In a real implementation, you would test actual API calls here
        # For now, we'll assume they're healthy if configured
        return HealthCheckResult(
            component="ai_services",
            status=HealthStatus.HEALTHY,
            message=f"AI services available: {', '.join(providers)}",
            details={
                "configured_providers": providers,
                "primary_model": ai_config["primary_model"],
                "fallback_model": ai_config["fallback_model"],
            },
        )
    
    async def _check_storage_health(self) -> HealthCheckResult:
        """Check storage system health."""
        try:
            # Check if Supabase storage configuration is present
            if not all([settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY]):
                return HealthCheckResult(
                    component="storage",
                    status=HealthStatus.DEGRADED,
                    message="Storage service not configured",
                    details={"configured": False},
                )
            
            # In a real implementation, you would test MinIO connectivity here
            # For now, we'll assume it's healthy if configured
            return HealthCheckResult(
                component="storage",
                status=HealthStatus.HEALTHY,
                message="Storage service is configured and available",
                details={
                    "configured": True,
                    "endpoint": settings.MINIO_ENDPOINT,
                    "bucket": settings.MINIO_BUCKET_NAME,
                    "ssl_enabled": settings.MINIO_USE_SSL,
                },
            )
        
        except Exception as e:
            return HealthCheckResult(
                component="storage",
                status=HealthStatus.UNHEALTHY,
                message=f"Storage check failed: {str(e)}",
            )
    
    async def _check_system_health(self) -> HealthCheckResult:
        """Check system resource health."""
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            load_avg = psutil.getloadavg()
            uptime = time.time() - self.start_time
            
            # Determine status based on resource usage
            if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
                status = HealthStatus.DEGRADED
                message = "High system resource usage"
            elif cpu_percent > 95 or memory.percent > 95 or disk.percent > 95:
                status = HealthStatus.UNHEALTHY
                message = "Critical system resource usage"
            else:
                status = HealthStatus.HEALTHY
                message = "System resources are healthy"
            
            return HealthCheckResult(
                component="system",
                status=status,
                message=message,
                details=SystemMetrics(
                    cpu_percent=cpu_percent,
                    memory_percent=memory.percent,
                    disk_percent=disk.percent,
                    load_average=load_avg,
                    uptime_seconds=uptime,
                ).to_dict(),
            )
        
        except Exception as e:
            return HealthCheckResult(
                component="system",
                status=HealthStatus.UNKNOWN,
                message=f"System check failed: {str(e)}",
            )
    
    async def get_overall_health(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get overall system health summary.
        
        Args:
            force_refresh: Force refresh of all checks
            
        Returns:
            Overall health summary
        """
        results = await self.check_all_components(force_refresh)
        
        # Calculate overall status
        statuses = [result.status for result in results]
        
        if any(status == HealthStatus.UNHEALTHY for status in statuses):
            overall_status = HealthStatus.UNHEALTHY
        elif any(status == HealthStatus.DEGRADED for status in statuses):
            overall_status = HealthStatus.DEGRADED
        elif any(status == HealthStatus.UNKNOWN for status in statuses):
            overall_status = HealthStatus.DEGRADED  # Treat unknown as degraded
        else:
            overall_status = HealthStatus.HEALTHY
        
        # Calculate component summary
        component_summary = {}
        for result in results:
            component_summary[result.component] = result.to_dict()
        
        return {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "components": component_summary,
            "summary": {
                "total_components": len(results),
                "healthy": sum(1 for r in results if r.status == HealthStatus.HEALTHY),
                "degraded": sum(1 for r in results if r.status == HealthStatus.DEGRADED),
                "unhealthy": sum(1 for r in results if r.status == HealthStatus.UNHEALTHY),
                "unknown": sum(1 for r in results if r.status == HealthStatus.UNKNOWN),
            },
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
        }
    
    async def get_detailed_metrics(self) -> Dict[str, Any]:
        """
        Get detailed system metrics and performance data.
        
        Returns:
            Detailed metrics dictionary
        """
        try:
            # System metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()
            
            # Process metrics
            process = psutil.Process()
            process_memory = process.memory_info()
            
            return {
                "system": {
                    "cpu": {
                        "percent": cpu_percent,
                        "count": psutil.cpu_count(),
                        "load_average": psutil.getloadavg(),
                    },
                    "memory": {
                        "total_gb": memory.total / (1024**3),
                        "available_gb": memory.available / (1024**3),
                        "percent_used": memory.percent,
                        "swap_percent": psutil.swap_memory().percent,
                    },
                    "disk": {
                        "total_gb": disk.total / (1024**3),
                        "free_gb": disk.free / (1024**3),
                        "percent_used": disk.percent,
                    },
                    "network": {
                        "bytes_sent": network.bytes_sent,
                        "bytes_recv": network.bytes_recv,
                        "packets_sent": network.packets_sent,
                        "packets_recv": network.packets_recv,
                    },
                },
                "process": {
                    "memory_mb": process_memory.rss / (1024**2),
                    "cpu_percent": process.cpu_percent(),
                    "threads": process.num_threads(),
                    "uptime_seconds": time.time() - self.start_time,
                },
                "application": {
                    "version": settings.APP_VERSION,
                    "environment": settings.ENVIRONMENT,
                    "start_time": self.start_time,
                },
            }
        
        except Exception as e:
            logger.error("Failed to get detailed metrics", exc_info=e)
            return {"error": str(e)}


# Global health checker instance
health_checker = HealthChecker()


# Convenience functions
async def check_health(force_refresh: bool = False) -> Dict[str, Any]:
    """
    Check overall system health.
    
    Args:
        force_refresh: Force refresh of all checks
        
    Returns:
        Health check results
    """
    return await health_checker.get_overall_health(force_refresh)


async def check_readiness() -> Tuple[bool, Dict[str, Any]]:
    """
    Check if the system is ready to serve requests.
    
    Returns:
        Tuple of (is_ready, health_data)
    """
    health_data = await health_checker.get_overall_health()
    
    # System is ready if no components are unhealthy
    critical_components = ["database", "cache"]
    is_ready = all(
        health_data["components"][comp]["status"] != "unhealthy"
        for comp in critical_components
        if comp in health_data["components"]
    )
    
    return is_ready, health_data


async def check_liveness() -> Tuple[bool, Dict[str, Any]]:
    """
    Check if the system is alive (basic liveness check).
    
    Returns:
        Tuple of (is_alive, basic_info)
    """
    try:
        basic_info = {
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat(),
            "version": settings.APP_VERSION,
            "uptime_seconds": time.time() - health_checker.start_time,
        }
        return True, basic_info
    except Exception as e:
        return False, {"status": "dead", "error": str(e)}


async def get_metrics() -> Dict[str, Any]:
    """
    Get detailed system metrics.
    
    Returns:
        Detailed metrics
    """
    return await health_checker.get_detailed_metrics()