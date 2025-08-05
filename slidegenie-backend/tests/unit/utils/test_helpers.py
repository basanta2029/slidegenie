"""Test utilities and helpers for unit tests."""

import io
import json
import random
import string
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, MagicMock

import pytest
from faker import Faker

fake = Faker()


class MockResponse:
    """Mock HTTP response for external API calls."""
    
    def __init__(self, status_code: int = 200, json_data: Optional[Dict] = None, 
                 text: str = "", headers: Optional[Dict] = None):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text
        self.headers = headers or {}
    
    def json(self):
        return self._json_data
    
    async def aread(self):
        return self.text.encode()
    
    async def aclose(self):
        pass


class TestDataGenerator:
    """Generate realistic test data for various entities."""
    
    @staticmethod
    def generate_user(user_id: Optional[int] = None, **kwargs) -> Dict[str, Any]:
        """Generate test user data."""
        return {
            "id": user_id or fake.random_int(min=1, max=10000),
            "email": kwargs.get("email", fake.email()),
            "name": kwargs.get("name", fake.name()),
            "institution": kwargs.get("institution", fake.company()),
            "role": kwargs.get("role", "user"),
            "is_active": kwargs.get("is_active", True),
            "is_verified": kwargs.get("is_verified", True),
            "created_at": kwargs.get("created_at", datetime.utcnow()),
            "updated_at": kwargs.get("updated_at", datetime.utcnow()),
        }
    
    @staticmethod
    def generate_presentation(presentation_id: Optional[int] = None, **kwargs) -> Dict[str, Any]:
        """Generate test presentation data."""
        return {
            "id": presentation_id or fake.random_int(min=1, max=10000),
            "user_id": kwargs.get("user_id", fake.random_int(min=1, max=10000)),
            "title": kwargs.get("title", f"Presentation on {fake.catch_phrase()}"),
            "description": kwargs.get("description", fake.text(max_nb_chars=200)),
            "slide_count": kwargs.get("slide_count", fake.random_int(min=5, max=30)),
            "status": kwargs.get("status", "completed"),
            "metadata": kwargs.get("metadata", {
                "theme": "academic",
                "language": "en",
                "duration_minutes": fake.random_int(min=10, max=60)
            }),
            "created_at": kwargs.get("created_at", datetime.utcnow()),
            "updated_at": kwargs.get("updated_at", datetime.utcnow()),
        }
    
    @staticmethod
    def generate_slide(slide_id: Optional[int] = None, **kwargs) -> Dict[str, Any]:
        """Generate test slide data."""
        slide_types = ["title", "content", "methodology", "results", "conclusion", "references"]
        return {
            "id": slide_id or fake.random_int(min=1, max=10000),
            "presentation_id": kwargs.get("presentation_id", fake.random_int(min=1, max=10000)),
            "order": kwargs.get("order", fake.random_int(min=1, max=30)),
            "type": kwargs.get("type", random.choice(slide_types)),
            "title": kwargs.get("title", fake.sentence(nb_words=6)),
            "content": kwargs.get("content", {
                "main_points": [fake.sentence() for _ in range(3)],
                "speaker_notes": fake.paragraph(),
                "references": []
            }),
            "layout": kwargs.get("layout", "two_column"),
            "animations": kwargs.get("animations", []),
            "created_at": kwargs.get("created_at", datetime.utcnow()),
            "updated_at": kwargs.get("updated_at", datetime.utcnow()),
        }
    
    @staticmethod
    def generate_academic_content() -> Dict[str, Any]:
        """Generate realistic academic content."""
        return {
            "title": f"Impact of {fake.word().title()} on {fake.word().title()} Systems",
            "abstract": fake.text(max_nb_chars=500),
            "sections": [
                {
                    "heading": "Introduction",
                    "content": fake.paragraphs(nb=3),
                    "citations": [f"({fake.last_name()} et al., {fake.year()})" for _ in range(3)]
                },
                {
                    "heading": "Literature Review",
                    "content": fake.paragraphs(nb=4),
                    "citations": [f"({fake.last_name()}, {fake.year()})" for _ in range(5)]
                },
                {
                    "heading": "Methodology",
                    "content": fake.paragraphs(nb=3),
                    "equations": ["E = mc^2", "F = ma", "∇²φ = 0"]
                },
                {
                    "heading": "Results",
                    "content": fake.paragraphs(nb=3),
                    "figures": [f"Figure {i}: {fake.sentence()}" for i in range(1, 4)]
                },
                {
                    "heading": "Conclusion",
                    "content": fake.paragraphs(nb=2),
                    "future_work": fake.paragraph()
                }
            ],
            "references": [
                f"{fake.last_name()}, {fake.first_name()[0]}. ({fake.year()}). "
                f"{fake.sentence(nb_words=8)}. {fake.company()} Journal."
                for _ in range(10)
            ]
        }
    
    @staticmethod
    def generate_pdf_content() -> bytes:
        """Generate mock PDF content."""
        # Simple PDF header for testing
        return b"%PDF-1.4\n%Mock PDF content for testing\n"
    
    @staticmethod
    def generate_latex_content() -> str:
        """Generate mock LaTeX content."""
        return r"""
\documentclass{article}
\usepackage{amsmath}
\title{Sample LaTeX Document}
\author{Test Author}
\date{\today}

\begin{document}
\maketitle

\section{Introduction}
This is a test LaTeX document for unit testing.

\section{Methodology}
We use the following equation:
\begin{equation}
    E = mc^2
\end{equation}

\section{Results}
Our results show significant improvement.

\section{Conclusion}
The test was successful.

\end{document}
"""
    
    @staticmethod
    def generate_docx_content() -> bytes:
        """Generate mock DOCX content (ZIP structure)."""
        # Simplified DOCX header (it's actually a ZIP file)
        return b"PK\x03\x04Mock DOCX content for testing"


