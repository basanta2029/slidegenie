"""File and document factories for testing."""

import factory
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Union
import random
import io
import base64
from pathlib import Path

from .base import BaseFactory, DictFactory, fake


class FileFactory(DictFactory):
    """Factory for creating file test data."""
    
    id = factory.Sequence(lambda n: f"file_{n}")
    
    filename = factory.LazyAttribute(lambda o: _generate_filename(o.file_type))
    
    file_type = factory.LazyAttribute(
        lambda o: random.choice([
            "pdf", "docx", "pptx", "tex", "txt", "md",
            "png", "jpg", "svg", "csv", "json"
        ])
    )
    
    mime_type = factory.LazyAttribute(lambda o: {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "tex": "text/x-latex",
        "txt": "text/plain",
        "md": "text/markdown",
        "png": "image/png",
        "jpg": "image/jpeg",
        "svg": "image/svg+xml",
        "csv": "text/csv",
        "json": "application/json",
    }[o.file_type])
    
    size_bytes = factory.LazyAttribute(lambda o: {
        "pdf": random.randint(100_000, 10_000_000),
        "docx": random.randint(50_000, 5_000_000),
        "pptx": random.randint(500_000, 20_000_000),
        "tex": random.randint(10_000, 500_000),
        "txt": random.randint(1_000, 100_000),
        "md": random.randint(1_000, 50_000),
        "png": random.randint(50_000, 2_000_000),
        "jpg": random.randint(30_000, 1_500_000),
        "svg": random.randint(1_000, 100_000),
        "csv": random.randint(1_000, 1_000_000),
        "json": random.randint(100, 100_000),
    }[o.file_type])
    
    # Storage information
    storage_path = factory.LazyAttribute(
        lambda o: f"uploads/{datetime.now().year}/{datetime.now().month:02d}/{o.id}/{o.filename}"
    )
    
    storage_backend = factory.LazyAttribute(
        lambda o: random.choice(["s3", "local", "gcs"])
    )
    
    bucket_name = factory.LazyAttribute(
        lambda o: "slidegenie-uploads" if o.storage_backend == "s3" else None
    )
    
    # File metadata
    content_hash = factory.LazyAttribute(
        lambda o: BaseFactory.random_string(64, "sha256:")
    )
    
    uploaded_by = factory.LazyAttribute(lambda o: f"user_{random.randint(1, 100)}")
    uploaded_at = factory.LazyAttribute(lambda o: BaseFactory.random_timestamp(30))
    
    # Processing status
    processing_status = factory.LazyAttribute(
        lambda o: random.choice([
            "pending", "processing", "completed", "failed", "quarantined"
        ])
    )
    
    processed_at = factory.LazyAttribute(
        lambda o: o.uploaded_at + timedelta(seconds=random.randint(1, 300))
        if o.processing_status in ["completed", "failed"] else None
    )
    
    # Security scan results
    virus_scan_status = factory.LazyAttribute(
        lambda o: random.choice(["clean", "infected", "suspicious", "pending"])
        if o.processing_status != "pending" else "pending"
    )
    
    virus_scan_details = factory.LazyAttribute(
        lambda o: {
            "scanner": "ClamAV",
            "version": "0.103.8",
            "scan_time": random.uniform(0.1, 5.0),
            "threats": [] if o.virus_scan_status == "clean" else [
                f"Threat.{BaseFactory.random_string(8)}"
            ],
        } if o.virus_scan_status != "pending" else None
    )
    
    # Content analysis
    content_type_detected = factory.LazyAttribute(
        lambda o: random.choice([
            "research_paper", "presentation", "thesis",
            "report", "article", "book_chapter", "unknown"
        ]) if o.file_type in ["pdf", "docx", "tex"] else None
    )
    
    language_detected = factory.LazyAttribute(
        lambda o: random.choice(["en", "es", "fr", "de", "ja", "zh"])
        if o.content_type_detected else None
    )
    
    page_count = factory.LazyAttribute(
        lambda o: random.randint(1, 300)
        if o.file_type in ["pdf", "docx"] else None
    )
    
    word_count = factory.LazyAttribute(
        lambda o: random.randint(100, 50000)
        if o.file_type in ["pdf", "docx", "tex", "txt", "md"] else None
    )
    
    # Extracted metadata
    extracted_metadata = factory.LazyAttribute(
        lambda o: _generate_extracted_metadata(o.file_type, o.content_type_detected)
    )
    
    # Access control
    is_public = factory.LazyAttribute(lambda o: random.random() > 0.8)
    
    access_permissions = factory.LazyAttribute(
        lambda o: {
            "owner": o.uploaded_by,
            "read": [f"user_{random.randint(101, 200)}" for _ in range(random.randint(0, 3))],
            "write": [],
        }
    )
    
    # Version control
    version = factory.LazyAttribute(lambda o: random.randint(1, 5))
    
    is_latest = factory.LazyAttribute(lambda o: random.random() > 0.7)
    
    previous_version_id = factory.LazyAttribute(
        lambda o: f"file_{random.randint(1, o.id.split('_')[1])}"
        if o.version > 1 else None
    )
    
    # Tags and categories
    tags = factory.LazyAttribute(
        lambda o: random.sample([
            "machine-learning", "research", "conference",
            "draft", "final", "review", "important",
            "archived", "template", "reference"
        ], random.randint(0, 4))
    )
    
    class Params:
        pdf_research_paper = factory.Trait(
            file_type="pdf",
            content_type_detected="research_paper",
            page_count=factory.LazyAttribute(lambda o: random.randint(8, 15)),
            processing_status="completed",
            virus_scan_status="clean",
        )
        
        docx_thesis = factory.Trait(
            file_type="docx",
            content_type_detected="thesis",
            page_count=factory.LazyAttribute(lambda o: random.randint(80, 200)),
            word_count=factory.LazyAttribute(lambda o: random.randint(20000, 80000)),
            processing_status="completed",
        )
        
        infected_file = factory.Trait(
            virus_scan_status="infected",
            processing_status="quarantined",
            is_public=False,
        )


