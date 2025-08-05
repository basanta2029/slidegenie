"""
File upload performance testing.

Tests concurrent file uploads, large file handling, and multipart upload performance.
"""
from locust import task, events, constant_pacing
import os
import random
import logging
from typing import Optional

from ..base_user import BaseSlideGenieUser
from ..config import config
from ..utils import generate_test_data, measure_time, metrics, create_test_file


logger = logging.getLogger(__name__)


class FileUploadUser(BaseSlideGenieUser):
    """User that performs file upload operations."""
    
    wait_time = constant_pacing(2)  # One request every 2 seconds
    
    def on_start(self):
        """Initialize test files."""
        super().on_start()
        self._ensure_test_files()
        
    def _ensure_test_files(self):
        """Ensure test files exist."""
        fixtures_dir = "tests/performance/fixtures"
        os.makedirs(fixtures_dir, exist_ok=True)
        
        # Create test files if they don't exist
        self.test_files = {
            "small_pdf": {
                "path": f"{fixtures_dir}/small_paper_1mb.pdf",
                "size_mb": 1,
                "type": "application/pdf"
            },
            "medium_pdf": {
                "path": f"{fixtures_dir}/medium_paper_10mb.pdf",
                "size_mb": 10,
                "type": "application/pdf"
            },
            "large_pdf": {
                "path": f"{fixtures_dir}/large_paper_50mb.pdf",
                "size_mb": 50,
                "type": "application/pdf"
            },
            "huge_pdf": {
                "path": f"{fixtures_dir}/huge_paper_100mb.pdf",
                "size_mb": 100,
                "type": "application/pdf"
            },
            "docx": {
                "path": f"{fixtures_dir}/thesis_5mb.docx",
                "size_mb": 5,
                "type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            },
            "latex": {
                "path": f"{fixtures_dir}/article_2mb.tex",
                "size_mb": 2,
                "type": "text/x-tex"
            }
        }
        
        for file_key, file_info in self.test_files.items():
            if not os.path.exists(file_info["path"]):
                logger.info(f"Creating test file: {file_info['path']}")
                create_test_file(
                    file_info["path"],
                    file_info["size_mb"],
                    content_type="binary" if "pdf" in file_key or "docx" in file_key else "text"
                )
                
    @task(10)
    def upload_small_file(self):
        """Upload a small file (1MB)."""
        file_info = self.test_files["small_pdf"]
        self._upload_file_with_metrics(file_info, "small")
        
    @task(5)
    def upload_medium_file(self):
        """Upload a medium file (10MB)."""
        file_info = self.test_files["medium_pdf"]
        self._upload_file_with_metrics(file_info, "medium")
        
    @task(3)
    def upload_large_file(self):
        """Upload a large file (50MB)."""
        file_info = self.test_files["large_pdf"]
        self._upload_file_with_metrics(file_info, "large")
        
    @task(1)
    def upload_huge_file(self):
        """Upload a huge file (100MB) to test limits."""
        file_info = self.test_files["huge_pdf"]
        self._upload_file_with_metrics(file_info, "huge")
        
    @task(5)
    def upload_multiple_formats(self):
        """Upload different file formats."""
        formats = ["docx", "latex", "small_pdf"]
        for format_key in random.sample(formats, 2):
            file_info = self.test_files[format_key]
            self._upload_file_with_metrics(file_info, format_key)
            
    @task(3)
    def concurrent_uploads(self):
        """Simulate concurrent uploads from same user."""
        import concurrent.futures
        
        files_to_upload = random.sample(["small_pdf", "medium_pdf", "docx"], 2)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = []
            for file_key in files_to_upload:
                file_info = self.test_files[file_key]
                future = executor.submit(
                    self._upload_file_with_metrics,
                    file_info,
                    f"concurrent_{file_key}"
                )
                futures.append(future)
                
            # Wait for all uploads to complete
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Concurrent upload failed: {e}")
                    
    @task(2)
    def upload_with_processing(self):
        """Upload file and wait for processing completion."""
        file_info = random.choice([
            self.test_files["small_pdf"],
            self.test_files["medium_pdf"],
            self.test_files["docx"]
        ])
        
        # Upload file
        upload_id = self._upload_file_with_metrics(file_info, "process")
        
        if upload_id:
            # Wait for processing
            with measure_time() as timer:
                result = self.wait_for_job_completion(
                    upload_id,
                    job_type="document-processing",
                    timeout=120
                )
                
            if result.get("status") == "completed":
                metrics.record_metric("file_processing_time", timer.duration_ms)
                
                # Get extracted content
                response = self.make_authenticated_request(
                    "get",
                    f"{config.api_prefix}/documents/{upload_id}/content",
                    name="Get processed content"
                )
                
                if response.status_code == 200:
                    content = response.json()
                    metrics.record_metric("extracted_pages", content.get("page_count", 0))
                    metrics.record_metric("extracted_words", content.get("word_count", 0))
                    
    @task(2)
    def multipart_upload(self):
        """Test multipart upload for large files."""
        file_info = random.choice([
            self.test_files["large_pdf"],
            self.test_files["huge_pdf"]
        ])
        
        # Initiate multipart upload
        with measure_time() as init_timer:
            response = self.make_authenticated_request(
                "post",
                f"{config.api_prefix}/documents/upload/multipart/init",
                name="Init multipart upload",
                json={
                    "filename": os.path.basename(file_info["path"]),
                    "file_size": file_info["size_mb"] * 1024 * 1024,
                    "content_type": file_info["type"]
                },
                catch_response=True
            )
            
        if response.status_code != 200:
            response.failure(f"Multipart init failed: {response.text}")
            return
            
        upload_data = response.json()
        upload_id = upload_data.get("upload_id")
        part_size = upload_data.get("part_size", 8 * 1024 * 1024)  # 8MB default
        
        response.success()
        metrics.record_metric("multipart_init_time", init_timer.duration_ms)
        
        # Upload parts
        with open(file_info["path"], "rb") as f:
            part_number = 1
            total_upload_time = 0
            
            while True:
                chunk = f.read(part_size)
                if not chunk:
                    break
                    
                with measure_time() as part_timer:
                    part_response = self.make_authenticated_request(
                        "put",
                        f"{config.api_prefix}/documents/upload/multipart/{upload_id}/part/{part_number}",
                        name=f"Upload part {part_number}",
                        data=chunk,
                        headers={"Content-Type": "application/octet-stream"},
                        catch_response=True
                    )
                    
                if part_response.status_code == 200:
                    part_response.success()
                    total_upload_time += part_timer.duration_ms
                else:
                    part_response.failure(f"Part upload failed: {part_response.text}")
                    return
                    
                part_number += 1
                
        # Complete multipart upload
        with measure_time() as complete_timer:
            complete_response = self.make_authenticated_request(
                "post",
                f"{config.api_prefix}/documents/upload/multipart/{upload_id}/complete",
                name="Complete multipart upload",
                catch_response=True
            )
            
        if complete_response.status_code == 200:
            complete_response.success()
            metrics.record_metric("multipart_complete_time", complete_timer.duration_ms)
            metrics.record_metric("multipart_total_time", 
                                init_timer.duration_ms + total_upload_time + complete_timer.duration_ms)
            metrics.record_metric("multipart_parts_count", part_number - 1)
        else:
            complete_response.failure(f"Multipart complete failed: {complete_response.text}")
            
    def _upload_file_with_metrics(
        self,
        file_info: dict,
        category: str
    ) -> Optional[str]:
        """Upload a file and record detailed metrics."""
        file_path = file_info["path"]
        file_size_mb = file_info["size_mb"]
        
        # Record upload start
        with measure_time() as timer:
            with open(file_path, "rb") as f:
                files = {
                    "file": (
                        os.path.basename(file_path),
                        f,
                        file_info["type"]
                    )
                }
                
                # Add metadata
                data = {
                    "title": f"Test upload {category} - {generate_test_data.random_string(5)}",
                    "description": f"Performance test upload of {file_size_mb}MB file",
                    "tags": ["performance-test", category]
                }
                
                response = self.make_authenticated_request(
                    "post",
                    f"{config.api_prefix}/documents/upload",
                    name=f"Upload {category} file ({file_size_mb}MB)",
                    files=files,
                    data=data,
                    catch_response=True
                )
                
        if response.status_code == 200:
            response.success()
            upload_data = response.json()
            upload_id = upload_data.get("upload_id")
            
            # Calculate and record metrics
            upload_time_ms = timer.duration_ms
            throughput_mbps = (file_size_mb * 8) / (upload_time_ms / 1000)  # Megabits per second
            
            metrics.record_metric(f"upload_time_{category}", upload_time_ms)
            metrics.record_metric(f"upload_throughput_mbps_{category}", throughput_mbps)
            metrics.record_metric("upload_file_size_mb", file_size_mb)
            
            # Check if server reported processing time
            if "processing_time_ms" in upload_data:
                metrics.record_metric("server_processing_time", upload_data["processing_time_ms"])
                
            return upload_id
        else:
            response.failure(f"Upload failed: {response.text}")
            metrics.record_error(f"upload_failed_{category}")
            return None


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Export file upload metrics."""
    import os
    from datetime import datetime
    
    results_dir = "tests/performance/results"
    os.makedirs(results_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    metrics.export_to_file(f"{results_dir}/file_upload_metrics_{timestamp}.json")
    
    # Print upload performance summary
    summary = metrics.get_summary()
    print("\n=== File Upload Performance Summary ===")
    
    for size in ["small", "medium", "large", "huge"]:
        metric_name = f"upload_time_{size}"
        if metric_name in summary["metrics"]:
            size_metrics = summary["metrics"][metric_name]
            print(f"\n{size.capitalize()} File Upload Time:")
            print(f"  Count: {size_metrics['count']}")
            print(f"  P50: {size_metrics['p50']:.2f}ms")
            print(f"  P90: {size_metrics['p90']:.2f}ms")
            print(f"  P95: {size_metrics['p95']:.2f}ms")