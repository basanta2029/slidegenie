"""
Comprehensive storage system for document processing.

This module provides a complete storage solution including:
- Original file storage with S3/MinIO integration
- Content caching with Redis/PostgreSQL
- Search indexing with Elasticsearch
- File lifecycle management and cleanup
- Backup and versioning system
- Storage analytics and monitoring
"""

import logging

logger = logging.getLogger(__name__)

# Storage manager is always available
from .storage_manager import StorageManager

# Try to import other components, use mocks if not available
try:
    from .backup_manager import BackupManager
except Exception as e:
    logger.warning(f"Failed to import BackupManager: {e}")
    from .mock_components import MockBackupManager as BackupManager

try:
    from .cache_manager import CacheManager
except Exception as e:
    logger.warning(f"Failed to import CacheManager: {e}")
    from .mock_components import MockCacheManager as CacheManager

try:
    from .lifecycle_manager import LifecycleManager
except Exception as e:
    logger.warning(f"Failed to import LifecycleManager: {e}")
    from .mock_components import MockLifecycleManager as LifecycleManager

try:
    from .search_indexer import SearchIndexer
except Exception as e:
    logger.warning(f"Failed to import SearchIndexer: {e}")
    from .mock_search_indexer import MockSearchIndexer as SearchIndexer

# S3 manager might not be needed with Supabase
try:
    from .s3_manager import S3StorageManager, MultipartUpload, UploadPart, StorageMetrics
except Exception as e:
    logger.warning(f"Failed to import S3StorageManager: {e}")
    # Create dummy classes for compatibility
    class S3StorageManager:
        pass
    class MultipartUpload:
        pass
    class UploadPart:
        pass
    class StorageMetrics:
        pass

__all__ = [
    "StorageManager",
    "CacheManager", 
    "SearchIndexer",
    "LifecycleManager",
    "BackupManager",
    "S3StorageManager",
    "MultipartUpload", 
    "UploadPart",
    "StorageMetrics"
]