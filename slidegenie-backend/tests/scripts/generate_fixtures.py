#!/usr/bin/env python3
"""Generate test fixtures for SlideGenie."""

import json
import os
from pathlib import Path
from typing import Dict, Any, List
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.factories import (
    UserFactory,
    PresentationFactory,
    SlideFactory,
    ResearchPaperFactory,
    ThesisFactory,
    CitationFactory,
    TemplateFactory,
    FileFactory,
)


def ensure_directory(path: Path) -> None:
    """Ensure directory exists."""
    path.mkdir(parents=True, exist_ok=True)


def save_json_fixture(data: Any, filename: str, directory: Path) -> None:
    """Save data as JSON fixture."""
    ensure_directory(directory)
    filepath = directory / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"✓ Generated {filepath}")


def generate_user_fixtures() -> Dict[str, Any]:
    """Generate user fixtures."""
    fixtures = {
        "admin_user": UserFactory(admin=True),
        "professor": UserFactory(professor=True),
        "student": UserFactory(student=True),
        "free_user": UserFactory(free_user=True),
        "unverified_user": UserFactory(unverified=True),
        "premium_users": [UserFactory(is_premium=True) for _ in range(3)],
        "regular_users": [UserFactory() for _ in range(5)],
    }
    return fixtures


def generate_presentation_fixtures() -> Dict[str, Any]:
    """Generate presentation fixtures."""
    fixtures = {
        "conference_presentation": PresentationFactory(conference_presentation=True),
        "thesis_defense": PresentationFactory(thesis_defense=True),
        "lecture": PresentationFactory(lecture=True),
        "draft_presentation": PresentationFactory(draft=True),
        "published_presentations": [PresentationFactory(published=True) for _ in range(3)],
    }
    
    # Generate slides for each presentation
    for key, presentation in fixtures.items():
        if isinstance(presentation, dict):
            presentation["slides"] = [
                SlideFactory(
                    presentation_id=presentation["id"],
                    slide_number=i+1
                )
                for i in range(presentation.get("slide_count", 10))
            ]
    
    return fixtures


def generate_academic_fixtures() -> Dict[str, Any]:
    """Generate academic content fixtures."""
    fixtures = {
        "research_papers": [ResearchPaperFactory() for _ in range(5)],
        "thesis_examples": {
            "phd": ThesisFactory(thesis_type="phd"),
            "masters": ThesisFactory(thesis_type="masters"),
            "undergraduate": ThesisFactory(thesis_type="undergraduate"),
        },
        "citations": {
            "recent": [CitationFactory(recent=True) for _ in range(10)],
            "highly_cited": [CitationFactory(highly_cited=True) for _ in range(5)],
            "general": [CitationFactory() for _ in range(20)],
        },
    }
    return fixtures


def generate_template_fixtures() -> Dict[str, Any]:
    """Generate template fixtures."""
    categories = ["Academic", "Business", "Conference", "Minimal"]
    
    fixtures = {
        "templates_by_category": {
            category: [
                TemplateFactory(category=category)
                for _ in range(5)
            ]
            for category in categories
        },
        "featured_templates": [
            TemplateFactory(is_featured=True)
            for _ in range(3)
        ],
        "academic_template": TemplateFactory(academic_template=True),
        "minimal_template": TemplateFactory(minimal_template=True),
        "conference_template": TemplateFactory(conference_template=True),
    }
    return fixtures


def generate_file_fixtures() -> Dict[str, Any]:
    """Generate file upload fixtures."""
    fixtures = {
        "pdf_files": [
            FileFactory(pdf_research_paper=True)
            for _ in range(3)
        ],
        "docx_files": [
            FileFactory(docx_thesis=True)
            for _ in range(2)
        ],
        "various_files": [
            FileFactory(file_type=file_type)
            for file_type in ["pdf", "docx", "pptx", "tex", "txt"]
        ],
        "infected_file": FileFactory(infected_file=True),
    }
    return fixtures


def generate_sample_files() -> None:
    """Generate actual sample files for testing."""
    files_dir = Path(__file__).parent.parent / "fixtures" / "files"
    ensure_directory(files_dir / "uploads")
    ensure_directory(files_dir / "academic")
    
    # Sample PDF content (minimal PDF)
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Arial >> >> >> /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT /F1 12 Tf 100 700 Td (Sample PDF) Tj ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000297 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
391
%%EOF"""
    
    with open(files_dir / "uploads" / "sample.pdf", "wb") as f:
        f.write(pdf_content)
    
    # Sample text files
    sample_texts = {
        "research_abstract.txt": """Deep Learning Approaches for Natural Language Understanding in Academic Contexts

This paper presents a comprehensive study of deep learning techniques applied to natural language processing tasks in academic environments. We introduce a novel architecture that combines transformer-based models with domain-specific knowledge graphs to improve understanding of scientific literature.

Keywords: deep learning, NLP, transformers, knowledge graphs, academic AI""",
        
        "latex_sample.tex": r"""\documentclass{article}
\usepackage{amsmath}
\title{Sample LaTeX Document}
\author{Test Author}
\date{\today}

\begin{document}
\maketitle

\section{Introduction}
This is a sample LaTeX document for testing purposes.

\section{Mathematical Content}
Here's an equation:
\begin{equation}
    E = mc^2
\end{equation}

\end{document}""",
        
        "bibliography.bib": """@article{smith2023deep,
  title={Deep Learning Approaches for Natural Language Understanding},
  author={Smith, John and Doe, Jane},
  journal={Nature Machine Intelligence},
  volume={5},
  number={3},
  pages={234--245},
  year={2023}
}

@inproceedings{johnson2024transformers,
  title={Transformers in Academic Text Processing},
  author={Johnson, Alice and Brown, Bob},
  booktitle={Proceedings of ICML 2024},
  pages={1234--1245},
  year={2024}
}""",
    }
    
    for filename, content in sample_texts.items():
        with open(files_dir / "academic" / filename, "w", encoding="utf-8") as f:
            f.write(content)
    
    print(f"✓ Generated sample files in {files_dir}")


def main():
    """Generate all fixtures."""
    print("🎲 Generating test fixtures for SlideGenie...")
    
    fixtures_dir = Path(__file__).parent.parent / "fixtures"
    
    # Generate JSON fixtures
    fixtures_data = {
        "users": generate_user_fixtures(),
        "presentations": generate_presentation_fixtures(),
        "academic": generate_academic_fixtures(),
        "templates": generate_template_fixtures(),
        "files": generate_file_fixtures(),
    }
    
    # Save each category separately
    for category, data in fixtures_data.items():
        save_json_fixture(data, f"{category}.json", fixtures_dir)
    
    # Save combined fixtures
    save_json_fixture(fixtures_data, "all_fixtures.json", fixtures_dir)
    
    # Generate sample files
    generate_sample_files()
    
    # Generate database seed data
    seed_data = {
        "users": fixtures_data["users"]["regular_users"][:3],
        "templates": fixtures_data["templates"]["templates_by_category"]["Academic"][:3],
        "presentations": fixtures_data["presentations"]["published_presentations"][:2],
    }
    save_json_fixture(seed_data, "seed_data.json", fixtures_dir)
    
    print("\n✅ All fixtures generated successfully!")
    print(f"📁 Fixtures saved to: {fixtures_dir}")


if __name__ == "__main__":
    main()