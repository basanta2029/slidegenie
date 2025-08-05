"""Presentation and slide factories for testing."""

import factory
from factory import fuzzy
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import random
import json

from .base import BaseFactory, DictFactory, academic_fake, fake
from .user_factory import UserFactory


class PresentationFactory(DictFactory):
    """Factory for creating presentation test data."""
    
    id = factory.Sequence(lambda n: f"pres_{n}")
    user_id = factory.LazyAttribute(lambda o: UserFactory().get("id"))
    
    title = factory.LazyAttribute(lambda o: academic_fake.research_title())
    description = factory.LazyAttribute(lambda o: academic_fake.abstract(3))
    
    # Presentation metadata
    presentation_type = factory.LazyAttribute(
        lambda o: random.choice([
            "conference", "thesis_defense", "lecture",
            "seminar", "workshop", "poster", "webinar"
        ])
    )
    
    duration_minutes = factory.LazyAttribute(
        lambda o: {
            "conference": random.randint(15, 30),
            "thesis_defense": random.randint(45, 90),
            "lecture": random.randint(45, 60),
            "seminar": random.randint(30, 60),
            "workshop": random.randint(90, 180),
            "poster": random.randint(5, 10),
            "webinar": random.randint(30, 60),
        }.get(o.presentation_type, 30)
    )
    
    slide_count = factory.LazyAttribute(
        lambda o: max(5, int(o.duration_minutes * random.uniform(0.8, 1.2)))
    )
    
    # Academic context
    conference_name = factory.LazyAttribute(
        lambda o: BaseFactory.random_conference() if o.presentation_type == "conference" else None
    )
    
    target_audience = factory.LazyAttribute(
        lambda o: random.choice([
            "researchers", "students", "general_academic",
            "industry", "mixed", "specialists"
        ])
    )
    
    academic_level = factory.LazyAttribute(
        lambda o: random.choice([
            "undergraduate", "graduate", "phd",
            "postdoc", "faculty", "professional"
        ])
    )
    
    # Content metadata
    keywords = factory.LazyAttribute(lambda o: BaseFactory.random_research_keywords())
    references_count = factory.LazyAttribute(lambda o: random.randint(5, 50))
    
    # Template and styling
    template_id = factory.LazyAttribute(lambda o: f"template_{random.randint(1, 10)}")
    theme = factory.LazyAttribute(
        lambda o: random.choice([
            "academic_blue", "minimal_white", "dark_professional",
            "nature_inspired", "tech_modern", "classic_serif"
        ])
    )
    
    color_scheme = factory.LazyAttribute(lambda o: {
        "primary": fake.hex_color(),
        "secondary": fake.hex_color(),
        "accent": fake.hex_color(),
        "background": "#FFFFFF" if "white" in o.theme else "#1a1a1a",
        "text": "#000000" if "white" in o.theme else "#FFFFFF",
    })
    
    font_settings = factory.LazyAttribute(lambda o: {
        "heading": random.choice(["Arial", "Helvetica", "Times New Roman", "Calibri"]),
        "body": random.choice(["Arial", "Helvetica", "Georgia", "Verdana"]),
        "code": "Consolas",
        "math": "Computer Modern",
    })
    
    # Status and workflow
    status = factory.LazyAttribute(
        lambda o: random.choice([
            "draft", "in_progress", "ready_for_review",
            "finalized", "presented", "archived"
        ])
    )
    
    version = factory.LazyAttribute(lambda o: f"{random.randint(1, 3)}.{random.randint(0, 9)}")
    
    # Collaboration
    collaborators = factory.LazyAttribute(
        lambda o: [
            {
                "user_id": f"user_{random.randint(100, 200)}",
                "role": random.choice(["viewer", "editor", "reviewer"]),
                "added_at": BaseFactory.random_timestamp(30).isoformat(),
            }
            for _ in range(random.randint(0, 3))
        ]
    )
    
    is_public = factory.LazyAttribute(lambda o: random.random() > 0.7)
    share_token = factory.LazyAttribute(
        lambda o: BaseFactory.random_string(16) if o.is_public else None
    )
    
    # Generation details
    generation_method = factory.LazyAttribute(
        lambda o: random.choice(["ai_generated", "uploaded", "manual", "hybrid"])
    )
    
    ai_model_used = factory.LazyAttribute(
        lambda o: random.choice(["gpt-4", "claude-3", "custom"]) 
        if o.generation_method in ["ai_generated", "hybrid"] else None
    )
    
    source_document_id = factory.LazyAttribute(
        lambda o: f"doc_{random.randint(1, 100)}" 
        if o.generation_method in ["ai_generated", "uploaded"] else None
    )
    
    # Quality metrics
    quality_score = factory.LazyAttribute(lambda o: random.uniform(0.7, 1.0))
    readability_score = factory.LazyAttribute(lambda o: random.uniform(60, 90))
    coherence_score = factory.LazyAttribute(lambda o: random.uniform(0.6, 0.95))
    
    # Export history
    export_formats = factory.LazyAttribute(
        lambda o: random.sample(["pdf", "pptx", "beamer", "google_slides"], random.randint(0, 3))
    )
    
    last_exported_at = factory.LazyAttribute(
        lambda o: BaseFactory.random_timestamp(7) if o.export_formats else None
    )
    
    # Timestamps
    created_at = factory.LazyAttribute(lambda o: BaseFactory.random_timestamp(90))
    updated_at = factory.LazyAttribute(
        lambda o: BaseFactory.random_timestamp(7) if o.status != "draft" else o.created_at
    )
    presented_at = factory.LazyAttribute(
        lambda o: BaseFactory.random_timestamp(7) if o.status == "presented" else None
    )
    
    # Analytics
    view_count = factory.LazyAttribute(
        lambda o: random.randint(0, 1000) if o.is_public else random.randint(0, 50)
    )
    
    download_count = factory.LazyAttribute(
        lambda o: random.randint(0, o.view_count // 10) if o.view_count > 0 else 0
    )
    
    # Additional settings
    settings = factory.LazyAttribute(lambda o: {
        "auto_advance": False,
        "loop": False,
        "show_slide_numbers": True,
        "show_progress_bar": True,
        "enable_presenter_notes": True,
        "transition": random.choice(["fade", "slide", "none"]),
        "transition_speed": random.choice(["fast", "medium", "slow"]),
    })
    
    class Params:
        # Traits for different presentation types
        conference_presentation = factory.Trait(
            presentation_type="conference",
            duration_minutes=20,
            slide_count=factory.LazyAttribute(lambda o: random.randint(15, 25)),
            academic_level="phd",
            is_public=True,
        )
        
        thesis_defense = factory.Trait(
            presentation_type="thesis_defense",
            duration_minutes=60,
            slide_count=factory.LazyAttribute(lambda o: random.randint(40, 60)),
            academic_level="phd",
            references_count=factory.LazyAttribute(lambda o: random.randint(50, 150)),
        )
        
        lecture = factory.Trait(
            presentation_type="lecture",
            duration_minutes=50,
            slide_count=factory.LazyAttribute(lambda o: random.randint(30, 45)),
            target_audience="students",
        )
        
        draft = factory.Trait(
            status="draft",
            quality_score=factory.LazyAttribute(lambda o: random.uniform(0.3, 0.6)),
            view_count=0,
            download_count=0,
        )
        
        published = factory.Trait(
            status="finalized",
            is_public=True,
            quality_score=factory.LazyAttribute(lambda o: random.uniform(0.8, 1.0)),
        )


class SlideFactory(DictFactory):
    """Factory for creating slide test data."""
    
    id = factory.Sequence(lambda n: f"slide_{n}")
    presentation_id = factory.LazyAttribute(lambda o: f"pres_{random.randint(1, 100)}")
    
    slide_number = factory.Sequence(lambda n: n + 1)
    
    # Slide type based on position
    slide_type = factory.LazyAttribute(lambda o: {
        1: "title",
        2: "outline",
    }.get(o.slide_number, random.choice([
        "content", "bullet_points", "image_text",
        "comparison", "timeline", "conclusion", "references"
    ])))
    
    title = factory.LazyAttribute(lambda o: {
        "title": academic_fake.research_title(),
        "outline": "Outline",
        "content": fake.sentence(nb_words=6)[:-1],
        "bullet_points": fake.sentence(nb_words=5)[:-1],
        "image_text": fake.sentence(nb_words=4)[:-1],
        "comparison": f"{fake.word().title()} vs {fake.word().title()}",
        "timeline": "Research Timeline",
        "conclusion": "Conclusions",
        "references": "References",
    }.get(o.slide_type, fake.sentence(nb_words=5)[:-1]))
    
    # Content generation based on slide type
    content = factory.LazyAttribute(lambda o: _generate_slide_content(o.slide_type))
    
    # Speaker notes
    speaker_notes = factory.LazyAttribute(
        lambda o: fake.paragraph(nb_sentences=random.randint(2, 5))
        if random.random() > 0.3 else None
    )
    
    # Layout configuration
    layout = factory.LazyAttribute(lambda o: {
        "template": o.slide_type,
        "columns": random.randint(1, 2) if o.slide_type == "content" else 1,
        "content_blocks": _generate_layout_blocks(o.slide_type),
    })
    
    # Timing
    duration_seconds = factory.LazyAttribute(
        lambda o: {
            "title": 30,
            "outline": 45,
            "conclusion": 60,
            "references": 30,
        }.get(o.slide_type, random.randint(45, 90))
    )
    
    # Animations
    animations = factory.LazyAttribute(
        lambda o: [
            {
                "element": f"element_{i}",
                "type": random.choice(["fade_in", "slide_up", "zoom_in"]),
                "delay": i * 0.5,
                "duration": 0.5,
            }
            for i in range(random.randint(0, 3))
        ] if random.random() > 0.6 else []
    )
    
    # Media elements
    media = factory.LazyAttribute(lambda o: _generate_media_elements(o.slide_type))
    
    # Academic elements
    citations = factory.LazyAttribute(
        lambda o: [academic_fake.citation_text() for _ in range(random.randint(0, 3))]
        if o.slide_type not in ["title", "outline"] else []
    )
    
    equations = factory.LazyAttribute(
        lambda o: [academic_fake.equation() for _ in range(random.randint(0, 2))]
        if o.slide_type == "content" and random.random() > 0.7 else []
    )
    
    # Metadata
    keywords = factory.LazyAttribute(
        lambda o: random.sample(BaseFactory.random_research_keywords(), random.randint(2, 4))
    )
    
    # Quality metrics
    text_density = factory.LazyAttribute(lambda o: random.uniform(0.2, 0.8))
    visual_balance = factory.LazyAttribute(lambda o: random.uniform(0.6, 0.95))
    
    # Version tracking
    version = 1
    created_at = factory.LazyAttribute(lambda o: BaseFactory.random_timestamp(30))
    updated_at = factory.LazyAttribute(lambda o: o.created_at)
    
    # Collaboration
    last_edited_by = factory.LazyAttribute(lambda o: f"user_{random.randint(1, 10)}")
    
    class Params:
        title_slide = factory.Trait(
            slide_number=1,
            slide_type="title",
            duration_seconds=30,
        )
        
        content_slide = factory.Trait(
            slide_type="content",
            equations=factory.LazyAttribute(
                lambda o: [academic_fake.equation() for _ in range(random.randint(1, 3))]
            ),
        )
        
        references_slide = factory.Trait(
            slide_type="references",
            title="References",
            citations=factory.LazyAttribute(
                lambda o: [academic_fake.citation_text() for _ in range(random.randint(5, 15))]
            ),
        )


def _generate_slide_content(slide_type: str) -> Dict[str, Any]:
    """Generate content based on slide type."""
    
    if slide_type == "title":
        return {
            "main_title": academic_fake.research_title(),
            "subtitle": fake.company() + " " + BaseFactory.random_conference(),
            "authors": [fake.name() for _ in range(random.randint(1, 4))],
            "institution": BaseFactory.random_university(),
            "date": fake.date_this_year().isoformat(),
        }
    
    elif slide_type == "outline":
        num_sections = random.randint(4, 7)
        return {
            "sections": [
                {
                    "title": fake.sentence(nb_words=4)[:-1],
                    "subsections": [
                        fake.sentence(nb_words=3)[:-1] 
                        for _ in range(random.randint(0, 3))
                    ]
                }
                for _ in range(num_sections)
            ]
        }
    
    elif slide_type == "bullet_points":
        return {
            "points": [
                {
                    "text": fake.sentence(),
                    "level": random.randint(0, 2),
                    "bullet_style": random.choice(["disc", "circle", "square"]),
                }
                for _ in range(random.randint(3, 7))
            ]
        }
    
    elif slide_type == "comparison":
        return {
            "left": {
                "title": fake.word().title(),
                "points": [fake.sentence() for _ in range(random.randint(3, 5))],
            },
            "right": {
                "title": fake.word().title(),
                "points": [fake.sentence() for _ in range(random.randint(3, 5))],
            }
        }
    
    elif slide_type == "timeline":
        num_events = random.randint(4, 8)
        return {
            "events": [
                {
                    "date": fake.date_between(start_date="-5y", end_date="today").isoformat(),
                    "title": fake.sentence(nb_words=3)[:-1],
                    "description": fake.sentence(),
                }
                for _ in range(num_events)
            ]
        }
    
    elif slide_type == "references":
        return {
            "references": [
                {
                    "authors": [fake.name() for _ in range(random.randint(1, 4))],
                    "year": random.randint(2015, 2024),
                    "title": academic_fake.research_title(),
                    "journal": BaseFactory.random_journal(),
                    "volume": random.randint(1, 50),
                    "pages": f"{random.randint(1, 300)}-{random.randint(301, 400)}",
                }
                for _ in range(random.randint(5, 15))
            ]
        }
    
    else:  # content or other types
        return {
            "text": fake.paragraph(nb_sentences=random.randint(3, 6)),
            "highlights": [fake.word() for _ in range(random.randint(0, 3))],
        }


def _generate_layout_blocks(slide_type: str) -> List[Dict[str, Any]]:
    """Generate layout blocks for a slide."""
    
    if slide_type == "image_text":
        return [
            {
                "type": "text",
                "position": {"x": 0.1, "y": 0.1, "width": 0.4, "height": 0.8},
            },
            {
                "type": "image",
                "position": {"x": 0.5, "y": 0.1, "width": 0.4, "height": 0.8},
            }
        ]
    
    elif slide_type == "comparison":
        return [
            {
                "type": "text",
                "position": {"x": 0.05, "y": 0.2, "width": 0.4, "height": 0.7},
            },
            {
                "type": "divider",
                "position": {"x": 0.48, "y": 0.2, "width": 0.04, "height": 0.7},
            },
            {
                "type": "text",
                "position": {"x": 0.55, "y": 0.2, "width": 0.4, "height": 0.7},
            }
        ]
    
    else:
        return [
            {
                "type": "text",
                "position": {"x": 0.1, "y": 0.2, "width": 0.8, "height": 0.7},
            }
        ]


def _generate_media_elements(slide_type: str) -> List[Dict[str, Any]]:
    """Generate media elements for a slide."""
    
    media = []
    
    if slide_type == "image_text" or (slide_type == "content" and random.random() > 0.6):
        media.append({
            "type": "image",
            "url": f"https://placeholder.com/{random.randint(400, 800)}x{random.randint(300, 600)}",
            "alt_text": fake.sentence(),
            "caption": fake.sentence() if random.random() > 0.5 else None,
            "attribution": fake.name() if random.random() > 0.7 else None,
        })
    
    if slide_type == "content" and random.random() > 0.8:
        media.append({
            "type": "chart",
            "chart_type": random.choice(["bar", "line", "pie", "scatter"]),
            "data_url": f"data/chart_{BaseFactory.random_string(8)}.json",
            "title": fake.sentence(nb_words=4)[:-1],
        })
    
    if random.random() > 0.95:  # Rare video embeds
        media.append({
            "type": "video",
            "url": f"https://example.com/video_{BaseFactory.random_string(10)}.mp4",
            "thumbnail": f"https://placeholder.com/640x360",
            "duration": random.randint(30, 300),
        })
    
    return media