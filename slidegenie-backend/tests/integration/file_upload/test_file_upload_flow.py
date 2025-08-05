"""
Integration tests for file upload and processing.

Tests PDF, DOCX, and LaTeX file uploads with virus scanning,
processing, and storage verification.
"""
import asyncio
import io
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.presentation import PresentationRepository


@pytest.mark.integration
@pytest.mark.asyncio
class TestFileUploadFlow:
    """Test complete file upload and processing workflows."""
    
    async def test_pdf_upload_and_processing(
        self,
        authenticated_client: AsyncClient,
        sample_pdf_file: Path,
        mock_ai_responses,
        db_session: AsyncSession,
    ):
        """Test PDF file upload and presentation generation."""
        # Upload PDF file
        with open(sample_pdf_file, "rb") as f:
            files = {"file": ("test.pdf", f, "application/pdf")}
            response = await authenticated_client.post(
                "/api/v1/upload/pdf",
                files=files,
                data={
                    "title": "PDF Test Presentation",
                    "extract_images": "true",
                },
            )
        
        assert response.status_code == 202
        data = response.json()
        
        assert "job_id" in data
        assert "file_id" in data
        assert data["status"] == "processing"
        
        job_id = data["job_id"]
        
        # Wait for processing to complete
        max_attempts = 30
        for _ in range(max_attempts):
            response = await authenticated_client.get(
                f"/api/v1/generation/jobs/{job_id}"
            )
            job_data = response.json()
            
            if job_data["status"] == "completed":
                break
            elif job_data["status"] == "failed":
                pytest.fail(f"Processing failed: {job_data.get('error')}")
            
            await asyncio.sleep(1)
        else:
            pytest.fail("Processing did not complete within timeout")
        
        # Verify presentation was created
        presentation_id = job_data["presentation_id"]
        response = await authenticated_client.get(
            f"/api/v1/presentations/{presentation_id}"
        )
        
        assert response.status_code == 200
        presentation = response.json()
        assert presentation["title"] == "PDF Test Presentation"
        assert presentation["source_type"] == "pdf"
        assert presentation["source_file_id"] == data["file_id"]
    
    async def test_docx_upload_and_processing(
        self,
        authenticated_client: AsyncClient,
        sample_docx_file: Path,
        mock_ai_responses,
    ):
        """Test DOCX file upload and processing."""
        # Upload DOCX file
        with open(sample_docx_file, "rb") as f:
            files = {
                "file": (
                    "test.docx",
                    f,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            }
            response = await authenticated_client.post(
                "/api/v1/upload/docx",
                files=files,
                data={
                    "preserve_formatting": "true",
                    "extract_media": "true",
                },
            )
        
        assert response.status_code == 202
        data = response.json()
        
        job_id = data["job_id"]
        
        # Monitor processing progress
        progress_updates = []
        for _ in range(30):
            response = await authenticated_client.get(
                f"/api/v1/generation/jobs/{job_id}"
            )
            job_data = response.json()
            
            if "progress" in job_data:
                progress_updates.append(job_data["progress"])
            
            if job_data["status"] == "completed":
                break
            
            await asyncio.sleep(0.5)
        
        # Verify content extraction
        presentation_id = job_data["presentation_id"]
        response = await authenticated_client.get(
            f"/api/v1/presentations/{presentation_id}"
        )
        
        presentation = response.json()
        
        # Check that headings were converted to slides
        slide_titles = [s["title"] for s in presentation["slides"]]
        assert "Introduction" in slide_titles
        assert "Methods" in slide_titles
        assert "Results" in slide_titles
        assert "Conclusion" in slide_titles
    
    async def test_latex_upload_and_compilation(
        self,
        authenticated_client: AsyncClient,
        sample_latex_file: Path,
        mock_ai_responses,
    ):
        """Test LaTeX file upload and processing."""
        # Upload LaTeX file
        with open(sample_latex_file, "rb") as f:
            files = {"file": ("test.tex", f, "text/x-tex")}
            response = await authenticated_client.post(
                "/api/v1/upload/latex",
                files=files,
                data={
                    "compile_pdf": "true",
                    "preserve_equations": "true",
                },
            )
        
        assert response.status_code == 202
        data = response.json()
        
        job_id = data["job_id"]
        
        # Wait for compilation and processing
        for _ in range(40):  # LaTeX compilation might take longer
            response = await authenticated_client.get(
                f"/api/v1/generation/jobs/{job_id}"
            )
            job_data = response.json()
            
            if job_data["status"] == "completed":
                break
            
            await asyncio.sleep(1)
        
        # Verify LaTeX specific features
        presentation_id = job_data["presentation_id"]
        response = await authenticated_client.get(
            f"/api/v1/presentations/{presentation_id}"
        )
        
        presentation = response.json()
        
        # Check for equation preservation
        has_equation = any(
            "equation" in str(slide.get("content", {}))
            for slide in presentation["slides"]
        )
        assert has_equation
        
        # Check for beamer theme detection
        assert presentation.get("detected_theme") == "Madrid"
    
    async def test_large_file_handling(
        self,
        authenticated_client: AsyncClient,
        large_file: Path,
    ):
        """Test handling of large file uploads."""
        # Try to upload file exceeding size limit
        with open(large_file, "rb") as f:
            files = {"file": ("large.pdf", f, "application/pdf")}
            response = await authenticated_client.post(
                "/api/v1/upload/pdf",
                files=files,
            )
        
        assert response.status_code == 413
        error = response.json()
        assert "size" in error["detail"].lower()
    
    async def test_virus_scanning_integration(
        self,
        authenticated_client: AsyncClient,
        malicious_file: Path,
    ):
        """Test virus scanning during file upload."""
        # Upload file with virus signature
        with open(malicious_file, "rb") as f:
            files = {"file": ("malicious.pdf", f, "application/pdf")}
            response = await authenticated_client.post(
                "/api/v1/upload/pdf",
                files=files,
            )
        
        assert response.status_code == 400
        error = response.json()
        assert "virus" in error["detail"].lower() or "malicious" in error["detail"].lower()
    
    async def test_concurrent_file_uploads(
        self,
        authenticated_client: AsyncClient,
        sample_pdf_file: Path,
        sample_docx_file: Path,
        sample_latex_file: Path,
        mock_ai_responses,
    ):
        """Test handling multiple concurrent file uploads."""
        
        async def upload_file(file_path: Path, endpoint: str, content_type: str):
            with open(file_path, "rb") as f:
                files = {"file": (file_path.name, f, content_type)}
                response = await authenticated_client.post(
                    f"/api/v1/upload/{endpoint}",
                    files=files,
                )
            return response.json()
        
        # Upload all files concurrently
        results = await asyncio.gather(
            upload_file(sample_pdf_file, "pdf", "application/pdf"),
            upload_file(sample_docx_file, "docx", 
                       "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            upload_file(sample_latex_file, "latex", "text/x-tex"),
        )
        
        # All should be accepted
        assert all(r["status"] == "processing" for r in results)
        assert len(set(r["job_id"] for r in results)) == 3  # All unique job IDs
    
    async def test_file_metadata_extraction(
        self,
        authenticated_client: AsyncClient,
        sample_pdf_file: Path,
    ):
        """Test extraction of file metadata."""
        # Create PDF with metadata
        import PyPDF2
        
        # Read original PDF
        with open(sample_pdf_file, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            writer = PyPDF2.PdfWriter()
            
            # Copy pages
            for page in reader.pages:
                writer.add_page(page)
            
            # Add metadata
            writer.add_metadata({
                "/Title": "Test PDF with Metadata",
                "/Author": "Test Author",
                "/Subject": "Integration Testing",
                "/Keywords": "test, pdf, metadata",
            })
            
            # Write to temporary file
            metadata_pdf = sample_pdf_file.parent / "metadata_test.pdf"
            with open(metadata_pdf, "wb") as out:
                writer.write(out)
        
        # Upload PDF with metadata
        with open(metadata_pdf, "rb") as f:
            files = {"file": ("metadata.pdf", f, "application/pdf")}
            response = await authenticated_client.post(
                "/api/v1/upload/pdf",
                files=files,
                data={"extract_metadata": "true"},
            )
        
        assert response.status_code == 202
        data = response.json()
        
        # Check extracted metadata
        assert "metadata" in data
        metadata = data["metadata"]
        assert metadata.get("title") == "Test PDF with Metadata"
        assert metadata.get("author") == "Test Author"
        assert metadata.get("subject") == "Integration Testing"
    
    async def test_upload_progress_tracking(
        self,
        authenticated_client: AsyncClient,
        temp_upload_dir: Path,
    ):
        """Test file upload progress tracking for large files."""
        # Create a moderately large file (5MB)
        large_file = temp_upload_dir / "progress_test.pdf"
        size = 5 * 1024 * 1024
        
        with open(large_file, "wb") as f:
            f.write(b"%PDF-1.4\n")
            f.write(b"0" * (size - 10))
            f.write(b"%%EOF")
        
        # Upload with progress tracking
        with open(large_file, "rb") as f:
            # Use streaming upload
            files = {"file": ("large.pdf", f, "application/pdf")}
            
            # Note: Real progress tracking would require WebSocket connection
            # or chunked upload with progress callbacks
            response = await authenticated_client.post(
                "/api/v1/upload/pdf",
                files=files,
                data={"track_progress": "true"},
            )
        
        assert response.status_code == 202
        data = response.json()
        assert "upload_id" in data or "job_id" in data
    
    async def test_invalid_file_type_rejection(
        self,
        authenticated_client: AsyncClient,
        temp_upload_dir: Path,
    ):
        """Test rejection of invalid file types."""
        # Create executable file
        exe_file = temp_upload_dir / "malicious.exe"
        exe_file.write_bytes(b"MZ\x90\x00\x03")  # PE header
        
        # Try to upload
        with open(exe_file, "rb") as f:
            files = {"file": ("bad.exe", f, "application/x-msdownload")}
            response = await authenticated_client.post(
                "/api/v1/upload/pdf",
                files=files,
            )
        
        assert response.status_code == 400
        error = response.json()
        assert "file type" in error["detail"].lower()
    
    async def test_file_sanitization(
        self,
        authenticated_client: AsyncClient,
        temp_upload_dir: Path,
    ):
        """Test file sanitization during upload."""
        # Create PDF with potentially malicious JavaScript
        malicious_pdf = temp_upload_dir / "javascript.pdf"
        pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R /OpenAction << /S /JavaScript /JS (app.alert('XSS')) >> >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
trailer
<< /Size 4 /Root 1 0 R >>
%%EOF"""
        
        malicious_pdf.write_bytes(pdf_content)
        
        # Upload PDF with JavaScript
        with open(malicious_pdf, "rb") as f:
            files = {"file": ("javascript.pdf", f, "application/pdf")}
            response = await authenticated_client.post(
                "/api/v1/upload/pdf",
                files=files,
                data={"sanitize": "true"},
            )
        
        # Should either sanitize or reject
        assert response.status_code in [202, 400]
        
        if response.status_code == 202:
            # File was sanitized
            data = response.json()
            assert data.get("sanitized") is True