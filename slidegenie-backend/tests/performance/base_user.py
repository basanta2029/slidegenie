"""
Base user class for performance tests.
"""
import json
import time
from typing import Dict, Optional, Any
from locust import HttpUser, task, between, events
from locust.exception import RescheduleTask
import logging

from .config import config
from .utils import generate_test_data, measure_time


logger = logging.getLogger(__name__)


class BaseSlideGenieUser(HttpUser):
    """Base user class with common functionality."""
    
    abstract = True
    wait_time = between(1, 5)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.presentation_ids: list[str] = []
        self.upload_job_ids: list[str] = []
        self.export_job_ids: list[str] = []
        
    def on_start(self):
        """Called when a user starts."""
        self.login()
        
    def on_stop(self):
        """Called when a user stops."""
        self.logout()
        
    def login(self):
        """Authenticate the user."""
        with self.client.post(
            f"{config.api_prefix}/auth/login",
            json={
                "email": config.test_user_email,
                "password": config.test_user_password
            },
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                self.user_id = data.get("user", {}).get("id")
                response.success()
                logger.info(f"User {self.user_id} logged in successfully")
            else:
                response.failure(f"Login failed: {response.text}")
                raise RescheduleTask()
                
    def logout(self):
        """Logout the user."""
        if self.access_token:
            self.client.post(
                f"{config.api_prefix}/auth/logout",
                headers=self.auth_headers
            )
            
    @property
    def auth_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        if not self.access_token:
            return {}
        return {"Authorization": f"Bearer {self.access_token}"}
    
    def refresh_auth_token(self):
        """Refresh the authentication token."""
        if not self.refresh_token:
            self.login()
            return
            
        with self.client.post(
            f"{config.api_prefix}/auth/refresh",
            json={"refresh_token": self.refresh_token},
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                response.success()
            else:
                response.failure(f"Token refresh failed: {response.text}")
                self.login()  # Re-login if refresh fails
                
    def make_authenticated_request(
        self,
        method: str,
        url: str,
        name: Optional[str] = None,
        **kwargs
    ) -> Any:
        """Make an authenticated request with automatic retry on 401."""
        headers = kwargs.get("headers", {})
        headers.update(self.auth_headers)
        kwargs["headers"] = headers
        
        if name:
            kwargs["name"] = name
            
        # First attempt
        response = getattr(self.client, method)(url, **kwargs)
        
        # Retry with refreshed token if unauthorized
        if response.status_code == 401:
            self.refresh_auth_token()
            headers.update(self.auth_headers)
            response = getattr(self.client, method)(url, **kwargs)
            
        return response
    
    def wait_for_job_completion(
        self,
        job_id: str,
        job_type: str = "generation",
        timeout: int = 300,
        poll_interval: int = 2
    ) -> Dict[str, Any]:
        """Wait for an async job to complete."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            response = self.make_authenticated_request(
                "get",
                f"{config.api_prefix}/{job_type}/status/{job_id}",
                name=f"Check {job_type} status"
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                
                if status in ["completed", "failed", "cancelled"]:
                    return data
                    
            time.sleep(poll_interval)
            
        return {"status": "timeout", "error": f"Job {job_id} timed out after {timeout}s"}
    
    def upload_file(
        self,
        file_path: str,
        file_type: str = "pdf",
        name: Optional[str] = None
    ) -> Optional[str]:
        """Upload a file and return the upload ID."""
        with open(file_path, "rb") as f:
            files = {"file": (file_path.split("/")[-1], f, f"application/{file_type}")}
            
            with measure_time() as timer:
                response = self.make_authenticated_request(
                    "post",
                    f"{config.api_prefix}/documents/upload",
                    name=name or f"Upload {file_type} file",
                    files=files,
                    catch_response=True
                )
                
            if response.status_code == 200:
                data = response.json()
                upload_id = data.get("upload_id")
                self.upload_job_ids.append(upload_id)
                
                # Report custom metric
                events.request.fire(
                    request_type="FILE_UPLOAD",
                    name=f"Upload {file_type}",
                    response_time=timer.duration_ms,
                    response_length=len(response.content),
                    response=response,
                    exception=None,
                    context={}
                )
                
                response.success()
                return upload_id
            else:
                response.failure(f"File upload failed: {response.text}")
                return None
                
    def create_presentation(
        self,
        title: str,
        template_id: str,
        content: Optional[Dict] = None
    ) -> Optional[str]:
        """Create a new presentation."""
        data = {
            "title": title,
            "template_id": template_id,
            "content": content or generate_test_data.presentation_content()
        }
        
        response = self.make_authenticated_request(
            "post",
            f"{config.api_prefix}/presentations",
            name="Create presentation",
            json=data,
            catch_response=True
        )
        
        if response.status_code == 201:
            presentation_id = response.json().get("id")
            self.presentation_ids.append(presentation_id)
            response.success()
            return presentation_id
        else:
            response.failure(f"Presentation creation failed: {response.text}")
            return None
            
    def export_presentation(
        self,
        presentation_id: str,
        format: str = "pptx"
    ) -> Optional[str]:
        """Export a presentation."""
        response = self.make_authenticated_request(
            "post",
            f"{config.api_prefix}/export/{format}",
            name=f"Export to {format}",
            json={"presentation_id": presentation_id},
            catch_response=True
        )
        
        if response.status_code == 202:
            export_id = response.json().get("export_id")
            self.export_job_ids.append(export_id)
            response.success()
            return export_id
        else:
            response.failure(f"Export failed: {response.text}")
            return None