"""
Integration tests for full presentation generation flow.

Tests the complete end-to-end presentation creation process from
request submission through generation, processing, and retrieval.
"""
import asyncio
import json
from typing import Dict
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.schemas.generation import GenerationRequest, GenerationStatus
from app.domain.schemas.presentation import PresentationResponse
from app.repositories.presentation import PresentationRepository
from app.repositories.generation_job import GenerationJobRepository


@pytest.mark.integration
@pytest.mark.asyncio
class TestPresentationGenerationFlow:
    """Test complete presentation generation workflow."""
    
    async def test_full_generation_flow(
        self,
        authenticated_client: AsyncClient,
        test_presentation_data: Dict,
        mock_ai_responses,
        db_session: AsyncSession,
    ):
        """Test complete presentation generation from request to completion."""
        # Step 1: Submit generation request
        response = await authenticated_client.post(
            "/api/v1/presentations/generate",
            json=test_presentation_data,
        )
        assert response.status_code == 202
        
        data = response.json()
        assert "job_id" in data
        assert "status" in data
        assert data["status"] == "pending"
        
        job_id = data["job_id"]
        
        # Step 2: Check job status
        response = await authenticated_client.get(
            f"/api/v1/generation/jobs/{job_id}"
        )
        assert response.status_code == 200
        
        job_data = response.json()
        assert job_data["id"] == job_id
        assert job_data["status"] in ["pending", "processing", "completed"]
        
        # Step 3: Wait for completion (with timeout)
        max_attempts = 30
        for _ in range(max_attempts):
            response = await authenticated_client.get(
                f"/api/v1/generation/jobs/{job_id}"
            )
            job_data = response.json()
            
            if job_data["status"] == "completed":
                break
            elif job_data["status"] == "failed":
                pytest.fail(f"Job failed: {job_data.get('error')}")
            
            await asyncio.sleep(1)
        else:
            pytest.fail("Job did not complete within timeout")
        
        # Step 4: Retrieve generated presentation
        presentation_id = job_data["presentation_id"]
        response = await authenticated_client.get(
            f"/api/v1/presentations/{presentation_id}"
        )
        assert response.status_code == 200
        
        presentation = response.json()
        assert presentation["title"] == test_presentation_data["title"]
        assert len(presentation["slides"]) > 0
        
        # Verify database state
        pres_repo = PresentationRepository(db_session)
        db_presentation = await pres_repo.get(presentation_id)
        assert db_presentation is not None
        assert db_presentation.title == test_presentation_data["title"]
    
    async def test_generation_with_template(
        self,
        authenticated_client: AsyncClient,
        test_presentation_data: Dict,
        mock_ai_responses,
    ):
        """Test presentation generation using a template."""
        # First, get available templates
        response = await authenticated_client.get(
            "/api/v1/templates",
            params={"category": "academic"}
        )
        assert response.status_code == 200
        
        templates = response.json()
        assert len(templates) > 0
        
        template_id = templates[0]["id"]
        
        # Generate presentation with template
        generation_data = {
            **test_presentation_data,
            "template_id": template_id,
        }
        
        response = await authenticated_client.post(
            "/api/v1/presentations/generate",
            json=generation_data,
        )
        assert response.status_code == 202
        
        job_data = response.json()
        assert job_data["template_id"] == template_id
    
    async def test_generation_progress_tracking(
        self,
        authenticated_client: AsyncClient,
        test_presentation_data: Dict,
        mock_ai_responses,
    ):
        """Test real-time progress tracking during generation."""
        # Submit generation request
        response = await authenticated_client.post(
            "/api/v1/presentations/generate",
            json=test_presentation_data,
        )
        job_id = response.json()["job_id"]
        
        # Track progress updates
        progress_updates = []
        max_checks = 20
        
        for _ in range(max_checks):
            response = await authenticated_client.get(
                f"/api/v1/generation/jobs/{job_id}"
            )
            job_data = response.json()
            
            if "progress" in job_data:
                progress_updates.append(job_data["progress"])
            
            if job_data["status"] == "completed":
                break
            
            await asyncio.sleep(0.5)
        
        # Verify progress was tracked
        assert len(progress_updates) > 0
        assert all(0 <= p <= 100 for p in progress_updates)
        assert progress_updates[-1] == 100
    
    async def test_concurrent_generation_requests(
        self,
        authenticated_client: AsyncClient,
        test_presentation_data: Dict,
        mock_ai_responses,
    ):
        """Test handling multiple concurrent generation requests."""
        # Submit multiple requests concurrently
        num_requests = 5
        
        async def submit_request(index: int):
            data = {
                **test_presentation_data,
                "title": f"{test_presentation_data['title']} - Version {index}",
            }
            response = await authenticated_client.post(
                "/api/v1/presentations/generate",
                json=data,
            )
            return response.json()["job_id"]
        
        # Submit all requests
        job_ids = await asyncio.gather(
            *[submit_request(i) for i in range(num_requests)]
        )
        
        assert len(job_ids) == num_requests
        assert len(set(job_ids)) == num_requests  # All unique
        
        # Wait for all to complete
        async def wait_for_completion(job_id: str):
            for _ in range(30):
                response = await authenticated_client.get(
                    f"/api/v1/generation/jobs/{job_id}"
                )
                if response.json()["status"] == "completed":
                    return True
                await asyncio.sleep(1)
            return False
        
        results = await asyncio.gather(
            *[wait_for_completion(job_id) for job_id in job_ids]
        )
        
        assert all(results), "Not all jobs completed"
    
    async def test_generation_failure_handling(
        self,
        authenticated_client: AsyncClient,
        test_presentation_data: Dict,
        mocker,
    ):
        """Test handling of generation failures."""
        # Mock AI service to fail
        mocker.patch(
            "app.services.ai.anthropic_provider.AnthropicProvider.generate",
            side_effect=Exception("AI service error"),
        )
        mocker.patch(
            "app.services.ai.openai_provider.OpenAIProvider.generate",
            side_effect=Exception("Fallback also failed"),
        )
        
        # Submit request
        response = await authenticated_client.post(
            "/api/v1/presentations/generate",
            json=test_presentation_data,
        )
        assert response.status_code == 202
        
        job_id = response.json()["job_id"]
        
        # Wait for failure
        for _ in range(20):
            response = await authenticated_client.get(
                f"/api/v1/generation/jobs/{job_id}"
            )
            job_data = response.json()
            
            if job_data["status"] == "failed":
                assert "error" in job_data
                assert "AI service error" in job_data["error"]
                break
            
            await asyncio.sleep(0.5)
        else:
            pytest.fail("Job did not fail as expected")
    
    async def test_generation_cancellation(
        self,
        authenticated_client: AsyncClient,
        test_presentation_data: Dict,
        mock_ai_responses,
    ):
        """Test cancellation of in-progress generation."""
        # Submit request
        response = await authenticated_client.post(
            "/api/v1/presentations/generate",
            json=test_presentation_data,
        )
        job_id = response.json()["job_id"]
        
        # Wait for processing to start
        for _ in range(10):
            response = await authenticated_client.get(
                f"/api/v1/generation/jobs/{job_id}"
            )
            if response.json()["status"] == "processing":
                break
            await asyncio.sleep(0.2)
        
        # Cancel the job
        response = await authenticated_client.post(
            f"/api/v1/generation/jobs/{job_id}/cancel"
        )
        assert response.status_code == 200
        
        # Verify cancellation
        response = await authenticated_client.get(
            f"/api/v1/generation/jobs/{job_id}"
        )
        job_data = response.json()
        assert job_data["status"] == "cancelled"
    
    async def test_generation_with_citations(
        self,
        authenticated_client: AsyncClient,
        test_presentation_data: Dict,
        mock_ai_responses,
    ):
        """Test generation with academic citations."""
        # Update mock to include citations
        mock_ai_responses["anthropic"].return_value = {
            "title": "Test Presentation",
            "slides": [
                {
                    "type": "content",
                    "title": "Literature Review",
                    "content": {
                        "text": "Recent studies show significant results (Smith et al., 2023).",
                        "citations": [
                            {
                                "id": "smith2023",
                                "authors": ["Smith, J.", "Doe, A."],
                                "title": "Machine Learning in Medicine",
                                "year": 2023,
                                "journal": "Nature Medicine",
                            }
                        ],
                    },
                },
            ],
        }
        
        # Generate with citations
        data = {
            **test_presentation_data,
            "include_citations": True,
            "citation_style": "APA",
        }
        
        response = await authenticated_client.post(
            "/api/v1/presentations/generate",
            json=data,
        )
        job_id = response.json()["job_id"]
        
        # Wait for completion
        presentation_id = None
        for _ in range(30):
            response = await authenticated_client.get(
                f"/api/v1/generation/jobs/{job_id}"
            )
            job_data = response.json()
            
            if job_data["status"] == "completed":
                presentation_id = job_data["presentation_id"]
                break
            
            await asyncio.sleep(0.5)
        
        assert presentation_id is not None
        
        # Verify citations in presentation
        response = await authenticated_client.get(
            f"/api/v1/presentations/{presentation_id}"
        )
        presentation = response.json()
        
        # Find slide with citations
        citation_slide = next(
            (s for s in presentation["slides"] if "citations" in s.get("content", {})),
            None
        )
        assert citation_slide is not None
        assert len(citation_slide["content"]["citations"]) > 0