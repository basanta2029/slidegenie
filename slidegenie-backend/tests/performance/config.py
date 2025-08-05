"""
Performance testing configuration.
"""
import os
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class LoadProfile(Enum):
    """Load testing profiles."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    STRESS = "stress"
    SPIKE = "spike"
    SOAK = "soak"


@dataclass
class PerformanceConfig:
    """Performance test configuration."""
    # API Configuration
    base_url: str = os.getenv("PERF_TEST_BASE_URL", "http://localhost:8000")
    api_prefix: str = "/api/v1"
    
    # Authentication
    test_user_email: str = os.getenv("PERF_TEST_USER_EMAIL", "perf-test@example.com")
    test_user_password: str = os.getenv("PERF_TEST_USER_PASSWORD", "test-password-123")
    admin_email: str = os.getenv("PERF_TEST_ADMIN_EMAIL", "admin@example.com")
    admin_password: str = os.getenv("PERF_TEST_ADMIN_PASSWORD", "admin-password-123")
    
    # Test Data
    sample_pdf_path: str = "tests/performance/fixtures/sample_paper.pdf"
    large_pdf_path: str = "tests/performance/fixtures/large_paper_100mb.pdf"
    sample_docx_path: str = "tests/performance/fixtures/sample_thesis.docx"
    sample_latex_path: str = "tests/performance/fixtures/sample_article.tex"
    
    # Load Profiles
    load_profiles: Dict[LoadProfile, Dict] = field(default_factory=lambda: {
        LoadProfile.DEVELOPMENT: {
            "users": 10,
            "spawn_rate": 2,
            "run_time": "2m",
            "wait_time": (1, 3)
        },
        LoadProfile.STAGING: {
            "users": 50,
            "spawn_rate": 5,
            "run_time": "10m",
            "wait_time": (2, 5)
        },
        LoadProfile.PRODUCTION: {
            "users": 100,
            "spawn_rate": 10,
            "run_time": "30m",
            "wait_time": (3, 8)
        },
        LoadProfile.STRESS: {
            "users": 500,
            "spawn_rate": 50,
            "run_time": "15m",
            "wait_time": (1, 2)
        },
        LoadProfile.SPIKE: {
            "users": 1000,
            "spawn_rate": 100,
            "run_time": "5m",
            "wait_time": (0.5, 1)
        },
        LoadProfile.SOAK: {
            "users": 200,
            "spawn_rate": 10,
            "run_time": "2h",
            "wait_time": (5, 10)
        }
    })
    
    # Performance Thresholds
    thresholds: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        "response_time": {
            "p50": 200,  # 50th percentile in ms
            "p90": 500,  # 90th percentile in ms
            "p95": 1000,  # 95th percentile in ms
            "p99": 2000   # 99th percentile in ms
        },
        "error_rate": {
            "max_percent": 1.0  # Maximum 1% error rate
        },
        "throughput": {
            "min_rps": 100  # Minimum requests per second
        }
    })
    
    # WebSocket Configuration
    websocket_url: str = field(init=False)
    websocket_heartbeat_interval: int = 30
    websocket_max_connections: int = 1000
    
    # File Upload Configuration
    max_file_size_mb: int = 100
    chunk_size_mb: int = 8
    concurrent_uploads: int = 10
    
    # Database Performance
    db_connection_pool_size: int = 50
    db_query_timeout_ms: int = 5000
    
    # Queue Performance
    queue_worker_count: int = 10
    queue_batch_size: int = 100
    queue_processing_timeout_s: int = 300
    
    def __post_init__(self):
        """Initialize computed fields."""
        self.websocket_url = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
    
    def get_profile(self, profile: LoadProfile) -> Dict:
        """Get load profile configuration."""
        return self.load_profiles.get(profile, self.load_profiles[LoadProfile.DEVELOPMENT])
    
    def get_endpoints(self) -> List[str]:
        """Get list of API endpoints to test."""
        return [
            f"{self.api_prefix}/health",
            f"{self.api_prefix}/auth/login",
            f"{self.api_prefix}/auth/register",
            f"{self.api_prefix}/presentations",
            f"{self.api_prefix}/templates",
            f"{self.api_prefix}/generation/start",
            f"{self.api_prefix}/slides",
            f"{self.api_prefix}/documents/upload",
            f"{self.api_prefix}/export/pptx",
            f"{self.api_prefix}/export/pdf",
            f"{self.api_prefix}/analytics/usage",
            f"{self.api_prefix}/admin/stats"
        ]


# Global configuration instance
config = PerformanceConfig()


# Monitoring and metrics configuration
METRICS_CONFIG = {
    "prometheus": {
        "enabled": True,
        "port": 9090,
        "path": "/metrics"
    },
    "grafana": {
        "enabled": True,
        "dashboards": [
            "api_performance",
            "websocket_connections",
            "file_processing",
            "database_queries",
            "queue_metrics"
        ]
    },
    "custom_metrics": {
        "presentation_generation_time": {
            "type": "histogram",
            "buckets": [1, 5, 10, 30, 60, 120, 300]
        },
        "file_upload_duration": {
            "type": "histogram",
            "buckets": [0.5, 1, 2, 5, 10, 30]
        },
        "websocket_message_latency": {
            "type": "histogram",
            "buckets": [10, 50, 100, 250, 500, 1000]
        },
        "ai_api_call_duration": {
            "type": "histogram",
            "buckets": [0.5, 1, 2, 5, 10, 20]
        },
        "database_query_duration": {
            "type": "histogram",
            "buckets": [1, 5, 10, 50, 100, 500]
        }
    }
}