class MockFileFactory(DictFactory):
    """Factory for creating mock file objects for testing."""
    
    filename = factory.LazyAttribute(lambda o: _generate_filename(o.content_type))
    
    content_type = factory.LazyAttribute(
        lambda o: random.choice(["pdf", "docx", "txt", "tex"])
    )
    
    content = factory.LazyAttribute(lambda o: _generate_mock_content(o.content_type))
    
    size = factory.LazyAttribute(lambda o: len(o.content))
    
    file = factory.LazyAttribute(
        lambda o: io.BytesIO(o.content.encode() if isinstance(o.content, str) else o.content)
    )
    
    headers = factory.LazyAttribute(lambda o: {
        "content-type": {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "txt": "text/plain",
            "tex": "text/x-latex",
        }[o.content_type],
        "content-length": str(o.size),
        "content-disposition": f"attachment; filename=\"{o.filename}\"",
    })
    
    class Params:
        large_file = factory.Trait(
            content=factory.LazyAttribute(
                lambda o: b"x" * (10 * 1024 * 1024)  # 10MB
            ),
        )
        
        malicious_filename = factory.Trait(
            filename="../../../etc/passwd",
        )


class DocumentMetadataFactory(DictFactory):
    """Factory for document metadata."""
    
    title = factory.LazyAttribute(lambda o: fake.sentence(nb_words=8)[:-1])
    
    authors = factory.LazyAttribute(
        lambda o: [fake.name() for _ in range(random.randint(1, 5))]
    )
    
    abstract = factory.LazyAttribute(lambda o: fake.text(max_nb_chars=500))
    
    keywords = factory.LazyAttribute(
        lambda o: [fake.word() for _ in range(random.randint(3, 8))]
    )
    
    publication_date = factory.LazyAttribute(
        lambda o: fake.date_between(start_date="-5y", end_date="today")
    )
    
    document_type = factory.LazyAttribute(
        lambda o: random.choice([
            "article", "report", "thesis", "presentation", "book", "manual"
        ])
    )
    
    language = factory.LazyAttribute(
        lambda o: random.choice(["en", "es", "fr", "de", "ja"])
    )
    
    doi = factory.LazyAttribute(
        lambda o: f"10.{random.randint(1000, 9999)}/{BaseFactory.random_string(10)}"
        if random.random() > 0.5 else None
    )
    
    citations_count = factory.LazyAttribute(lambda o: random.randint(0, 500))
    
    # Additional metadata
    publisher = factory.LazyAttribute(
        lambda o: random.choice([
            "IEEE", "ACM", "Springer", "Elsevier", "Nature", "Science"
        ]) if o.document_type == "article" else None
    )
    
    institution = factory.LazyAttribute(
        lambda o: BaseFactory.random_university()
        if o.document_type in ["thesis", "report"] else None
    )
    
    conference = factory.LazyAttribute(
        lambda o: BaseFactory.random_conference()
        if o.document_type == "presentation" else None
    )


