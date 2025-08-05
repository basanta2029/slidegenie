#!/usr/bin/env python3
"""Verify test environment setup for SlideGenie."""

import os
import sys
import asyncio
from pathlib import Path
from typing import Dict, Tuple, List
import psycopg2
import redis
from minio import Minio
import httpx

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestEnvironmentVerifier:
    """Verify test environment is properly set up."""
    
    def __init__(self):
        self.results: Dict[str, Tuple[bool, str]] = {}
        self.warnings: List[str] = []
    
    def check_environment_variables(self) -> None:
        """Check required environment variables."""
        required_vars = [
            "DATABASE_URL",
            "REDIS_URL",
            "MINIO_ENDPOINT",
            "MINIO_ACCESS_KEY",
            "MINIO_SECRET_KEY",
        ]
        
        for var in required_vars:
            value = os.getenv(var)
            if value:
                self.results[f"Environment: {var}"] = (True, "Set")
            else:
                self.results[f"Environment: {var}"] = (False, "Not set")
    
    def check_postgresql(self) -> None:
        """Check PostgreSQL connection."""
        try:
            db_url = os.getenv("DATABASE_URL", "")
            # Parse connection string
            if db_url.startswith("postgresql://"):
                db_url = db_url.replace("postgresql://", "")
            
            parts = db_url.split("@")
            if len(parts) != 2:
                raise ValueError("Invalid DATABASE_URL format")
            
            user_pass, host_db = parts
            user, password = user_pass.split(":")
            host_port, db = host_db.split("/")
            host, port = host_port.split(":")
            
            # Connect to database
            conn = psycopg2.connect(
                host=host,
                port=port,
                database=db,
                user=user,
                password=password
            )
            
            # Check if we can query
            cur = conn.cursor()
            cur.execute("SELECT version();")
            version = cur.fetchone()[0]
            
            # Check for tables
            cur.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            table_count = cur.fetchone()[0]
            
            cur.close()
            conn.close()
            
            self.results["PostgreSQL Connection"] = (True, f"Connected ({version.split(',')[0]})")
            self.results["Database Tables"] = (True, f"{table_count} tables found")
            
            if table_count == 0:
                self.warnings.append("No tables found - run migrations: poetry run alembic upgrade head")
            
        except Exception as e:
            self.results["PostgreSQL Connection"] = (False, str(e))
    
    def check_redis(self) -> None:
        """Check Redis connection."""
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6380")
            r = redis.from_url(redis_url)
            
            # Test connection
            r.ping()
            
            # Get Redis info
            info = r.info()
            version = info.get("redis_version", "unknown")
            
            self.results["Redis Connection"] = (True, f"Connected (v{version})")
            
        except Exception as e:
            self.results["Redis Connection"] = (False, str(e))
    
    def check_minio(self) -> None:
        """Check MinIO connection."""
        try:
            endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9001")
            access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
            secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
            
            # Create MinIO client
            client = Minio(
                endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=False
            )
            
            # List buckets
            buckets = client.list_buckets()
            bucket_names = [b.name for b in buckets]
            
            self.results["MinIO Connection"] = (True, f"Connected ({len(buckets)} buckets)")
            
            # Check for test bucket
            if "test-uploads" in bucket_names:
                self.results["MinIO Test Bucket"] = (True, "test-uploads exists")
            else:
                self.results["MinIO Test Bucket"] = (False, "test-uploads not found")
                self.warnings.append("Create test bucket: mc mb minio/test-uploads")
            
        except Exception as e:
            self.results["MinIO Connection"] = (False, str(e))
    
    def check_fixtures(self) -> None:
        """Check if test fixtures exist."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        
        expected_files = [
            "users.json",
            "presentations.json",
            "academic.json",
            "templates.json",
            "files.json",
            "all_fixtures.json",
        ]
        
        for filename in expected_files:
            filepath = fixtures_dir / filename
            if filepath.exists():
                size = filepath.stat().st_size
                self.results[f"Fixture: {filename}"] = (True, f"{size:,} bytes")
            else:
                self.results[f"Fixture: {filename}"] = (False, "Not found")
        
        # Check sample files
        sample_files_dir = fixtures_dir / "files"
        if sample_files_dir.exists():
            file_count = len(list(sample_files_dir.rglob("*")))
            self.results["Sample Files"] = (True, f"{file_count} files")
        else:
            self.results["Sample Files"] = (False, "Directory not found")
            self.warnings.append("Generate fixtures: poetry run python tests/scripts/generate_fixtures.py")
    
    def check_dependencies(self) -> None:
        """Check Python dependencies."""
        try:
            import pytest
            self.results["pytest"] = (True, pytest.__version__)
        except ImportError:
            self.results["pytest"] = (False, "Not installed")
        
        try:
            import factory
            self.results["factory-boy"] = (True, factory.__version__)
        except ImportError:
            self.results["factory-boy"] = (False, "Not installed")
        
        try:
            import coverage
            self.results["coverage"] = (True, coverage.__version__)
        except ImportError:
            self.results["coverage"] = (False, "Not installed")
    
    async def check_api_health(self) -> None:
        """Check if API is running (for E2E tests)."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8001/health")
                if response.status_code == 200:
                    self.results["API Health"] = (True, "API is running")
                else:
                    self.results["API Health"] = (False, f"Status {response.status_code}")
        except Exception:
            self.results["API Health"] = (False, "Not running (OK for unit/integration tests)")
    
    def print_results(self) -> None:
        """Print verification results."""
        print("\n" + "="*60)
        print("🔍 TEST ENVIRONMENT VERIFICATION")
        print("="*60 + "\n")
        
        # Group results
        groups = {
            "Environment Variables": [],
            "Database": [],
            "Services": [],
            "Fixtures": [],
            "Dependencies": [],
        }
        
        for key, (success, message) in self.results.items():
            if key.startswith("Environment:"):
                groups["Environment Variables"].append((key, success, message))
            elif "PostgreSQL" in key or "Database" in key:
                groups["Database"].append((key, success, message))
            elif any(service in key for service in ["Redis", "MinIO", "API"]):
                groups["Services"].append((key, success, message))
            elif "Fixture" in key or "Sample" in key:
                groups["Fixtures"].append((key, success, message))
            else:
                groups["Dependencies"].append((key, success, message))
        
        # Print grouped results
        all_success = True
        for group_name, items in groups.items():
            if items:
                print(f"{group_name}:")
                for key, success, message in items:
                    status = "✅" if success else "❌"
                    name = key.replace("Environment: ", "").replace("Fixture: ", "")
                    print(f"  {status} {name}: {message}")
                    if not success:
                        all_success = False
                print()
        
        # Print warnings
        if self.warnings:
            print("⚠️  Warnings:")
            for warning in self.warnings:
                print(f"  - {warning}")
            print()
        
        # Summary
        print("="*60)
        if all_success:
            print("✅ All checks passed! Test environment is ready.")
            return True
        else:
            print("❌ Some checks failed. Please fix the issues above.")
            return False
    
    async def verify_all(self) -> bool:
        """Run all verification checks."""
        print("Verifying test environment setup...")
        
        self.check_environment_variables()
        self.check_postgresql()
        self.check_redis()
        self.check_minio()
        self.check_fixtures()
        self.check_dependencies()
        await self.check_api_health()
        
        return self.print_results()


async def main():
    """Main verification function."""
    verifier = TestEnvironmentVerifier()
    success = await verifier.verify_all()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())