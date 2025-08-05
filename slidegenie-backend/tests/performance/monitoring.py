"""
Performance monitoring utilities for real-time metrics collection.
"""
import os
import time
import psutil
import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from collections import deque
import aiohttp
import asyncpg
import redis.asyncio as redis
from prometheus_client import Counter, Histogram, Gauge, generate_latest


# Prometheus metrics
request_count = Counter('slidegenie_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('slidegenie_request_duration_seconds', 'Request duration', ['method', 'endpoint'])
active_connections = Gauge('slidegenie_active_connections', 'Active connections', ['type'])
queue_size = Gauge('slidegenie_queue_size', 'Queue size', ['queue_name'])
db_pool_size = Gauge('slidegenie_db_pool_size', 'Database connection pool size')
cache_hit_rate = Gauge('slidegenie_cache_hit_rate', 'Cache hit rate')
memory_usage = Gauge('slidegenie_memory_usage_bytes', 'Memory usage in bytes', ['type'])
cpu_usage = Gauge('slidegenie_cpu_usage_percent', 'CPU usage percentage')


@dataclass
class SystemMetrics:
    """System-level metrics."""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    network_sent_mb: float
    network_recv_mb: float
    open_files: int
    thread_count: int
    

@dataclass
class ApplicationMetrics:
    """Application-level metrics."""
    timestamp: float
    active_users: int
    active_websockets: int
    queue_sizes: Dict[str, int]
    db_connections_active: int
    db_connections_idle: int
    cache_operations_per_sec: float
    ai_api_calls_per_min: float
    error_rate_percent: float
    

class PerformanceMonitor:
    """Real-time performance monitoring."""
    
    def __init__(
        self,
        api_base_url: str,
        db_url: str,
        redis_url: str,
        sample_interval: float = 1.0
    ):
        self.api_base_url = api_base_url
        self.db_url = db_url
        self.redis_url = redis_url
        self.sample_interval = sample_interval
        
        # Metrics storage
        self.system_metrics: deque = deque(maxlen=3600)  # 1 hour at 1s interval
        self.app_metrics: deque = deque(maxlen=3600)
        
        # State tracking
        self.running = False
        self.start_time = None
        self.network_baseline = None
        
        # Connections
        self.db_pool: Optional[asyncpg.Pool] = None
        self.redis_client: Optional[redis.Redis] = None
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def start(self):
        """Start monitoring."""
        self.running = True
        self.start_time = time.time()
        
        # Initialize connections
        self.db_pool = await asyncpg.create_pool(self.db_url, min_size=1, max_size=5)
        self.redis_client = await redis.from_url(self.redis_url)
        self.session = aiohttp.ClientSession()
        
        # Get network baseline
        net_io = psutil.net_io_counters()
        self.network_baseline = {
            'sent': net_io.bytes_sent,
            'recv': net_io.bytes_recv
        }
        
        # Start monitoring tasks
        await asyncio.gather(
            self._monitor_system(),
            self._monitor_application(),
            self._monitor_database(),
            self._monitor_queues()
        )
        
    async def stop(self):
        """Stop monitoring."""
        self.running = False
        
        # Close connections
        if self.db_pool:
            await self.db_pool.close()
        if self.redis_client:
            await self.redis_client.close()
        if self.session:
            await self.session.close()
            
    async def _monitor_system(self):
        """Monitor system-level metrics."""
        while self.running:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=0.1)
                
                # Memory usage
                memory = psutil.virtual_memory()
                
                # Disk usage
                disk = psutil.disk_usage('/')
                
                # Network I/O
                net_io = psutil.net_io_counters()
                network_sent_mb = (net_io.bytes_sent - self.network_baseline['sent']) / (1024 * 1024)
                network_recv_mb = (net_io.bytes_recv - self.network_baseline['recv']) / (1024 * 1024)
                
                # Process info
                process = psutil.Process()
                
                metrics = SystemMetrics(
                    timestamp=time.time(),
                    cpu_percent=cpu_percent,
                    memory_percent=memory.percent,
                    memory_used_mb=memory.used / (1024 * 1024),
                    memory_available_mb=memory.available / (1024 * 1024),
                    disk_usage_percent=disk.percent,
                    network_sent_mb=network_sent_mb,
                    network_recv_mb=network_recv_mb,
                    open_files=len(process.open_files()),
                    thread_count=process.num_threads()
                )
                
                self.system_metrics.append(metrics)
                
                # Update Prometheus metrics
                cpu_usage.set(cpu_percent)
                memory_usage.labels(type='used').set(memory.used)
                memory_usage.labels(type='available').set(memory.available)
                
            except Exception as e:
                print(f"System monitoring error: {e}")
                
            await asyncio.sleep(self.sample_interval)
            
    async def _monitor_application(self):
        """Monitor application-level metrics."""
        error_count = 0
        request_count = 0
        last_check = time.time()
        
        while self.running:
            try:
                # Get application stats from API
                async with self.session.get(f"{self.api_base_url}/api/v1/admin/stats") as resp:
                    if resp.status == 200:
                        stats = await resp.json()
                        
                        # Calculate rates
                        current_time = time.time()
                        time_delta = current_time - last_check
                        
                        # Error rate
                        current_errors = stats.get('total_errors', 0)
                        current_requests = stats.get('total_requests', 0)
                        
                        error_rate = 0
                        if current_requests > request_count:
                            errors_delta = current_errors - error_count
                            requests_delta = current_requests - request_count
                            error_rate = (errors_delta / requests_delta) * 100 if requests_delta > 0 else 0
                            
                        error_count = current_errors
                        request_count = current_requests
                        last_check = current_time
                        
                        # Get queue sizes
                        queue_sizes = await self._get_queue_sizes()
                        
                        # Get database pool stats
                        db_stats = await self._get_db_pool_stats()
                        
                        metrics = ApplicationMetrics(
                            timestamp=time.time(),
                            active_users=stats.get('active_users', 0),
                            active_websockets=stats.get('active_websockets', 0),
                            queue_sizes=queue_sizes,
                            db_connections_active=db_stats['active'],
                            db_connections_idle=db_stats['idle'],
                            cache_operations_per_sec=stats.get('cache_ops_per_sec', 0),
                            ai_api_calls_per_min=stats.get('ai_calls_per_min', 0),
                            error_rate_percent=error_rate
                        )
                        
                        self.app_metrics.append(metrics)
                        
                        # Update Prometheus metrics
                        active_connections.labels(type='websocket').set(metrics.active_websockets)
                        active_connections.labels(type='http').set(metrics.active_users)
                        
                        for queue_name, size in queue_sizes.items():
                            queue_size.labels(queue_name=queue_name).set(size)
                            
            except Exception as e:
                print(f"Application monitoring error: {e}")
                
            await asyncio.sleep(self.sample_interval)
            
    async def _monitor_database(self):
        """Monitor database performance."""
        while self.running:
            try:
                # Get database statistics
                query = """
                SELECT 
                    (SELECT count(*) FROM pg_stat_activity WHERE state = 'active') as active_queries,
                    (SELECT count(*) FROM pg_stat_activity WHERE state = 'idle') as idle_connections,
                    (SELECT sum(blks_hit)::float / (sum(blks_hit) + sum(blks_read)) 
                     FROM pg_stat_database WHERE datname = current_database()) as cache_hit_ratio,
                    (SELECT count(*) FROM pg_stat_activity WHERE wait_event_type IS NOT NULL) as waiting_queries,
                    (SELECT max(age(backend_start)) FROM pg_stat_activity) as oldest_connection_age,
                    (SELECT count(*) FROM pg_locks WHERE NOT granted) as blocked_queries
                """
                
                async with self.db_pool.acquire() as conn:
                    row = await conn.fetchrow(query)
                    
                    if row:
                        # Update metrics
                        db_pool_size.set(row['active_queries'] + row['idle_connections'])
                        cache_hit_rate.set(row['cache_hit_ratio'] or 0)
                        
                        # Log if there are issues
                        if row['blocked_queries'] > 0:
                            print(f"Warning: {row['blocked_queries']} blocked queries detected")
                            
                        if row['waiting_queries'] > 10:
                            print(f"Warning: {row['waiting_queries']} queries waiting")
                            
            except Exception as e:
                print(f"Database monitoring error: {e}")
                
            await asyncio.sleep(self.sample_interval * 5)  # Less frequent DB checks
            
    async def _monitor_queues(self):
        """Monitor queue sizes and performance."""
        while self.running:
            try:
                queue_sizes = await self._get_queue_sizes()
                
                # Check for queue backlogs
                for queue_name, size in queue_sizes.items():
                    if size > 1000:
                        print(f"Warning: Queue {queue_name} has {size} items")
                        
            except Exception as e:
                print(f"Queue monitoring error: {e}")
                
            await asyncio.sleep(self.sample_interval * 2)
            
    async def _get_queue_sizes(self) -> Dict[str, int]:
        """Get current queue sizes."""
        sizes = {}
        
        try:
            # Get Redis queue sizes
            for queue_name in ['generation', 'export', 'processing']:
                size = await self.redis_client.llen(f"queue:{queue_name}")
                sizes[queue_name] = size
                
            # Get delayed job counts
            for queue_name in ['generation', 'export', 'processing']:
                delayed = await self.redis_client.zcard(f"queue:{queue_name}:delayed")
                sizes[f"{queue_name}_delayed"] = delayed
                
        except Exception as e:
            print(f"Error getting queue sizes: {e}")
            
        return sizes
        
    async def _get_db_pool_stats(self) -> Dict[str, int]:
        """Get database connection pool statistics."""
        if self.db_pool:
            return {
                'active': len([c for c in self.db_pool._holders if c.is_connected()]),
                'idle': self.db_pool.get_idle_size(),
                'total': self.db_pool.get_size()
            }
        return {'active': 0, 'idle': 0, 'total': 0}
        
    def get_summary(self) -> Dict[str, Any]:
        """Get monitoring summary."""
        if not self.system_metrics or not self.app_metrics:
            return {}
            
        # System metrics summary
        recent_system = list(self.system_metrics)[-60:]  # Last minute
        system_summary = {
            'cpu': {
                'avg': sum(m.cpu_percent for m in recent_system) / len(recent_system),
                'max': max(m.cpu_percent for m in recent_system),
                'current': recent_system[-1].cpu_percent if recent_system else 0
            },
            'memory': {
                'avg_percent': sum(m.memory_percent for m in recent_system) / len(recent_system),
                'max_percent': max(m.memory_percent for m in recent_system),
                'current_used_mb': recent_system[-1].memory_used_mb if recent_system else 0
            }
        }
        
        # Application metrics summary
        recent_app = list(self.app_metrics)[-60:]
        app_summary = {
            'users': {
                'avg': sum(m.active_users for m in recent_app) / len(recent_app),
                'max': max(m.active_users for m in recent_app),
                'current': recent_app[-1].active_users if recent_app else 0
            },
            'websockets': {
                'avg': sum(m.active_websockets for m in recent_app) / len(recent_app),
                'max': max(m.active_websockets for m in recent_app),
                'current': recent_app[-1].active_websockets if recent_app else 0
            },
            'error_rate': {
                'avg': sum(m.error_rate_percent for m in recent_app) / len(recent_app),
                'max': max(m.error_rate_percent for m in recent_app),
                'current': recent_app[-1].error_rate_percent if recent_app else 0
            }
        }
        
        return {
            'monitoring_duration_seconds': time.time() - self.start_time if self.start_time else 0,
            'system': system_summary,
            'application': app_summary,
            'latest_metrics': {
                'system': asdict(self.system_metrics[-1]) if self.system_metrics else None,
                'application': asdict(self.app_metrics[-1]) if self.app_metrics else None
            }
        }
        
    def export_metrics(self, filepath: str):
        """Export collected metrics to file."""
        data = {
            'summary': self.get_summary(),
            'system_metrics': [asdict(m) for m in self.system_metrics],
            'application_metrics': [asdict(m) for m in self.app_metrics]
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
            
    def get_prometheus_metrics(self) -> bytes:
        """Get Prometheus format metrics."""
        return generate_latest()


class AlertManager:
    """Manage performance alerts based on thresholds."""
    
    def __init__(self, thresholds: Dict[str, Dict[str, float]]):
        self.thresholds = thresholds
        self.alerts: List[Dict[str, Any]] = []
        
    def check_metrics(self, metrics: Dict[str, Any]):
        """Check metrics against thresholds and generate alerts."""
        timestamp = datetime.now().isoformat()
        
        # Check system metrics
        if 'system' in metrics:
            system = metrics['system']
            
            # CPU alerts
            if system['cpu']['current'] > self.thresholds.get('cpu_percent', 80):
                self.alerts.append({
                    'timestamp': timestamp,
                    'level': 'warning',
                    'type': 'cpu_high',
                    'message': f"CPU usage high: {system['cpu']['current']:.1f}%",
                    'value': system['cpu']['current']
                })
                
            # Memory alerts
            if system['memory']['current_used_mb'] > self.thresholds.get('memory_mb', 4096):
                self.alerts.append({
                    'timestamp': timestamp,
                    'level': 'warning',
                    'type': 'memory_high',
                    'message': f"Memory usage high: {system['memory']['current_used_mb']:.0f}MB",
                    'value': system['memory']['current_used_mb']
                })
                
        # Check application metrics
        if 'application' in metrics:
            app = metrics['application']
            
            # Error rate alerts
            if app['error_rate']['current'] > self.thresholds.get('error_rate_percent', 5):
                self.alerts.append({
                    'timestamp': timestamp,
                    'level': 'critical',
                    'type': 'error_rate_high',
                    'message': f"Error rate high: {app['error_rate']['current']:.1f}%",
                    'value': app['error_rate']['current']
                })
                
    def get_alerts(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get alerts since specified time."""
        if since:
            return [a for a in self.alerts if datetime.fromisoformat(a['timestamp']) > since]
        return self.alerts