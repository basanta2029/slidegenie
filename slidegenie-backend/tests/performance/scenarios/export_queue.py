"""
Export queue stress testing.

Tests the export system's ability to handle concurrent export requests
across different formats (PPTX, PDF, Beamer, Google Slides).
"""
from locust import task, events, constant_throughput
import random
import logging
import time
from collections import defaultdict

from ..base_user import BaseSlideGenieUser
from ..config import config
from ..utils import generate_test_data, measure_time, metrics


logger = logging.getLogger(__name__)


class ExportQueueUser(BaseSlideGenieUser):
    """User that stresses the export queue system."""
    
    wait_time = constant_throughput(0.5)  # 0.5 requests per second per user
    
    def on_start(self):
        """Create test presentations for export."""
        super().on_start()
        self.export_formats = ["pptx", "pdf", "beamer", "google-slides"]
        self.queue_metrics = defaultdict(list)
        self._create_test_presentations()
        
    def _create_test_presentations(self):
        """Create a pool of presentations to export."""
        # Get templates
        response = self.make_authenticated_request(
            "get",
            f"{config.api_prefix}/templates",
            name="Get templates for export"
        )
        
        if response.status_code != 200:
            logger.error("Failed to get templates")
            return
            
        templates = response.json().get("items", [])
        if not templates:
            logger.error("No templates available")
            return
            
        # Create 5-10 test presentations
        num_presentations = random.randint(5, 10)
        for i in range(num_presentations):
            template = random.choice(templates)
            presentation_id = self.create_presentation(
                title=f"Export Test {i} - {generate_test_data.random_string(5)}",
                template_id=template["id"]
            )
            
            if presentation_id:
                # Add some slides to make export more realistic
                self._add_slides_to_presentation(presentation_id, random.randint(10, 30))
                
    def _add_slides_to_presentation(self, presentation_id: str, slide_count: int):
        """Add slides to a presentation."""
        slides = []
        for i in range(slide_count):
            slide_data = generate_test_data.slide_content()
            slide_data["position"] = i + 1
            slides.append(slide_data)
            
        response = self.make_authenticated_request(
            "post",
            f"{config.api_prefix}/presentations/{presentation_id}/slides/bulk",
            name="Add slides for export",
            json={"slides": slides}
        )
        
        if response.status_code != 201:
            logger.warning(f"Failed to add slides: {response.text}")
            
    @task(10)
    def export_to_pptx(self):
        """Export presentation to PowerPoint format."""
        if not self.presentation_ids:
            return
            
        presentation_id = random.choice(self.presentation_ids)
        self._perform_export(presentation_id, "pptx")
        
    @task(8)
    def export_to_pdf(self):
        """Export presentation to PDF format."""
        if not self.presentation_ids:
            return
            
        presentation_id = random.choice(self.presentation_ids)
        self._perform_export(presentation_id, "pdf")
        
    @task(5)
    def export_to_beamer(self):
        """Export presentation to LaTeX Beamer format."""
        if not self.presentation_ids:
            return
            
        presentation_id = random.choice(self.presentation_ids)
        self._perform_export(presentation_id, "beamer")
        
    @task(3)
    def export_to_google_slides(self):
        """Export presentation to Google Slides format."""
        if not self.presentation_ids:
            return
            
        presentation_id = random.choice(self.presentation_ids)
        self._perform_export(presentation_id, "google-slides")
        
    @task(5)
    def concurrent_format_export(self):
        """Export same presentation to multiple formats concurrently."""
        if not self.presentation_ids:
            return
            
        presentation_id = random.choice(self.presentation_ids)
        formats = random.sample(self.export_formats, random.randint(2, 4))
        
        # Start all exports
        export_jobs = []
        for format in formats:
            job_id = self._start_export(presentation_id, format)
            if job_id:
                export_jobs.append((job_id, format))
                
        # Wait for all exports to complete
        for job_id, format in export_jobs:
            self._wait_for_export(job_id, format)
            
    @task(3)
    def bulk_export_request(self):
        """Submit multiple export requests at once."""
        if len(self.presentation_ids) < 3:
            return
            
        # Select multiple presentations
        presentations = random.sample(
            self.presentation_ids,
            min(len(self.presentation_ids), random.randint(3, 5))
        )
        
        format = random.choice(self.export_formats)
        
        # Submit bulk export
        with measure_time() as timer:
            response = self.make_authenticated_request(
                "post",
                f"{config.api_prefix}/export/bulk",
                name=f"Bulk export to {format}",
                json={
                    "presentation_ids": presentations,
                    "format": format,
                    "options": {
                        "include_notes": True,
                        "include_animations": format in ["pptx", "google-slides"],
                        "compress": True
                    }
                },
                catch_response=True
            )
            
        if response.status_code == 202:
            response.success()
            bulk_job_id = response.json().get("bulk_job_id")
            metrics.record_metric("bulk_export_submission_time", timer.duration_ms)
            metrics.record_metric("bulk_export_count", len(presentations))
            
            # Wait for bulk job completion
            self._wait_for_bulk_export(bulk_job_id, len(presentations))
        else:
            response.failure(f"Bulk export failed: {response.text}")
            
    @task(2)
    def export_with_custom_options(self):
        """Export with various custom options to test processing complexity."""
        if not self.presentation_ids:
            return
            
        presentation_id = random.choice(self.presentation_ids)
        format = random.choice(["pptx", "pdf"])
        
        # Generate random export options
        options = {
            "include_speaker_notes": random.choice([True, False]),
            "include_slide_numbers": random.choice([True, False]),
            "include_date": random.choice([True, False]),
            "watermark": random.choice([None, "DRAFT", "CONFIDENTIAL"]),
            "quality": random.choice(["draft", "standard", "high"]),
            "color_mode": random.choice(["color", "grayscale", "black_white"]),
            "slides_per_page": random.choice([1, 2, 4, 6]) if format == "pdf" else 1
        }
        
        self._perform_export(presentation_id, format, options)
        
    @task(1)
    def stress_queue_limits(self):
        """Submit many exports rapidly to stress queue limits."""
        if not self.presentation_ids:
            return
            
        # Submit 10-20 exports in rapid succession
        num_exports = random.randint(10, 20)
        export_jobs = []
        
        for _ in range(num_exports):
            presentation_id = random.choice(self.presentation_ids)
            format = random.choice(self.export_formats)
            
            job_id = self._start_export(presentation_id, format, record_metrics=False)
            if job_id:
                export_jobs.append((job_id, format))
                
        metrics.record_metric("stress_test_exports_submitted", len(export_jobs))
        
        # Wait for all to complete
        completed = 0
        failed = 0
        
        for job_id, format in export_jobs:
            result = self._wait_for_export(job_id, format, record_metrics=False)
            if result.get("status") == "completed":
                completed += 1
            else:
                failed += 1
                
        metrics.record_metric("stress_test_exports_completed", completed)
        metrics.record_metric("stress_test_exports_failed", failed)
        
    def _perform_export(
        self,
        presentation_id: str,
        format: str,
        options: dict = None
    ):
        """Perform a complete export operation."""
        job_id = self._start_export(presentation_id, format, options)
        if job_id:
            self._wait_for_export(job_id, format)
            
    def _start_export(
        self,
        presentation_id: str,
        format: str,
        options: dict = None,
        record_metrics: bool = True
    ) -> str:
        """Start an export job."""
        endpoint = f"{config.api_prefix}/export/{format}"
        
        request_data = {
            "presentation_id": presentation_id,
            "options": options or {}
        }
        
        with measure_time() as timer:
            response = self.make_authenticated_request(
                "post",
                endpoint,
                name=f"Start {format} export",
                json=request_data,
                catch_response=True
            )
            
        if response.status_code == 202:
            response.success()
            job_data = response.json()
            job_id = job_data.get("job_id")
            
            if record_metrics:
                metrics.record_metric(f"export_{format}_start_time", timer.duration_ms)
                
                # Record queue position if provided
                if "queue_position" in job_data:
                    metrics.record_metric(f"export_queue_position_{format}", 
                                        job_data["queue_position"])
                    
            return job_id
        else:
            response.failure(f"Export start failed: {response.text}")
            if record_metrics:
                metrics.record_error(f"export_{format}_start_failed")
            return None
            
    def _wait_for_export(
        self,
        job_id: str,
        format: str,
        record_metrics: bool = True
    ) -> dict:
        """Wait for export job completion."""
        start_time = time.time()
        
        result = self.wait_for_job_completion(
            job_id,
            job_type="export",
            timeout=300
        )
        
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        
        if record_metrics:
            if result.get("status") == "completed":
                metrics.record_metric(f"export_{format}_completion_time", duration_ms)
                
                # Download the exported file to measure size
                if "download_url" in result:
                    self._download_export(result["download_url"], format)
                    
                # Record processing metrics if available
                if "metrics" in result:
                    job_metrics = result["metrics"]
                    if "processing_time_ms" in job_metrics:
                        metrics.record_metric(f"export_{format}_processing_time",
                                            job_metrics["processing_time_ms"])
                    if "file_size_bytes" in job_metrics:
                        metrics.record_metric(f"export_{format}_file_size_mb",
                                            job_metrics["file_size_bytes"] / (1024 * 1024))
            else:
                metrics.record_error(f"export_{format}_{result.get('status', 'unknown')}")
                
        return result
        
    def _wait_for_bulk_export(self, bulk_job_id: str, count: int):
        """Wait for bulk export completion."""
        start_time = time.time()
        
        result = self.wait_for_job_completion(
            bulk_job_id,
            job_type="export/bulk",
            timeout=600  # 10 minutes for bulk
        )
        
        duration_ms = (time.time() - start_time) * 1000
        
        if result.get("status") == "completed":
            metrics.record_metric("bulk_export_completion_time", duration_ms)
            metrics.record_metric("bulk_export_time_per_item", duration_ms / count)
            
            # Record individual job results
            if "jobs" in result:
                completed = sum(1 for job in result["jobs"] 
                              if job.get("status") == "completed")
                metrics.record_metric("bulk_export_success_count", completed)
                
    def _download_export(self, download_url: str, format: str):
        """Download exported file to measure download performance."""
        with measure_time() as timer:
            response = self.client.get(
                download_url,
                name=f"Download {format} export",
                headers=self.auth_headers,
                stream=True,
                catch_response=True
            )
            
        if response.status_code == 200:
            response.success()
            
            # Calculate download metrics
            file_size_mb = len(response.content) / (1024 * 1024)
            download_time_s = timer.duration_ms / 1000
            throughput_mbps = (file_size_mb * 8) / download_time_s
            
            metrics.record_metric(f"export_{format}_download_time", timer.duration_ms)
            metrics.record_metric(f"export_{format}_download_throughput_mbps", throughput_mbps)
        else:
            response.failure(f"Export download failed: {response.text}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Export queue metrics summary."""
    import os
    from datetime import datetime
    
    results_dir = "tests/performance/results"
    os.makedirs(results_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    metrics.export_to_file(f"{results_dir}/export_queue_metrics_{timestamp}.json")
    
    # Print export performance summary
    summary = metrics.get_summary()
    print("\n=== Export Queue Performance Summary ===")
    
    for format in ["pptx", "pdf", "beamer", "google-slides"]:
        metric_name = f"export_{format}_completion_time"
        if metric_name in summary["metrics"]:
            format_metrics = summary["metrics"][metric_name]
            print(f"\n{format.upper()} Export Completion Time:")
            print(f"  Count: {format_metrics['count']}")
            print(f"  P50: {format_metrics['p50']/1000:.2f}s")
            print(f"  P90: {format_metrics['p90']/1000:.2f}s")
            print(f"  P95: {format_metrics['p95']/1000:.2f}s")
            print(f"  Max: {format_metrics['max']/1000:.2f}s")