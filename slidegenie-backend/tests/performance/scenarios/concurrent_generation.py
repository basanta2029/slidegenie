"""
Concurrent presentation generation load test.

Tests the system's ability to handle multiple simultaneous presentation
generation requests, including AI processing and queue management.
"""
from locust import task, events
from locust.exception import RescheduleTask
import random
import logging
import time

from ..base_user import BaseSlideGenieUser
from ..config import config
from ..utils import generate_test_data, measure_time, metrics


logger = logging.getLogger(__name__)


class PresentationGenerationUser(BaseSlideGenieUser):
    """User that generates presentations concurrently."""
    
    def on_start(self):
        """Initialize user with templates."""
        super().on_start()
        self.template_ids = self.fetch_templates()
        if not self.template_ids:
            logger.error("No templates available")
            raise RescheduleTask()
            
    def fetch_templates(self):
        """Fetch available templates."""
        response = self.make_authenticated_request(
            "get",
            f"{config.api_prefix}/templates",
            name="Get templates"
        )
        
        if response.status_code == 200:
            templates = response.json().get("items", [])
            return [t["id"] for t in templates if t.get("is_active")]
        return []
        
    @task(10)
    def generate_presentation_from_scratch(self):
        """Generate a presentation from scratch using AI."""
        template_id = random.choice(self.template_ids)
        
        # Start generation
        with measure_time() as timer:
            response = self.make_authenticated_request(
                "post",
                f"{config.api_prefix}/generation/start",
                name="Start generation",
                json={
                    "title": generate_test_data.presentation_title(),
                    "template_id": template_id,
                    "content": generate_test_data.presentation_content(),
                    "options": {
                        "ai_provider": random.choice(["anthropic", "openai"]),
                        "quality": random.choice(["draft", "standard", "premium"]),
                        "include_speaker_notes": True,
                        "include_references": True
                    }
                },
                catch_response=True
            )
            
        if response.status_code == 202:
            job_id = response.json().get("job_id")
            response.success()
            
            # Record generation start time
            metrics.record_metric("generation_start_time", timer.duration_ms)
            
            # Wait for completion
            self.wait_for_generation_completion(job_id)
        else:
            response.failure(f"Generation start failed: {response.text}")
            metrics.record_error("generation_start_failed")
            
    @task(5)
    def generate_presentation_from_document(self):
        """Generate a presentation from an uploaded document."""
        # First upload a document
        upload_id = self.upload_file(
            config.sample_pdf_path,
            file_type="pdf",
            name="Upload PDF for generation"
        )
        
        if not upload_id:
            return
            
        template_id = random.choice(self.template_ids)
        
        # Start generation from document
        with measure_time() as timer:
            response = self.make_authenticated_request(
                "post",
                f"{config.api_prefix}/generation/from-document",
                name="Generate from document",
                json={
                    "upload_id": upload_id,
                    "template_id": template_id,
                    "options": {
                        "extract_images": True,
                        "extract_tables": True,
                        "max_slides": random.choice([10, 20, 30, 50])
                    }
                },
                catch_response=True
            )
            
        if response.status_code == 202:
            job_id = response.json().get("job_id")
            response.success()
            
            # Record document generation time
            metrics.record_metric("document_generation_start_time", timer.duration_ms)
            
            # Wait for completion
            self.wait_for_generation_completion(job_id)
        else:
            response.failure(f"Document generation failed: {response.text}")
            metrics.record_error("document_generation_failed")
            
    @task(3)
    def generate_with_ai_suggestions(self):
        """Generate presentation with AI suggestions and iterations."""
        template_id = random.choice(self.template_ids)
        
        # Create initial presentation
        presentation_id = self.create_presentation(
            title=generate_test_data.presentation_title(),
            template_id=template_id
        )
        
        if not presentation_id:
            return
            
        # Request AI suggestions
        response = self.make_authenticated_request(
            "post",
            f"{config.api_prefix}/generation/suggestions",
            name="Get AI suggestions",
            json={
                "presentation_id": presentation_id,
                "suggestion_types": ["content", "design", "flow", "references"]
            },
            catch_response=True
        )
        
        if response.status_code == 200:
            suggestions = response.json().get("suggestions", [])
            response.success()
            
            # Apply some suggestions
            for suggestion in suggestions[:3]:  # Apply up to 3 suggestions
                self.apply_ai_suggestion(presentation_id, suggestion)
        else:
            response.failure(f"AI suggestions failed: {response.text}")
            
    @task(2)
    def bulk_slide_generation(self):
        """Generate multiple slides in bulk."""
        presentation_id = random.choice(self.presentation_ids) if self.presentation_ids else None
        
        if not presentation_id:
            # Create a new presentation if none exist
            presentation_id = self.create_presentation(
                title=generate_test_data.presentation_title(),
                template_id=random.choice(self.template_ids)
            )
            
        if not presentation_id:
            return
            
        # Generate multiple slides
        slide_count = random.randint(5, 15)
        
        with measure_time() as timer:
            response = self.make_authenticated_request(
                "post",
                f"{config.api_prefix}/generation/bulk-slides",
                name="Bulk slide generation",
                json={
                    "presentation_id": presentation_id,
                    "slides": [
                        generate_test_data.slide_content() 
                        for _ in range(slide_count)
                    ]
                },
                catch_response=True
            )
            
        if response.status_code == 202:
            job_id = response.json().get("job_id")
            response.success()
            
            # Record bulk generation metrics
            metrics.record_metric("bulk_slide_generation_time", timer.duration_ms)
            metrics.record_metric("bulk_slide_count", slide_count)
            
            # Wait for completion
            self.wait_for_generation_completion(job_id, timeout=180)
        else:
            response.failure(f"Bulk slide generation failed: {response.text}")
            
    def wait_for_generation_completion(self, job_id: str, timeout: int = 300):
        """Wait for generation job to complete and record metrics."""
        start_time = time.time()
        
        result = self.wait_for_job_completion(
            job_id,
            job_type="generation",
            timeout=timeout
        )
        
        end_time = time.time()
        duration = (end_time - start_time) * 1000  # Convert to ms
        
        if result.get("status") == "completed":
            metrics.record_metric("generation_completion_time", duration)
            
            # Record additional metrics from result
            if "metrics" in result:
                job_metrics = result["metrics"]
                metrics.record_metric("ai_tokens_used", job_metrics.get("tokens_used", 0))
                metrics.record_metric("ai_api_calls", job_metrics.get("api_calls", 0))
                metrics.record_metric("slides_generated", job_metrics.get("slides_count", 0))
        else:
            metrics.record_error(f"generation_{result.get('status', 'unknown')}")
            
    def apply_ai_suggestion(self, presentation_id: str, suggestion: dict):
        """Apply an AI suggestion to a presentation."""
        response = self.make_authenticated_request(
            "post",
            f"{config.api_prefix}/generation/apply-suggestion",
            name="Apply AI suggestion",
            json={
                "presentation_id": presentation_id,
                "suggestion_id": suggestion.get("id"),
                "confirmation": True
            },
            catch_response=True
        )
        
        if response.status_code == 200:
            response.success()
        else:
            response.failure(f"Apply suggestion failed: {response.text}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Export metrics when test stops."""
    import os
    from datetime import datetime
    
    # Create results directory
    results_dir = "tests/performance/results"
    os.makedirs(results_dir, exist_ok=True)
    
    # Export metrics
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    metrics.export_to_file(f"{results_dir}/generation_metrics_{timestamp}.json")
    
    # Print summary
    summary = metrics.get_summary()
    print("\n=== Generation Performance Summary ===")
    print(f"Total duration: {summary['duration_seconds']:.2f}s")
    
    if "generation_completion_time" in summary["metrics"]:
        gen_metrics = summary["metrics"]["generation_completion_time"]
        print(f"\nGeneration Completion Time:")
        print(f"  P50: {gen_metrics['p50']:.2f}ms")
        print(f"  P90: {gen_metrics['p90']:.2f}ms")
        print(f"  P95: {gen_metrics['p95']:.2f}ms")
        print(f"  P99: {gen_metrics['p99']:.2f}ms")