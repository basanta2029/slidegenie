"""Job and task factories for testing."""

import factory
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import random
import json

from .base import BaseFactory, DictFactory, fake


class GenerationJobFactory(DictFactory):
    """Factory for creating generation job test data."""
    
    id = factory.Sequence(lambda n: f"job_{n}")
    
    user_id = factory.LazyAttribute(lambda o: f"user_{random.randint(1, 100)}")
    
    job_type = factory.LazyAttribute(
        lambda o: random.choice([
            "presentation_generation",
            "slide_generation",
            "content_analysis",
            "export_generation",
            "batch_processing",
        ])
    )
    
    # Job configuration
    config = factory.LazyAttribute(lambda o: _generate_job_config(o.job_type))
    
    # Status and progress
    status = factory.LazyAttribute(
        lambda o: random.choice([
            "pending", "queued", "processing",
            "completed", "failed", "cancelled"
        ])
    )
    
    progress = factory.LazyAttribute(lambda o: {
        "pending": 0,
        "queued": 0,
        "processing": random.randint(10, 90),
        "completed": 100,
        "failed": random.randint(10, 90),
        "cancelled": random.randint(0, 90),
    }[o.status])
    
    current_step = factory.LazyAttribute(lambda o: {
        "pending": None,
        "queued": "Waiting in queue",
        "processing": random.choice([
            "Analyzing content",
            "Generating slides",
            "Applying styles",
            "Optimizing layout",
            "Finalizing presentation",
        ]),
        "completed": "Done",
        "failed": "Error occurred",
        "cancelled": "Cancelled by user",
    }[o.status])
    
    # Timing
    created_at = factory.LazyAttribute(lambda o: BaseFactory.random_timestamp(24))
    
    started_at = factory.LazyAttribute(
        lambda o: o.created_at + timedelta(seconds=random.randint(1, 300))
        if o.status not in ["pending", "queued"] else None
    )
    
    completed_at = factory.LazyAttribute(
        lambda o: o.started_at + timedelta(seconds=random.randint(30, 600))
        if o.status in ["completed", "failed"] and o.started_at else None
    )
    
    estimated_completion = factory.LazyAttribute(
        lambda o: datetime.now(timezone.utc) + timedelta(seconds=random.randint(30, 300))
        if o.status == "processing" else None
    )
    
    # Queue information
    queue_name = factory.LazyAttribute(
        lambda o: random.choice([
            "high_priority", "default", "low_priority", "batch"
        ])
    )
    
    queue_position = factory.LazyAttribute(
        lambda o: random.randint(1, 100) if o.status == "queued" else None
    )
    
    priority = factory.LazyAttribute(
        lambda o: random.choice([1, 5, 10])  # 1 = highest, 10 = lowest
    )
    
    # Retry information
    retry_count = factory.LazyAttribute(
        lambda o: random.randint(0, 3) if o.status == "failed" else 0
    )
    
    max_retries = 3
    
    # Results
    result = factory.LazyAttribute(
        lambda o: _generate_job_result(o.job_type, o.status)
    )
    
    error = factory.LazyAttribute(
        lambda o: {
            "code": random.choice([
                "GENERATION_FAILED",
                "INVALID_INPUT",
                "TIMEOUT",
                "RESOURCE_LIMIT",
                "AI_ERROR",
            ]),
            "message": fake.sentence(),
            "details": fake.text(max_nb_chars=200),
            "timestamp": o.completed_at.isoformat() if o.completed_at else None,
        } if o.status == "failed" else None
    )
    
    # Resource usage
    resources = factory.LazyAttribute(lambda o: {
        "cpu_time_seconds": random.uniform(0.1, 60) if o.started_at else 0,
        "memory_peak_mb": random.randint(50, 500) if o.started_at else 0,
        "ai_tokens_used": random.randint(100, 10000) if o.job_type == "presentation_generation" else 0,
        "ai_cost_usd": random.uniform(0.01, 5.0) if o.job_type == "presentation_generation" else 0,
    })
    
    # Metadata
    metadata = factory.LazyAttribute(lambda o: {
        "source": random.choice(["web", "api", "mobile"]),
        "client_version": f"{random.randint(1, 3)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
        "user_agent": fake.user_agent(),
        "ip_address": fake.ipv4(),
    })
    
    # Callbacks
    webhook_url = factory.LazyAttribute(
        lambda o: fake.url() if random.random() > 0.7 else None
    )
    
    callback_status = factory.LazyAttribute(
        lambda o: random.choice([
            "pending", "sent", "failed", "disabled"
        ]) if o.webhook_url and o.status in ["completed", "failed"] else None
    )
    
    class Params:
        completed_job = factory.Trait(
            status="completed",
            progress=100,
            current_step="Done",
        )
        
        failed_job = factory.Trait(
            status="failed",
            retry_count=factory.LazyAttribute(lambda o: random.randint(1, 3)),
        )
        
        processing_job = factory.Trait(
            status="processing",
            progress=factory.LazyAttribute(lambda o: random.randint(20, 80)),
        )


