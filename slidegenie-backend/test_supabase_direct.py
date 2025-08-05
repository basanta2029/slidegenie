"""
Direct test of Supabase Storage implementation.

This script tests the Supabase storage directly without going through
the full document processing pipeline.
"""

import os
import sys
from uuid import uuid4
from datetime import datetime

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set minimal environment variables if not set
if not os.getenv('SECRET_KEY'):
    os.environ['SECRET_KEY'] = 'test-secret-key-for-testing-only-change-in-production'


def test_supabase_storage():
    """Test Supabase storage operations directly."""
    print("🧪 Testing Supabase Storage Direct Integration")
    print("=" * 50)
    
    # Check environment variables
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    
    if not supabase_url or not supabase_key:
        print("\n❌ Missing required environment variables!")
        print("\n📋 Please set the following in your .env file:")
        print("   SUPABASE_URL=https://your-project.supabase.co")
        print("   SUPABASE_SERVICE_KEY=your-service-key-here")
        print("\n💡 Get these from your Supabase Dashboard:")
        print("   1. Go to https://app.supabase.com")
        print("   2. Select your project")
        print("   3. Go to Settings > API")
        print("   4. Copy the URL and service_role key")
        return
    
    print(f"\n✅ Environment configured:")
    print(f"   SUPABASE_URL: {supabase_url}")
    print(f"   SUPABASE_SERVICE_KEY: {'*' * 20}...{supabase_key[-4:]}")
    
    try:
        from app.services.document_processing.storage.supabase_storage import get_storage_client
        
        print("\n1️⃣ Initializing Supabase storage client...")
        storage_client = get_storage_client()
        print("✅ Storage client initialized")
        
        # Test health check
        print("\n2️⃣ Performing health check...")
        health = storage_client.health_check()
        print(f"✅ Health check completed: {health['status']}")
        print(f"   Bucket exists: {health.get('bucket_exists', False)}")
        
        # Test file operations
        test_content = f"Test file created at {datetime.now().isoformat()}".encode()
        test_key = f"test/test_file_{uuid4().hex[:8]}.txt"
        
        print(f"\n3️⃣ Testing file upload...")
        print(f"   Key: {test_key}")
        print(f"   Size: {len(test_content)} bytes")
        
        result = storage_client.upload_file(
            file_key=test_key,
            file_content=test_content,
            content_type="text/plain",
            metadata={"test": True}
        )
        
        if result['success']:
            print("✅ File uploaded successfully!")
            
            # Test download
            print("\n4️⃣ Testing file download...")
            downloaded = storage_client.download_file(test_key)
            print(f"✅ File downloaded: {len(downloaded)} bytes")
            print(f"   Content matches: {downloaded == test_content}")
            
            # Test signed URL
            print("\n5️⃣ Testing signed URL generation...")
            signed_url = storage_client.generate_signed_url(test_key, expires_in=300)
            if signed_url:
                print(f"✅ Signed URL generated (expires in 5 minutes)")
                print(f"   URL: {signed_url[:50]}...")
            
            # Test file listing
            print("\n6️⃣ Testing file listing...")
            files = storage_client.list_files(prefix="test", limit=10)
            print(f"✅ Found {len(files)} file(s) in test/ directory")
            for file in files:
                print(f"   - {file['name']} ({file['size']} bytes)")
            
            # Test file deletion
            print("\n7️⃣ Testing file deletion...")
            if storage_client.delete_file(test_key):
                print("✅ File deleted successfully!")
            else:
                print("⚠️  File deletion failed")
        else:
            print("❌ File upload failed!")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 50)
    print("🎉 Direct storage test completed!")


if __name__ == "__main__":
    test_supabase_storage()