class MockAIProvider:
    """Mock AI provider for testing."""
    
    def __init__(self, default_response: Optional[str] = None):
        self.default_response = default_response or "Mock AI response"
        self.call_count = 0
        self.last_prompt = None
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """Mock AI generation."""
        self.call_count += 1
        self.last_prompt = prompt
        
        # Return context-aware responses based on prompt
        if "title slide" in prompt.lower():
            return json.dumps({
                "title": "Test Presentation Title",
                "subtitle": "A comprehensive analysis",
                "author": "Dr. Test Author",
                "institution": "Test University",
                "date": "2024"
            })
        elif "outline" in prompt.lower():
            return json.dumps({
                "sections": [
                    {"title": "Introduction", "duration": 5},
                    {"title": "Methodology", "duration": 10},
                    {"title": "Results", "duration": 15},
                    {"title": "Conclusion", "duration": 5}
                ]
            })
        elif "content" in prompt.lower():
            return json.dumps({
                "main_points": [
                    "First important point",
                    "Second key insight",
                    "Third critical finding"
                ],
                "speaker_notes": "Elaborate on each point during presentation",
                "visual_suggestions": ["Graph showing trend", "Comparison chart"]
            })
        
        return self.default_response


class MockFileStorage:
    """Mock file storage for testing."""
    
    def __init__(self):
        self.files = {}
        self.upload_count = 0
        self.download_count = 0
    
    async def upload(self, file_path: str, content: bytes) -> str:
        """Mock file upload."""
        self.upload_count += 1
        self.files[file_path] = content
        return f"https://mock-storage.com/{file_path}"
    
    async def download(self, file_path: str) -> bytes:
        """Mock file download."""
        self.download_count += 1
        return self.files.get(file_path, b"Mock file content")
    
    async def delete(self, file_path: str) -> bool:
        """Mock file deletion."""
        if file_path in self.files:
            del self.files[file_path]
            return True
        return False
    
    async def exists(self, file_path: str) -> bool:
        """Check if file exists."""
        return file_path in self.files


class MockRedisCache:
    """Mock Redis cache for testing."""
    
    def __init__(self):
        self.cache = {}
        self.ttls = {}
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        if key in self.cache:
            # Check TTL
            if key in self.ttls and datetime.utcnow() > self.ttls[key]:
                del self.cache[key]
                del self.ttls[key]
                return None
            return self.cache[key]
        return None
    
    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        self.cache[key] = value
        if ttl:
            self.ttls[key] = datetime.utcnow() + timedelta(seconds=ttl)
        return True
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if key in self.cache:
            del self.cache[key]
            if key in self.ttls:
                del self.ttls[key]
            return True
        return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        return key in self.cache


def create_mock_async_context_manager(return_value=None):
    """Create a mock async context manager."""
    class MockAsyncContextManager:
        async def __aenter__(self):
            return return_value or self
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
    
    return MockAsyncContextManager()


def create_mock_file(filename: str, content: bytes) -> io.BytesIO:
    """Create a mock file object."""
    file_obj = io.BytesIO(content)
    file_obj.name = filename
    file_obj.filename = filename  # For compatibility with different file upload libraries
    return file_obj


# Pytest fixtures
@pytest.fixture
def mock_ai_provider():
    """Fixture for mock AI provider."""
    return MockAIProvider()


@pytest.fixture
def mock_file_storage():
    """Fixture for mock file storage."""
    return MockFileStorage()


@pytest.fixture
def mock_redis_cache():
    """Fixture for mock Redis cache."""
    return MockRedisCache()


@pytest.fixture
def test_data_generator():
    """Fixture for test data generator."""
    return TestDataGenerator()


@pytest.fixture
def mock_response_factory():
    """Factory for creating mock responses."""
    def _factory(status_code=200, json_data=None, text="", headers=None):
        return MockResponse(status_code, json_data, text, headers)
    return _factory