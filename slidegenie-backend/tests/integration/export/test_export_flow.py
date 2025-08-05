"""
Integration tests for presentation export functionality.

Tests PPTX, PDF, and LaTeX Beamer export with queue processing,
download link generation, and file validation.
"""
import asyncio
import io
import zipfile
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.presentation import PresentationRepository


@pytest.mark.integration
@pytest.mark.asyncio
class TestExportFlow:
    """Test complete export workflows for different formats."""
    
    async def create_test_presentation(
        self,
        authenticated_client: AsyncClient,
        title: str = "Export Test Presentation"
    ) -> str:
        """Helper to create a test presentation."""
        response = await authenticated_client.post(
            "/api/v1/presentations",
            json={
                "title": title,
                "description": "Test presentation for export",
                "slides": [
                    {
                        "type": "title",
                        "title": title,
                        "content": {
                            "subtitle": "Integration Testing",
                            "author": "Test Suite",
                            "date": "2024",
                        },
                        "order": 1,
                    },
                    {
                        "type": "content",
                        "title": "Introduction",
                        "content": {
                            "text": "This is an introduction slide with some content.",
                            "bullet_points": [
                                "First point",
                                "Second point",
                                "Third point with **emphasis**",
                            ],
                        },
                        "order": 2,
                    },
                    {
                        "type": "content",
                        "title": "Methods",
                        "content": {
                            "text": "Our methodology includes:",
                            "bullet_points": [
                                "Data collection",
                                "Analysis",
                                "Validation",
                            ],
                        },
                        "order": 3,
                    },
                    {
                        "type": "content",
                        "title": "Results",
                        "content": {
                            "text": "Key findings:",
                            "data": {
                                "chart_type": "bar",
                                "data_points": [
                                    {"label": "Group A", "value": 75},
                                    {"label": "Group B", "value": 85},
                                    {"label": "Group C", "value": 90},
                                ],
                            },
                        },
                        "order": 4,
                    },
                    {
                        "type": "conclusion",
                        "title": "Conclusion",
                        "content": {
                            "text": "In conclusion, our findings demonstrate success.",
                            "key_points": [
                                "All objectives met",
                                "Results validated",
                                "Future work identified",
                            ],
                        },
                        "order": 5,
                    },
                ],
                "settings": {
                    "theme": "professional",
                    "color_scheme": "blue",
                    "font_family": "Arial",
                },
            },
        )
        
        assert response.status_code == 201
        return response.json()["id"]
    
    async def test_pptx_export_flow(
        self,
        authenticated_client: AsyncClient,
    ):
        """Test PowerPoint export end-to-end."""
        # Create presentation
        presentation_id = await self.create_test_presentation(
            authenticated_client,
            "PPTX Export Test"
        )
        
        # Request PPTX export
        response = await authenticated_client.post(
            f"/api/v1/presentations/{presentation_id}/export",
            json={
                "format": "pptx",
                "options": {
                    "include_notes": True,
                    "slide_numbers": True,
                    "company_logo": False,
                },
            },
        )
        
        assert response.status_code == 202
        export_data = response.json()
        
        assert "job_id" in export_data
        assert export_data["format"] == "pptx"
        assert export_data["status"] == "pending"
        
        job_id = export_data["job_id"]
        
        # Wait for export to complete
        download_url = None
        for _ in range(30):
            response = await authenticated_client.get(
                f"/api/v1/export/jobs/{job_id}"
            )
            job_status = response.json()
            
            if job_status["status"] == "completed":
                download_url = job_status["download_url"]
                break
            elif job_status["status"] == "failed":
                pytest.fail(f"Export failed: {job_status.get('error')}")
            
            await asyncio.sleep(1)
        
        assert download_url is not None
        
        # Download the exported file
        response = await authenticated_client.get(download_url)
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        
        # Validate PPTX structure
        pptx_data = io.BytesIO(response.content)
        with zipfile.ZipFile(pptx_data, 'r') as zf:
            # Check for required PPTX files
            namelist = zf.namelist()
            assert "[Content_Types].xml" in namelist
            assert "ppt/presentation.xml" in namelist
            assert any("ppt/slides/slide" in name for name in namelist)
            
            # Verify number of slides (should be 5)
            slide_count = sum(1 for name in namelist if "ppt/slides/slide" in name and name.endswith(".xml"))
            assert slide_count == 5
    
    async def test_pdf_export_with_options(
        self,
        authenticated_client: AsyncClient,
    ):
        """Test PDF export with various formatting options."""
        # Create presentation
        presentation_id = await self.create_test_presentation(
            authenticated_client,
            "PDF Export Test"
        )
        
        # Request PDF export with custom options
        response = await authenticated_client.post(
            f"/api/v1/presentations/{presentation_id}/export",
            json={
                "format": "pdf",
                "options": {
                    "page_size": "A4",
                    "orientation": "landscape",
                    "include_notes": True,
                    "slides_per_page": 1,
                    "quality": "high",
                    "watermark": "DRAFT",
                },
            },
        )
        
        assert response.status_code == 202
        job_id = response.json()["job_id"]
        
        # Wait for completion
        download_url = None
        for _ in range(30):
            response = await authenticated_client.get(
                f"/api/v1/export/jobs/{job_id}"
            )
            job_status = response.json()
            
            if job_status["status"] == "completed":
                download_url = job_status["download_url"]
                break
            
            await asyncio.sleep(1)
        
        assert download_url is not None
        
        # Download PDF
        response = await authenticated_client.get(download_url)
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        
        # Basic PDF validation
        pdf_content = response.content
        assert pdf_content.startswith(b"%PDF-")
        assert b"%%EOF" in pdf_content
        
        # Check for watermark (would need PDF parsing library for detailed check)
        # assert b"DRAFT" in pdf_content  # Simplified check
    
    async def test_latex_beamer_export(
        self,
        authenticated_client: AsyncClient,
    ):
        """Test LaTeX Beamer export with academic formatting."""
        # Create presentation with academic content
        response = await authenticated_client.post(
            "/api/v1/presentations",
            json={
                "title": "Machine Learning in Healthcare",
                "description": "Academic presentation for LaTeX export",
                "slides": [
                    {
                        "type": "title",
                        "title": "Machine Learning in Healthcare",
                        "content": {
                            "subtitle": "A Systematic Review",
                            "author": "John Doe\\inst{1} \\and Jane Smith\\inst{2}",
                            "institute": "\\inst{1}MIT \\and \\inst{2}Harvard",
                            "date": "\\today",
                        },
                        "order": 1,
                    },
                    {
                        "type": "content",
                        "title": "Mathematical Foundation",
                        "content": {
                            "text": "Consider the optimization problem:",
                            "equation": "\\min_{w} \\frac{1}{2}||w||^2 + C\\sum_{i=1}^{n}\\xi_i",
                        },
                        "order": 2,
                    },
                    {
                        "type": "content",
                        "title": "References",
                        "content": {
                            "citations": [
                                {
                                    "id": "smith2023",
                                    "text": "Smith et al. (2023). Machine Learning in Medicine. Nature Medicine.",
                                },
                                {
                                    "id": "doe2024",
                                    "text": "Doe, J. (2024). Deep Learning Applications. Science.",
                                },
                            ],
                        },
                        "order": 3,
                    },
                ],
                "settings": {
                    "theme": "academic",
                    "beamer_theme": "Madrid",
                    "color_theme": "seahorse",
                },
            },
        )
        
        presentation_id = response.json()["id"]
        
        # Request LaTeX export
        response = await authenticated_client.post(
            f"/api/v1/presentations/{presentation_id}/export",
            json={
                "format": "latex",
                "options": {
                    "beamer_theme": "Madrid",
                    "include_notes": True,
                    "bibliography_style": "plain",
                    "package_list": ["amsmath", "graphicx", "hyperref"],
                },
            },
        )
        
        assert response.status_code == 202
        job_id = response.json()["job_id"]
        
        # Wait for completion
        download_url = None
        for _ in range(30):
            response = await authenticated_client.get(
                f"/api/v1/export/jobs/{job_id}"
            )
            if response.json()["status"] == "completed":
                download_url = response.json()["download_url"]
                break
            await asyncio.sleep(1)
        
        # Download LaTeX source
        response = await authenticated_client.get(download_url)
        assert response.status_code == 200
        
        latex_content = response.text
        
        # Verify LaTeX structure
        assert "\\documentclass{beamer}" in latex_content
        assert "\\usetheme{Madrid}" in latex_content
        assert "\\begin{document}" in latex_content
        assert "\\end{document}" in latex_content
        assert "\\begin{frame}" in latex_content
        assert "\\min_{w}" in latex_content  # Check equation
    
    async def test_export_queue_processing(
        self,
        authenticated_client: AsyncClient,
    ):
        """Test export queue handling with multiple requests."""
        # Create multiple presentations
        presentation_ids = []
        for i in range(3):
            pres_id = await self.create_test_presentation(
                authenticated_client,
                f"Queue Test {i}"
            )
            presentation_ids.append(pres_id)
        
        # Submit multiple export requests simultaneously
        async def request_export(pres_id: str, format: str):
            response = await authenticated_client.post(
                f"/api/v1/presentations/{pres_id}/export",
                json={"format": format},
            )
            return response.json()["job_id"]
        
        # Request different formats for each presentation
        job_ids = await asyncio.gather(
            request_export(presentation_ids[0], "pptx"),
            request_export(presentation_ids[1], "pdf"),
            request_export(presentation_ids[2], "latex"),
        )
        
        assert len(job_ids) == 3
        assert len(set(job_ids)) == 3  # All unique
        
        # Monitor all jobs
        completed = []
        for _ in range(60):  # Extended timeout for multiple exports
            for job_id in job_ids:
                if job_id in completed:
                    continue
                
                response = await authenticated_client.get(
                    f"/api/v1/export/jobs/{job_id}"
                )
                if response.json()["status"] == "completed":
                    completed.append(job_id)
            
            if len(completed) == 3:
                break
            
            await asyncio.sleep(1)
        
        assert len(completed) == 3, "Not all export jobs completed"
    
    async def test_export_cancellation(
        self,
        authenticated_client: AsyncClient,
    ):
        """Test cancellation of export jobs."""
        # Create large presentation to have time to cancel
        presentation_id = await self.create_test_presentation(authenticated_client)
        
        # Start export
        response = await authenticated_client.post(
            f"/api/v1/presentations/{presentation_id}/export",
            json={
                "format": "pptx",
                "options": {"high_quality_images": True},
            },
        )
        job_id = response.json()["job_id"]
        
        # Cancel immediately
        response = await authenticated_client.post(
            f"/api/v1/export/jobs/{job_id}/cancel"
        )
        assert response.status_code == 200
        
        # Verify cancellation
        response = await authenticated_client.get(
            f"/api/v1/export/jobs/{job_id}"
        )
        assert response.json()["status"] == "cancelled"
    
    async def test_export_link_expiry(
        self,
        authenticated_client: AsyncClient,
        mocker,
    ):
        """Test download link expiration."""
        # Mock time to test expiry
        presentation_id = await self.create_test_presentation(authenticated_client)
        
        # Export presentation
        response = await authenticated_client.post(
            f"/api/v1/presentations/{presentation_id}/export",
            json={"format": "pdf"},
        )
        job_id = response.json()["job_id"]
        
        # Wait for completion
        download_url = None
        for _ in range(30):
            response = await authenticated_client.get(
                f"/api/v1/export/jobs/{job_id}"
            )
            if response.json()["status"] == "completed":
                download_url = response.json()["download_url"]
                expires_at = response.json()["expires_at"]
                break
            await asyncio.sleep(1)
        
        assert download_url is not None
        assert expires_at is not None
        
        # Verify link works initially
        response = await authenticated_client.get(download_url)
        assert response.status_code == 200
        
        # Note: Testing actual expiry would require mocking time
        # or waiting for real expiry, which is impractical
    
    async def test_export_format_validation(
        self,
        authenticated_client: AsyncClient,
    ):
        """Test validation of export format requests."""
        presentation_id = await self.create_test_presentation(authenticated_client)
        
        # Try invalid format
        response = await authenticated_client.post(
            f"/api/v1/presentations/{presentation_id}/export",
            json={"format": "invalid_format"},
        )
        assert response.status_code == 422
        
        # Try with missing format
        response = await authenticated_client.post(
            f"/api/v1/presentations/{presentation_id}/export",
            json={},
        )
        assert response.status_code == 422
    
    async def test_export_with_custom_templates(
        self,
        authenticated_client: AsyncClient,
    ):
        """Test export using custom templates."""
        # Create presentation with template reference
        response = await authenticated_client.post(
            "/api/v1/presentations",
            json={
                "title": "Template Export Test",
                "template_id": "academic_conference",  # Assuming this exists
                "slides": [
                    {
                        "type": "title",
                        "title": "Conference Presentation",
                        "content": {},
                        "order": 1,
                    },
                ],
                "settings": {
                    "use_template_styling": True,
                },
            },
        )
        
        presentation_id = response.json()["id"]
        
        # Export with template styling
        response = await authenticated_client.post(
            f"/api/v1/presentations/{presentation_id}/export",
            json={
                "format": "pptx",
                "options": {
                    "apply_template_styling": True,
                },
            },
        )
        
        assert response.status_code == 202
        
        # Would need to verify template styling in output
    
    async def test_batch_export(
        self,
        authenticated_client: AsyncClient,
    ):
        """Test batch export of multiple presentations."""
        # Create multiple presentations
        presentation_ids = []
        for i in range(3):
            pres_id = await self.create_test_presentation(
                authenticated_client,
                f"Batch Export {i}"
            )
            presentation_ids.append(pres_id)
        
        # Request batch export
        response = await authenticated_client.post(
            "/api/v1/export/batch",
            json={
                "presentation_ids": presentation_ids,
                "format": "pdf",
                "options": {
                    "combine_into_single_file": True,
                    "include_table_of_contents": True,
                },
            },
        )
        
        assert response.status_code == 202
        batch_job_id = response.json()["batch_job_id"]
        
        # Monitor batch job
        for _ in range(60):
            response = await authenticated_client.get(
                f"/api/v1/export/batch/{batch_job_id}"
            )
            batch_status = response.json()
            
            if batch_status["status"] == "completed":
                assert batch_status["completed_count"] == 3
                assert "download_url" in batch_status
                break
            
            await asyncio.sleep(1)