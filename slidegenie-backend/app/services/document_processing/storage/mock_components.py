"""
Mock implementations for storage components in MVP mode.

These provide simple in-memory implementations when Redis,
Elasticsearch, and other services are not available.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class MockCacheManager:
    """Mock cache manager using in-memory storage."""
    
    def __init__(self):
        self.cache = {}
        self.processed_content = {}
        self.hits = 0
        self.misses = 0
        logger.info("MockCacheManager initialized")
    
    async def initialize(self) -> None:
        """Initialize cache manager."""
        logger.info("MockCacheManager initialized successfully")
    
    async def get_document_data(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get document data from cache."""
        if file_id in self.cache:
            self.hits += 1
            return self.cache[file_id]
        self.misses += 1
        return None
    
    async def cache_processed_content(self, file_id: str, content: Dict[str, Any]) -> bool:
        """Cache processed content."""
        self.processed_content[file_id] = content
        return True
    
    async def get_processed_content(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get processed content from cache."""
        return self.processed_content.get(file_id)
    
    async def delete_document_data(self, file_id: str) -> bool:
        """Delete document data from cache."""
        deleted = False
        if file_id in self.cache:
            del self.cache[file_id]
            deleted = True
        if file_id in self.processed_content:
            del self.processed_content[file_id]
            deleted = True
        return deleted
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get cache metrics."""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0.0
        
        return {
            "total_keys": len(self.cache) + len(self.processed_content),
            "total_size_mb": 0.1,  # Mock size
            "hit_rate": hit_rate,
            "hit_count": self.hits,
            "miss_count": self.misses,
            "avg_response_time_ms": 0.1
        }
    
    async def optimize(self) -> Dict[str, Any]:
        """Optimize cache (no-op for mock)."""
        return {"optimized": True, "cleared": 0}
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check."""
        return {"status": "healthy", "issues": []}


class MockLifecycleManager:
    """Mock lifecycle manager for file lifecycle operations."""
    
    def __init__(self):
        self.soft_deleted = set()
        self.temp_files = {}
        logger.info("MockLifecycleManager initialized")
    
    async def initialize(self) -> None:
        """Initialize lifecycle manager."""
        logger.info("MockLifecycleManager initialized successfully")
    
    async def mark_for_deletion(self, file_id: str, user_id: UUID) -> bool:
        """Mark file for soft deletion."""
        self.soft_deleted.add(file_id)
        logger.info(f"Marked file {file_id} for deletion")
        return True
    
    async def restore_file(self, file_id: str, user_id: UUID) -> bool:
        """Restore soft-deleted file."""
        if file_id in self.soft_deleted:
            self.soft_deleted.remove(file_id)
            logger.info(f"Restored file {file_id}")
            return True
        return False
    
    async def get_file_status(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get file lifecycle status."""
        status = "active"
        if file_id in self.soft_deleted:
            status = "soft_deleted"
        
        return {
            "file_id": file_id,
            "status": status,
            "age_days": 0.1
        }
    
    async def create_temp_file(self, content: bytes, suffix: str = "", prefix: str = "") -> tuple:
        """Create temporary file."""
        import tempfile
        from pathlib import Path
        
        with tempfile.NamedTemporaryFile(suffix=suffix, prefix=prefix, delete=False) as tmp:
            tmp.write(content)
            temp_id = str(UUID())
            self.temp_files[temp_id] = tmp.name
            return temp_id, Path(tmp.name)
    
    async def cleanup_temp_file(self, temp_id: str) -> bool:
        """Clean up temporary file."""
        if temp_id in self.temp_files:
            try:
                import os
                os.unlink(self.temp_files[temp_id])
                del self.temp_files[temp_id]
                return True
            except:
                pass
        return False
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get lifecycle metrics."""
        return {
            "active_files": 10,  # Mock count
            "archived_files": 0,
            "soft_deleted_files": len(self.soft_deleted),
            "temp_files": len(self.temp_files),
            "oldest_file_days": 1.0,
            "last_cleanup": datetime.utcnow()
        }
    
    async def run_cleanup(self) -> Dict[str, Any]:
        """Run cleanup operations."""
        return {"cleaned": 0, "errors": 0}
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check."""
        return {"status": "healthy", "issues": []}


class MockBackupManager:
    """Mock backup manager for file backup operations."""
    
    def __init__(self):
        self.scheduled_backups = set()
        logger.info("MockBackupManager initialized")
    
    async def initialize(self) -> None:
        """Initialize backup manager."""
        logger.info("MockBackupManager initialized successfully")
    
    async def schedule_backup(self, file_id: str, user_id: UUID) -> bool:
        """Schedule file for backup."""
        self.scheduled_backups.add(file_id)
        logger.info(f"Scheduled backup for file {file_id}")
        return True
    
    async def delete_backups(self, file_id: str) -> bool:
        """Delete file backups."""
        if file_id in self.scheduled_backups:
            self.scheduled_backups.remove(file_id)
        return True
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get backup metrics."""
        return {
            "total_backups": len(self.scheduled_backups),
            "successful_backups": len(self.scheduled_backups),
            "failed_backups": 0,
            "backup_success_rate": 1.0,
            "total_backup_size_mb": 0.1,
            "average_backup_time_seconds": 1.0,
            "status": "healthy"
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check."""
        return {"status": "healthy", "issues": []}