class TaskQueueFactory(DictFactory):
    """Factory for task queue entries."""
    
    id = factory.Sequence(lambda n: f"task_{n}")
    
    queue_name = factory.LazyAttribute(
        lambda o: random.choice([
            "celery", "arq", "rq", "bull", "rabbitmq"
        ])
    )
    
    task_name = factory.LazyAttribute(
        lambda o: random.choice([
            "generate_presentation",
            "process_document",
            "export_to_pdf",
            "send_email",
            "cleanup_files",
            "analyze_content",
        ])
    )
    
    args = factory.LazyAttribute(
        lambda o: [f"arg_{i}" for i in range(random.randint(0, 3))]
    )
    
    kwargs = factory.LazyAttribute(lambda o: {
        f"param_{i}": random.choice([
            fake.word(),
            random.randint(1, 100),
            random.random() > 0.5,
        ])
        for i in range(random.randint(1, 5))
    })
    
    status = factory.LazyAttribute(
        lambda o: random.choice([
            "pending", "running", "success", "failed", "retrying"
        ])
    )
    
    created_at = factory.LazyAttribute(lambda o: BaseFactory.random_timestamp(1))
    
    started_at = factory.LazyAttribute(
        lambda o: o.created_at + timedelta(seconds=random.randint(1, 60))
        if o.status != "pending" else None
    )
    
    completed_at = factory.LazyAttribute(
        lambda o: o.started_at + timedelta(seconds=random.randint(1, 300))
        if o.status in ["success", "failed"] and o.started_at else None
    )
    
    eta = factory.LazyAttribute(
        lambda o: BaseFactory.random_future_timestamp(1)
        if random.random() > 0.7 else None
    )
    
    retries = factory.LazyAttribute(
        lambda o: random.randint(1, 3) if o.status == "retrying" else 0
    )
    
    max_retries = 3
    
    result = factory.LazyAttribute(
        lambda o: {"success": True, "data": fake.word()}
        if o.status == "success" else None
    )
    
    error = factory.LazyAttribute(
        lambda o: {
            "type": random.choice([
                "ValueError", "TimeoutError", "ConnectionError"
            ]),
            "message": fake.sentence(),
            "traceback": fake.text(max_nb_chars=500),
        } if o.status == "failed" else None
    )