def _generate_filename(file_type: str) -> str:
    """Generate a realistic filename based on file type."""
    
    base_names = {
        "pdf": [
            "research_paper", "thesis", "presentation",
            "report", "article", "manuscript"
        ],
        "docx": [
            "draft", "proposal", "thesis_chapter",
            "meeting_notes", "research_outline"
        ],
        "pptx": [
            "conference_presentation", "defense",
            "lecture", "seminar", "workshop"
        ],
        "tex": [
            "paper", "thesis", "article",
            "manuscript", "chapter"
        ],
        "txt": ["notes", "readme", "abstract", "data"],
        "md": ["README", "documentation", "notes", "guide"],
        "png": ["figure", "diagram", "plot", "chart"],
        "jpg": ["photo", "image", "picture", "scan"],
        "svg": ["diagram", "flowchart", "graph", "illustration"],
        "csv": ["data", "results", "measurements", "survey"],
        "json": ["config", "data", "metadata", "results"],
    }
    
    base = random.choice(base_names.get(file_type, ["file"]))
    timestamp = datetime.now().strftime("%Y%m%d")
    version = f"v{random.randint(1, 3)}" if random.random() > 0.5 else ""
    
    parts = [base, timestamp]
    if version:
        parts.append(version)
    
    return f"{'_'.join(parts)}.{file_type}"


def _generate_mock_content(content_type: str) -> Union[str, bytes]:
    """Generate mock file content based on type."""
    
    if content_type == "txt":
        return fake.text(max_nb_chars=1000)
    
    elif content_type == "tex":
        return f"""\\documentclass{{article}}
\\usepackage{{amsmath}}
\\title{{{fake.sentence(nb_words=6)[:-1]}}}
\\author{{{fake.name()}}}
\\date{{\\today}}

\\begin{{document}}
\\maketitle

\\begin{{abstract}}
{fake.text(max_nb_chars=300)}
\\end{{abstract}}

\\section{{Introduction}}
{fake.text(max_nb_chars=500)}

\\section{{Methodology}}
{fake.text(max_nb_chars=500)}

\\section{{Results}}
{fake.text(max_nb_chars=400)}

\\section{{Conclusion}}
{fake.text(max_nb_chars=300)}

\\end{{document}}"""
    
    elif content_type == "pdf":
        # Generate a minimal PDF header (not a valid PDF, but enough for testing)
        return b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n" + fake.text(max_nb_chars=1000).encode()
    
    elif content_type == "docx":
        # Generate a minimal DOCX header (not a valid DOCX, but enough for testing)
        return b"PK\x03\x04" + fake.text(max_nb_chars=1000).encode()
    
    else:
        return fake.text(max_nb_chars=500)


def _generate_extracted_metadata(file_type: str, content_type: Optional[str]) -> Dict[str, Any]:
    """Generate extracted metadata based on file type and content."""
    
    metadata = {
        "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
        "extraction_method": "automatic",
    }
    
    if file_type in ["pdf", "docx"] and content_type:
        metadata.update({
            "title": fake.sentence(nb_words=8)[:-1],
            "authors": [fake.name() for _ in range(random.randint(1, 4))],
            "creation_date": fake.date_time_between(start_date="-2y").isoformat(),
            "modification_date": fake.date_time_between(start_date="-1y").isoformat(),
            "subject": fake.sentence(nb_words=5)[:-1],
            "keywords": [fake.word() for _ in range(random.randint(3, 8))],
        })
        
        if content_type == "research_paper":
            metadata.update({
                "abstract": fake.text(max_nb_chars=300),
                "doi": f"10.{random.randint(1000, 9999)}/{BaseFactory.random_string(10)}",
                "references_count": random.randint(10, 50),
            })
        
        elif content_type == "thesis":
            metadata.update({
                "degree_type": random.choice(["PhD", "Masters", "Bachelors"]),
                "institution": BaseFactory.random_university(),
                "department": BaseFactory.random_department(),
                "advisor": fake.name(),
            })
    
    elif file_type in ["png", "jpg", "svg"]:
        metadata.update({
            "width": random.randint(100, 4000),
            "height": random.randint(100, 3000),
            "dpi": random.choice([72, 96, 150, 300]),
            "color_space": random.choice(["RGB", "CMYK", "Grayscale"]),
        })
    
    elif file_type == "csv":
        metadata.update({
            "rows": random.randint(10, 10000),
            "columns": random.randint(2, 50),
            "headers": [fake.word() for _ in range(random.randint(2, 10))],
            "delimiter": random.choice([",", ";", "\t"]),
        })
    
    return metadata


from datetime import timedelta