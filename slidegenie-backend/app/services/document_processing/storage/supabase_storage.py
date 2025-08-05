"""
Supabase Storage integration for document storage.

This module provides integration with Supabase Storage for file operations.
It implements S3-compatible operations using Supabase's storage API.
"""

import io
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, BinaryIO
from urllib.parse import urlparse
from uuid import UUID

from supabase import create_client, Client
from storage3.exceptions import StorageException

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class SupabaseStorageClient:
    """
    Supabase Storage client for document storage operations.
    
    Provides methods for uploading, downloading, and managing files
    in Supabase Storage buckets.
    """
    
    def __init__(self):
        """Initialize Supabase client."""
        settings = get_settings()
        
        # Get Supabase credentials from environment
        self.supabase_url = getattr(settings, 'SUPABASE_URL', None)
        self.supabase_key = getattr(settings, 'SUPABASE_SERVICE_KEY', None)
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError(
                "Supabase credentials not configured. "
                "Please set SUPABASE_URL and SUPABASE_SERVICE_KEY in environment."
            )
        
        # Initialize Supabase client
        self.client: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Default bucket name
        self.default_bucket = getattr(settings, 'SUPABASE_STORAGE_BUCKET', 'documents')
        
        # Initialize bucket if needed
        self._ensure_bucket_exists()
        
        logger.info(f"SupabaseStorageClient initialized with bucket: {self.default_bucket}")
    
    def _ensure_bucket_exists(self) -> None:
        """Ensure the default bucket exists."""
        try:
            # List existing buckets
            buckets = self.client.storage.list_buckets()
            bucket_names = [bucket.name for bucket in buckets]
            
            if self.default_bucket not in bucket_names:
                # Create bucket with public access disabled
                self.client.storage.create_bucket(
                    self.default_bucket,
                    options={
                        "public": False,  # Private bucket for document storage
                        "file_size_limit": 52428800,  # 50MB limit
                        "allowed_mime_types": [
                            "application/pdf",
                            "text/plain",
                            "text/markdown",
                            "text/x-tex",
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                            "image/png",
                            "image/jpeg",
                            "image/gif"
                        ]
                    }
                )
                logger.info(f"Created bucket: {self.default_bucket}")
        except Exception as e:
            logger.error(f"Error ensuring bucket exists: {e}")
            # Continue anyway - bucket might already exist
    
    def upload_file(
        self,
        file_key: str,
        file_content: Union[bytes, BinaryIO],
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Upload a file to Supabase Storage.
        
        Args:
            file_key: Storage path/key for the file
            file_content: File content as bytes or file-like object
            content_type: MIME type of the file
            metadata: Additional metadata to store
            
        Returns:
            Upload result with file info
        """
        try:
            # Ensure file_content is bytes
            if hasattr(file_content, 'read'):
                file_bytes = file_content.read()
            else:
                file_bytes = file_content
            
            # Prepare options
            options = {}
            if content_type:
                options['content-type'] = content_type
            
            # Upload file
            response = self.client.storage.from_(self.default_bucket).upload(
                path=file_key,
                file=file_bytes,
                file_options=options
            )
            
            # Get file info
            file_info = self.get_file_info(file_key)
            
            logger.info(f"Successfully uploaded file: {file_key}")
            
            return {
                'success': True,
                'key': file_key,
                'size': len(file_bytes),
                'content_type': content_type,
                'metadata': metadata,
                'uploaded_at': datetime.utcnow().isoformat(),
                'file_info': file_info
            }
            
        except StorageException as e:
            logger.error(f"Supabase storage error uploading {file_key}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error uploading {file_key}: {e}")
            raise
    
    def download_file(self, file_key: str) -> bytes:
        """
        Download a file from Supabase Storage.
        
        Args:
            file_key: Storage path/key for the file
            
        Returns:
            File content as bytes
        """
        try:
            # Download file
            response = self.client.storage.from_(self.default_bucket).download(file_key)
            
            logger.info(f"Successfully downloaded file: {file_key}")
            return response
            
        except StorageException as e:
            logger.error(f"Supabase storage error downloading {file_key}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error downloading {file_key}: {e}")
            raise
    
    def delete_file(self, file_key: str) -> bool:
        """
        Delete a file from Supabase Storage.
        
        Args:
            file_key: Storage path/key for the file
            
        Returns:
            True if successful
        """
        try:
            # Delete file
            response = self.client.storage.from_(self.default_bucket).remove([file_key])
            
            logger.info(f"Successfully deleted file: {file_key}")
            return True
            
        except StorageException as e:
            logger.error(f"Supabase storage error deleting {file_key}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting {file_key}: {e}")
            return False
    
    def get_file_info(self, file_key: str) -> Optional[Dict[str, Any]]:
        """
        Get file information from Supabase Storage.
        
        Args:
            file_key: Storage path/key for the file
            
        Returns:
            File metadata or None if not found
        """
        try:
            # List files in the directory
            file_dir = str(Path(file_key).parent)
            file_name = Path(file_key).name
            
            files = self.client.storage.from_(self.default_bucket).list(
                path=file_dir,
                options={
                    "limit": 100,
                    "offset": 0
                }
            )
            
            # Find the specific file
            for file in files:
                if file.get('name') == file_name:
                    return {
                        'name': file.get('name'),
                        'size': file.get('metadata', {}).get('size', 0),
                        'content_type': file.get('metadata', {}).get('mimetype'),
                        'last_modified': file.get('updated_at'),
                        'created_at': file.get('created_at')
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting file info for {file_key}: {e}")
            return None
    
    def list_files(
        self,
        prefix: str = "",
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List files in a directory.
        
        Args:
            prefix: Directory prefix to list
            limit: Maximum number of files to return
            offset: Pagination offset
            
        Returns:
            List of file metadata
        """
        try:
            files = self.client.storage.from_(self.default_bucket).list(
                path=prefix,
                options={
                    "limit": limit,
                    "offset": offset
                }
            )
            
            return [
                {
                    'key': f"{prefix}/{file.get('name')}" if prefix else file.get('name'),
                    'name': file.get('name'),
                    'size': file.get('metadata', {}).get('size', 0),
                    'content_type': file.get('metadata', {}).get('mimetype'),
                    'last_modified': file.get('updated_at'),
                    'created_at': file.get('created_at')
                }
                for file in files
            ]
            
        except Exception as e:
            logger.error(f"Error listing files with prefix {prefix}: {e}")
            return []
    
    def generate_signed_url(
        self,
        file_key: str,
        expires_in: int = 3600
    ) -> Optional[str]:
        """
        Generate a signed URL for temporary file access.
        
        Args:
            file_key: Storage path/key for the file
            expires_in: URL expiration time in seconds
            
        Returns:
            Signed URL or None if error
        """
        try:
            # Create signed URL
            response = self.client.storage.from_(self.default_bucket).create_signed_url(
                path=file_key,
                expires_in=expires_in
            )
            
            if response.get('signedURL'):
                logger.info(f"Generated signed URL for {file_key}, expires in {expires_in}s")
                return response['signedURL']
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating signed URL for {file_key}: {e}")
            return None
    
    def copy_file(
        self,
        source_key: str,
        destination_key: str
    ) -> bool:
        """
        Copy a file within Supabase Storage.
        
        Args:
            source_key: Source file path/key
            destination_key: Destination file path/key
            
        Returns:
            True if successful
        """
        try:
            # Download source file
            content = self.download_file(source_key)
            
            # Get source file info
            file_info = self.get_file_info(source_key)
            content_type = file_info.get('content_type') if file_info else None
            
            # Upload to destination
            self.upload_file(destination_key, content, content_type)
            
            logger.info(f"Successfully copied {source_key} to {destination_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error copying file from {source_key} to {destination_key}: {e}")
            return False
    
    def move_file(
        self,
        source_key: str,
        destination_key: str
    ) -> bool:
        """
        Move a file within Supabase Storage.
        
        Args:
            source_key: Source file path/key
            destination_key: Destination file path/key
            
        Returns:
            True if successful
        """
        try:
            # Copy file first
            if self.copy_file(source_key, destination_key):
                # Delete source if copy succeeded
                return self.delete_file(source_key)
            
            return False
            
        except Exception as e:
            logger.error(f"Error moving file from {source_key} to {destination_key}: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the storage connection.
        
        Returns:
            Health check results
        """
        try:
            # Try to list buckets
            buckets = self.client.storage.list_buckets()
            
            # Check if our default bucket exists
            bucket_exists = any(b.name == self.default_bucket for b in buckets)
            
            return {
                'status': 'healthy' if bucket_exists else 'degraded',
                'bucket_exists': bucket_exists,
                'bucket_count': len(buckets),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Storage health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }


# Singleton instance
_storage_client: Optional[SupabaseStorageClient] = None


def get_storage_client() -> SupabaseStorageClient:
    """
    Get or create the Supabase storage client instance.
    
    Returns:
        SupabaseStorageClient instance
    """
    global _storage_client
    if _storage_client is None:
        _storage_client = SupabaseStorageClient()
    return _storage_client