class ExportJobFactory(DictFactory):
    """Factory for export job test data."""
    
    id = factory.Sequence(lambda n: f"export_{n}")
    
    presentation_id = factory.LazyAttribute(lambda o: f"pres_{random.randint(1, 100)}")
    user_id = factory.LazyAttribute(lambda o: f"user_{random.randint(1, 100)}")
    
    format = factory.LazyAttribute(
        lambda o: random.choice([
            "pdf", "pptx", "beamer", "google_slides", "keynote"
        ])
    )
    
    options = factory.LazyAttribute(lambda o: _generate_export_options(o.format))
    
    status = factory.LazyAttribute(
        lambda o: random.choice([
            "pending", "processing", "uploading",
            "completed", "failed", "expired"
        ])
    )
    
    progress_steps = factory.LazyAttribute(lambda o: [
        {
            "name": "Preparing content",
            "status": "completed" if o.progress >= 20 else "processing" if o.progress >= 0 else "pending",
            "progress": min(100, o.progress * 5),
        },
        {
            "name": "Generating document",
            "status": "completed" if o.progress >= 60 else "processing" if o.progress >= 20 else "pending",
            "progress": max(0, min(100, (o.progress - 20) * 2.5)),
        },
        {
            "name": "Applying styles",
            "status": "completed" if o.progress >= 80 else "processing" if o.progress >= 60 else "pending",
            "progress": max(0, min(100, (o.progress - 60) * 5)),
        },
        {
            "name": "Finalizing",
            "status": "completed" if o.progress >= 100 else "processing" if o.progress >= 80 else "pending",
            "progress": max(0, min(100, (o.progress - 80) * 5)),
        },
    ])
    
    progress = factory.LazyAttribute(lambda o: {
        "pending": 0,
        "processing": random.randint(10, 90),
        "uploading": 95,
        "completed": 100,
        "failed": random.randint(10, 90),
        "expired": 100,
    }[o.status])
    
    file_size_bytes = factory.LazyAttribute(
        lambda o: random.randint(100_000, 50_000_000)
        if o.status == "completed" else None
    )
    
    download_url = factory.LazyAttribute(
        lambda o: f"https://downloads.slidegenie.io/exports/{o.id}/{o.format}"
        if o.status == "completed" else None
    )
    
    download_expires_at = factory.LazyAttribute(
        lambda o: BaseFactory.random_future_timestamp(7)
        if o.status == "completed" else None
    )
    
    created_at = factory.LazyAttribute(lambda o: BaseFactory.random_timestamp(1))
    completed_at = factory.LazyAttribute(
        lambda o: o.created_at + timedelta(seconds=random.randint(30, 300))
        if o.status in ["completed", "failed", "expired"] else None
    )


class BackgroundTaskFactory(DictFactory):
    """Factory for background task test data."""
    
    id = factory.Sequence(lambda n: f"bgtask_{n}")
    
    task_type = factory.LazyAttribute(
        lambda o: random.choice([
            "cleanup_old_files",
            "send_notification",
            "update_analytics",
            "sync_data",
            "generate_report",
            "backup_database",
        ])
    )
    
    schedule_type = factory.LazyAttribute(
        lambda o: random.choice([
            "cron", "interval", "one_time", "event_triggered"
        ])
    )
    
    schedule = factory.LazyAttribute(lambda o: {
        "cron": random.choice([
            "0 0 * * *",  # Daily at midnight
            "0 */6 * * *",  # Every 6 hours
            "0 2 * * 0",  # Weekly on Sunday at 2 AM
        ]),
        "interval": {
            "every": random.randint(1, 60),
            "unit": random.choice(["minutes", "hours", "days"]),
        },
        "one_time": BaseFactory.random_future_timestamp(7).isoformat(),
        "event_triggered": {
            "event": random.choice([
                "user_signup", "presentation_created", "storage_limit_reached"
            ]),
        },
    }[o.schedule_type])
    
    is_active = factory.LazyAttribute(lambda o: random.random() > 0.2)
    
    last_run = factory.LazyAttribute(
        lambda o: BaseFactory.random_timestamp(7) if random.random() > 0.3 else None
    )
    
    next_run = factory.LazyAttribute(
        lambda o: BaseFactory.random_future_timestamp(1)
        if o.is_active and o.schedule_type != "one_time" else None
    )
    
    run_count = factory.LazyAttribute(lambda o: random.randint(0, 1000))
    
    success_count = factory.LazyAttribute(
        lambda o: random.randint(int(o.run_count * 0.8), o.run_count)
    )
    
    failure_count = factory.LazyAttribute(lambda o: o.run_count - o.success_count)
    
    average_duration_seconds = factory.LazyAttribute(
        lambda o: random.uniform(0.1, 300) if o.run_count > 0 else None
    )
    
    config = factory.LazyAttribute(lambda o: {
        "cleanup_old_files": {
            "days_to_keep": 30,
            "file_types": ["temp", "cache", "upload"],
        },
        "send_notification": {
            "notification_type": "email",
            "template": "weekly_summary",
        },
        "update_analytics": {
            "metrics": ["usage", "performance", "errors"],
        },
        "sync_data": {
            "source": "primary_db",
            "destination": "analytics_db",
        },
        "generate_report": {
            "report_type": "monthly_usage",
            "recipients": ["admin@slidegenie.io"],
        },
        "backup_database": {
            "databases": ["main", "analytics"],
            "destination": "s3",
        },
    }[o.task_type])


