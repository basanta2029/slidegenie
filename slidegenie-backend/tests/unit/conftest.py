"""Pytest configuration for unit tests."""

import pytest
import asyncio
from typing import Generator
import os
import sys
from unittest.mock import Mock, AsyncMock, patch

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Configure asyncio for tests
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_redis_client():
    """Mock Redis client."""
    client = AsyncMock()
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock(return_value=True)
    client.delete = AsyncMock(return_value=True)
    client.exists = AsyncMock(return_value=False)
    client.expire = AsyncMock(return_value=True)
    return client


@pytest.fixture
def mock_settings():
    """Mock application settings."""
    settings = Mock()
    settings.SECRET_KEY = "test-secret-key"
    settings.DATABASE_URL = "postgresql://test:test@localhost/test"
    settings.REDIS_URL = "redis://localhost:6379/0"
    settings.JWT_ALGORITHM = "HS256"
    settings.JWT_EXPIRATION_MINUTES = 30
    settings.ANTHROPIC_API_KEY = "test-anthropic-key"
    settings.OPENAI_API_KEY = "test-openai-key"
    settings.AWS_ACCESS_KEY_ID = "test-aws-key"
    settings.AWS_SECRET_ACCESS_KEY = "test-aws-secret"
    settings.S3_BUCKET_NAME = "test-bucket"
    settings.MAX_FILE_SIZE_MB = 50
    settings.ALLOWED_FILE_TYPES = [".pdf", ".docx", ".tex", ".pptx"]
    return settings


@pytest.fixture(autouse=True)
def mock_external_services():
    """Automatically mock external services for all tests."""
    with patch('boto3.client') as mock_boto:
        with patch('redis.asyncio.Redis') as mock_redis:
            with patch('httpx.AsyncClient') as mock_http:
                # Configure default behaviors
                mock_s3 = Mock()
                mock_boto.return_value = mock_s3
                
                yield {
                    'boto3': mock_boto,
                    'redis': mock_redis,
                    'httpx': mock_http,
                    's3': mock_s3
                }


@pytest.fixture
def sample_pdf_bytes():
    """Sample PDF file content."""
    return b"%PDF-1.4\n%Test PDF content\n%%EOF"


@pytest.fixture
def sample_docx_bytes():
    """Sample DOCX file content."""
    # DOCX is a zip file, so we return a minimal zip header
    return b"PK\x03\x04\x14\x00\x00\x00\x08\x00"


@pytest.fixture
def sample_latex_content():
    """Sample LaTeX content."""
    return r"""
\documentclass{article}
\begin{document}
\title{Test Document}
\author{Test Author}
\maketitle
\section{Introduction}
This is a test LaTeX document.
\end{document}
""".encode()


@pytest.fixture
def sample_presentation_data():
    """Sample presentation data structure."""
    return {
        "id": 1,
        "user_id": 1,
        "title": "Test Presentation",
        "description": "A test presentation for unit tests",
        "slide_count": 10,
        "slides": [
            {
                "id": 1,
                "order": 1,
                "type": "title",
                "title": "Test Presentation",
                "content": {"subtitle": "Unit Test Example"}
            },
            {
                "id": 2,
                "order": 2,
                "type": "content",
                "title": "Introduction",
                "content": {
                    "bullet_points": [
                        "First point",
                        "Second point",
                        "Third point"
                    ]
                }
            }
        ],
        "metadata": {
            "theme": "academic",
            "template_id": 1,
            "language": "en",
            "created_at": "2024-01-01T00:00:00Z"
        }
    }


# Test environment variables
os.environ.update({
    "TESTING": "true",
    "DATABASE_URL": "postgresql://test:test@localhost/test",
    "REDIS_URL": "redis://localhost:6379/0",
    "SECRET_KEY": "test-secret-key",
    "ANTHROPIC_API_KEY": "test-anthropic-key",
    "OPENAI_API_KEY": "test-openai-key"
})