"""
Test script for Supabase Storage integration.

This script tests the basic file operations using the Supabase Storage implementation.
"""

import asyncio
import os
from uuid import uuid4
from datetime import datetime

# Add the app directory to Python path
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.document_processing.storage.storage_manager import StorageManager


async def test_storage_operations():
    """Test basic storage operations."""
    print("🧪 Testing Supabase Storage Integration")
    print("=" * 50)
    
    # Initialize storage manager
    storage_manager = StorageManager()
    
    try:
        print("\n1️⃣ Initializing storage components...")
        await storage_manager.initialize()
        print("✅ Storage components initialized")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        print("\n⚠️  Make sure you have set the following environment variables:")
        print("   - SUPABASE_URL")
        print("   - SUPABASE_SERVICE_KEY")
        print("   - DATABASE_URL (for PostgreSQL)")
        return
    
    # Test data
    test_user_id = uuid4()
    test_content = b"""# Test Document
    
This is a test document for verifying Supabase Storage integration.

## Features Tested
- File upload
- File retrieval
- File deletion
- Metadata handling
- Content processing

Generated at: """ + datetime.now().isoformat().encode()
    
    test_filename = f"test_document_{uuid4().hex[:8]}.md"
    
    print(f"\n2️⃣ Testing document upload...")
    print(f"   User ID: {test_user_id}")
    print(f"   Filename: {test_filename}")
    print(f"   Size: {len(test_content)} bytes")
    
    try:
        # Store document
        file_id, storage_info = await storage_manager.store_document(
            file_content=test_content,
            filename=test_filename,
            content_type="text/markdown",
            user_id=test_user_id,
            metadata={
                "test": True,
                "created_at": datetime.now().isoformat(),
                "purpose": "storage integration test"
            }
        )
        
        print(f"✅ Document uploaded successfully!")
        print(f"   File ID: {file_id}")
        print(f"   Storage path: {storage_info['storage_path']}")
        print(f"   Size: {storage_info['size_mb']:.2f} MB")
        
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return
    
    print(f"\n3️⃣ Testing document retrieval...")
    
    try:
        # Retrieve document
        retrieved_doc = await storage_manager.retrieve_document(
            file_id=file_id,
            user_id=test_user_id,
            include_content=True
        )
        
        print(f"✅ Document retrieved successfully!")
        print(f"   Filename: {retrieved_doc.get('filename', 'N/A')}")
        print(f"   Content type: {retrieved_doc.get('content_type', 'N/A')}")
        print(f"   Size: {retrieved_doc.get('size_mb', 0):.2f} MB")
        
        if 'raw_content' in retrieved_doc:
            content_preview = retrieved_doc['raw_content'][:100]
            print(f"   Content preview: {content_preview}...")
        
    except Exception as e:
        print(f"❌ Retrieval failed: {e}")
    
    print(f"\n4️⃣ Testing user quota...")
    
    try:
        quota = await storage_manager.get_user_quota(test_user_id)
        print(f"✅ User quota retrieved!")
        print(f"   Total limit: {quota.total_limit_mb} MB")
        print(f"   Used: {quota.used_mb:.2f} MB")
        print(f"   Available: {quota.available_mb:.2f} MB")
        print(f"   Files: {quota.file_count}/{quota.max_files}")
    except Exception as e:
        print(f"❌ Quota check failed: {e}")
    
    print(f"\n5️⃣ Testing document deletion...")
    
    try:
        # Delete document
        deleted = await storage_manager.delete_document(
            file_id=file_id,
            user_id=test_user_id,
            permanent=True
        )
        
        if deleted:
            print(f"✅ Document deleted successfully!")
        else:
            print(f"⚠️  Document deletion returned false")
            
    except Exception as e:
        print(f"❌ Deletion failed: {e}")
    
    print(f"\n6️⃣ Testing storage metrics...")
    
    try:
        metrics = await storage_manager.get_storage_metrics()
        print(f"✅ Storage metrics retrieved!")
        print(f"   Total files: {metrics.total_files}")
        print(f"   Total size: {metrics.total_size_mb:.2f} MB")
        print(f"   Cache hit rate: {metrics.cache_hit_rate:.1%}")
        print(f"   Storage health: {metrics.storage_health}")
    except Exception as e:
        print(f"❌ Metrics retrieval failed: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Storage integration test completed!")
    
    # Test health check
    print(f"\n7️⃣ Testing storage health check...")
    try:
        from app.services.document_processing.storage.supabase_storage import get_storage_client
        storage_client = get_storage_client()
        health = storage_client.health_check()
        print(f"✅ Storage health check completed!")
        print(f"   Status: {health['status']}")
        print(f"   Bucket exists: {health.get('bucket_exists', False)}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")


if __name__ == "__main__":
    # Run the async test
    asyncio.run(test_storage_operations())