def _generate_job_config(job_type: str) -> Dict[str, Any]:
    """Generate job configuration based on type."""
    
    configs = {
        "presentation_generation": {
            "source_document_id": f"doc_{random.randint(1, 100)}",
            "template_id": f"template_{random.randint(1, 10)}",
            "options": {
                "slide_count": random.randint(10, 30),
                "include_references": random.choice([True, False]),
                "auto_layout": True,
                "language": random.choice(["en", "es", "fr"]),
                "ai_model": random.choice(["gpt-4", "claude-3"]),
            },
        },
        "slide_generation": {
            "presentation_id": f"pres_{random.randint(1, 100)}",
            "slide_type": random.choice([
                "title", "content", "image", "conclusion"
            ]),
            "content": fake.text(max_nb_chars=200),
            "position": random.randint(1, 20),
        },
        "content_analysis": {
            "document_id": f"doc_{random.randint(1, 100)}",
            "analysis_type": random.choice([
                "summarization", "key_points", "structure", "readability"
            ]),
            "options": {
                "detail_level": random.choice(["brief", "detailed", "comprehensive"]),
            },
        },
        "export_generation": {
            "presentation_id": f"pres_{random.randint(1, 100)}",
            "format": random.choice(["pdf", "pptx", "beamer"]),
            "options": _generate_export_options(
                random.choice(["pdf", "pptx", "beamer"])
            ),
        },
        "batch_processing": {
            "job_ids": [f"job_{random.randint(1, 100)}" for _ in range(random.randint(2, 10))],
            "operation": random.choice([
                "generate_all", "export_all", "analyze_all"
            ]),
        },
    }
    
    return configs.get(job_type, {})


def _generate_job_result(job_type: str, status: str) -> Optional[Dict[str, Any]]:
    """Generate job result based on type and status."""
    
    if status != "completed":
        return None
    
    results = {
        "presentation_generation": {
            "presentation_id": f"pres_{random.randint(1, 1000)}",
            "slide_count": random.randint(10, 30),
            "generation_time": random.uniform(5, 60),
            "quality_score": random.uniform(0.7, 1.0),
        },
        "slide_generation": {
            "slide_id": f"slide_{random.randint(1, 1000)}",
            "slide_number": random.randint(1, 30),
        },
        "content_analysis": {
            "summary": fake.text(max_nb_chars=500),
            "key_points": [fake.sentence() for _ in range(random.randint(3, 7))],
            "readability_score": random.uniform(60, 90),
            "structure": {
                "sections": random.randint(3, 8),
                "paragraphs": random.randint(10, 50),
                "sentences": random.randint(50, 200),
            },
        },
        "export_generation": {
            "file_id": f"file_{random.randint(1, 1000)}",
            "file_size": random.randint(100_000, 10_000_000),
            "download_url": fake.url(),
        },
        "batch_processing": {
            "total_jobs": random.randint(5, 20),
            "successful": random.randint(3, 18),
            "failed": random.randint(0, 2),
            "results": [
                {"job_id": f"job_{i}", "status": "completed"}
                for i in range(random.randint(5, 10))
            ],
        },
    }
    
    return results.get(job_type, {"status": "completed"})


def _generate_export_options(format: str) -> Dict[str, Any]:
    """Generate export options based on format."""
    
    base_options = {
        "include_speaker_notes": random.choice([True, False]),
        "include_slide_numbers": random.choice([True, False]),
        "compression": random.choice(["none", "standard", "high"]),
    }
    
    format_specific = {
        "pdf": {
            "slides_per_page": random.choice([1, 2, 4, 6]),
            "handout_mode": random.choice([True, False]),
            "include_outline": random.choice([True, False]),
        },
        "pptx": {
            "template": random.choice(["modern", "classic", "minimal"]),
            "include_animations": random.choice([True, False]),
            "editable_charts": random.choice([True, False]),
        },
        "beamer": {
            "theme": random.choice(["default", "AnnArbor", "Berlin", "Madrid"]),
            "include_navigation": random.choice([True, False]),
            "compile_to_pdf": random.choice([True, False]),
        },
        "google_slides": {
            "share_settings": random.choice(["view", "comment", "edit"]),
            "copy_to_drive": random.choice([True, False]),
        },
        "keynote": {
            "include_builds": random.choice([True, False]),
            "resolution": random.choice(["1024x768", "1920x1080", "custom"]),
        },
    }
    
    options = base_options.copy()
    options.update(format_specific.get(format, {}))
    
    return options