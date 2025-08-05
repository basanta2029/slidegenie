"""
Utility functions for performance testing.
"""
import os
import time
import random
import string
import json
from contextlib import contextmanager
from typing import Dict, Any, List, Optional, Generator
from datetime import datetime, timedelta
import faker


fake = faker.Faker()


class Timer:
    """Context manager for timing operations."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        
    @property
    def duration(self) -> float:
        """Get duration in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0
        
    @property
    def duration_ms(self) -> float:
        """Get duration in milliseconds."""
        return self.duration * 1000


@contextmanager
def measure_time() -> Generator[Timer, None, None]:
    """Measure execution time of a code block."""
    timer = Timer()
    timer.start_time = time.time()
    try:
        yield timer
    finally:
        timer.end_time = time.time()


class TestDataGenerator:
    """Generate test data for performance tests."""
    
    @staticmethod
    def random_string(length: int = 10) -> str:
        """Generate a random string."""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    @staticmethod
    def presentation_title() -> str:
        """Generate a random presentation title."""
        topics = [
            "Machine Learning in Healthcare",
            "Quantum Computing Fundamentals",
            "Climate Change Mitigation Strategies",
            "Blockchain Technology Applications",
            "Artificial Intelligence Ethics",
            "Renewable Energy Solutions",
            "Data Privacy in Digital Age",
            "Space Exploration Technologies",
            "Biotechnology Innovations",
            "Cybersecurity Best Practices"
        ]
        return f"{random.choice(topics)} - {TestDataGenerator.random_string(5)}"
    
    @staticmethod
    def presentation_content() -> Dict[str, Any]:
        """Generate random presentation content."""
        return {
            "topic": fake.sentence(nb_words=6),
            "audience": random.choice(["academic", "professional", "general"]),
            "duration": random.choice([10, 15, 20, 30, 45, 60]),
            "key_points": [fake.sentence() for _ in range(random.randint(3, 7))],
            "references": [
                {
                    "title": fake.sentence(nb_words=8),
                    "authors": [fake.name() for _ in range(random.randint(1, 3))],
                    "year": random.randint(2015, 2024),
                    "journal": fake.company()
                }
                for _ in range(random.randint(2, 5))
            ]
        }
    
    @staticmethod
    def slide_content() -> Dict[str, Any]:
        """Generate random slide content."""
        slide_types = ["title", "content", "image", "chart", "table", "conclusion"]
        return {
            "type": random.choice(slide_types),
            "title": fake.sentence(nb_words=5),
            "content": fake.paragraph(nb_sentences=random.randint(2, 5)),
            "notes": fake.paragraph(nb_sentences=2),
            "layout": random.choice(["full", "two-column", "three-column", "image-left", "image-right"])
        }
    
    @staticmethod
    def user_data() -> Dict[str, str]:
        """Generate random user data."""
        return {
            "email": fake.email(),
            "password": TestDataGenerator.random_string(12),
            "full_name": fake.name(),
            "institution": fake.company(),
            "department": random.choice(["Computer Science", "Physics", "Biology", "Engineering", "Mathematics"])
        }
    
    @staticmethod
    def search_query() -> str:
        """Generate random search query."""
        terms = [
            "machine learning",
            "neural networks",
            "data analysis",
            "statistical methods",
            "research methodology",
            "literature review",
            "experimental design",
            "hypothesis testing",
            "data visualization",
            "scientific writing"
        ]
        return random.choice(terms)
    
    @staticmethod
    def generate_large_text(size_kb: int = 100) -> str:
        """Generate large text content of specified size."""
        # Approximate 1KB = 1000 characters
        chars_needed = size_kb * 1000
        paragraphs = []
        current_size = 0
        
        while current_size < chars_needed:
            paragraph = fake.paragraph(nb_sentences=10)
            paragraphs.append(paragraph)
            current_size += len(paragraph)
            
        return "\n\n".join(paragraphs)[:chars_needed]
    
    @staticmethod
    def analytics_event() -> Dict[str, Any]:
        """Generate random analytics event."""
        events = [
            "presentation_viewed",
            "slide_edited",
            "template_selected",
            "file_uploaded",
            "export_completed",
            "ai_generation_started",
            "collaboration_started",
            "feedback_submitted"
        ]
        
        return {
            "event": random.choice(events),
            "timestamp": datetime.now().isoformat(),
            "properties": {
                "duration": random.randint(1, 300),
                "success": random.choice([True, False]),
                "source": random.choice(["web", "api", "mobile"]),
                "user_agent": fake.user_agent()
            }
        }


# Global instance
generate_test_data = TestDataGenerator()


class MetricsCollector:
    """Collect and aggregate performance metrics."""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
        self.errors: Dict[str, int] = {}
        self.start_time = time.time()
        
    def record_metric(self, name: str, value: float):
        """Record a metric value."""
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append(value)
        
    def record_error(self, name: str):
        """Record an error occurrence."""
        if name not in self.errors:
            self.errors[name] = 0
        self.errors[name] += 1
        
    def get_percentile(self, name: str, percentile: float) -> Optional[float]:
        """Get percentile value for a metric."""
        if name not in self.metrics or not self.metrics[name]:
            return None
            
        sorted_values = sorted(self.metrics[name])
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
        
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics."""
        duration = time.time() - self.start_time
        summary = {
            "duration_seconds": duration,
            "metrics": {},
            "errors": self.errors
        }
        
        for name, values in self.metrics.items():
            if values:
                summary["metrics"][name] = {
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "mean": sum(values) / len(values),
                    "p50": self.get_percentile(name, 50),
                    "p90": self.get_percentile(name, 90),
                    "p95": self.get_percentile(name, 95),
                    "p99": self.get_percentile(name, 99)
                }
                
        return summary
        
    def export_to_file(self, filepath: str):
        """Export metrics to JSON file."""
        with open(filepath, "w") as f:
            json.dump(self.get_summary(), f, indent=2)


# Global metrics collector
metrics = MetricsCollector()


def create_test_file(filepath: str, size_mb: int, content_type: str = "text"):
    """Create a test file of specified size."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    if content_type == "text":
        # Generate text content
        size_kb = size_mb * 1024
        content = generate_test_data.generate_large_text(size_kb)
        with open(filepath, "w") as f:
            f.write(content)
    elif content_type == "binary":
        # Generate binary content
        size_bytes = size_mb * 1024 * 1024
        with open(filepath, "wb") as f:
            f.write(os.urandom(size_bytes))
            
            
def cleanup_test_data(presentation_ids: List[str], upload_ids: List[str], client):
    """Clean up test data after performance test."""
    # Delete presentations
    for pid in presentation_ids:
        try:
            client.delete(f"/api/v1/presentations/{pid}")
        except Exception as e:
            print(f"Failed to delete presentation {pid}: {e}")
            
    # Delete uploaded files
    for uid in upload_ids:
        try:
            client.delete(f"/api/v1/documents/{uid}")
        except Exception as e:
            print(f"Failed to delete upload {uid}: {e}")