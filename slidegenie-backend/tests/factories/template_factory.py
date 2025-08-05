"""Template factories for testing."""

import factory
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import random
import json

from .base import BaseFactory, DictFactory, fake, academic_fake


class TemplateCategoryFactory(DictFactory):
    """Factory for template category test data."""
    
    id = factory.Sequence(lambda n: f"cat_{n}")
    
    name = factory.LazyAttribute(
        lambda o: random.choice([
            "Academic", "Business", "Creative", "Minimal",
            "Conference", "Education", "Research", "Marketing"
        ])
    )
    
    slug = factory.LazyAttribute(lambda o: o.name.lower().replace(" ", "-"))
    
    description = factory.LazyAttribute(
        lambda o: f"Templates for {o.name.lower()} presentations"
    )
    
    icon = factory.LazyAttribute(lambda o: {
        "Academic": "graduation-cap",
        "Business": "briefcase",
        "Creative": "palette",
        "Minimal": "minus-circle",
        "Conference": "users",
        "Education": "book-open",
        "Research": "microscope",
        "Marketing": "trending-up",
    }.get(o.name, "folder"))
    
    color = factory.LazyAttribute(lambda o: fake.hex_color())
    
    is_premium = factory.LazyAttribute(
        lambda o: o.name in ["Business", "Marketing"]
    )
    
    template_count = factory.LazyAttribute(lambda o: random.randint(5, 50))
    
    created_at = factory.LazyAttribute(lambda o: BaseFactory.random_timestamp(365))
    updated_at = factory.LazyAttribute(lambda o: o.created_at)


class TemplateFactory(DictFactory):
    """Factory for creating template test data."""
    
    id = factory.Sequence(lambda n: f"template_{n}")
    
    name = factory.LazyAttribute(lambda o: _generate_template_name(o.category))
    
    category = factory.LazyAttribute(
        lambda o: random.choice([
            "Academic", "Business", "Creative", "Minimal",
            "Conference", "Education", "Research"
        ])
    )
    
    category_id = factory.LazyAttribute(lambda o: f"cat_{random.randint(1, 8)}")
    
    description = factory.LazyAttribute(
        lambda o: f"A {o.style} template for {o.category.lower()} presentations"
    )
    
    # Visual style
    style = factory.LazyAttribute(
        lambda o: random.choice([
            "modern", "classic", "minimalist", "bold",
            "elegant", "playful", "professional", "academic"
        ])
    )
    
    color_scheme = factory.LazyAttribute(lambda o: {
        "primary": fake.hex_color(),
        "secondary": fake.hex_color(),
        "accent": fake.hex_color(),
        "background": "#FFFFFF" if o.style in ["minimalist", "classic"] else fake.hex_color(),
        "text": "#000000" if o.style in ["minimalist", "classic"] else "#FFFFFF",
        "success": "#28a745",
        "warning": "#ffc107",
        "error": "#dc3545",
    })
    
    # Typography
    fonts = factory.LazyAttribute(lambda o: {
        "heading": random.choice([
            "Montserrat", "Roboto", "Open Sans", "Lato",
            "Playfair Display", "Merriweather", "Ubuntu"
        ]),
        "body": random.choice([
            "Open Sans", "Roboto", "Lato", "Source Sans Pro",
            "Noto Sans", "Arial", "Helvetica"
        ]),
        "code": "Source Code Pro",
        "math": "Computer Modern",
    })
    
    font_sizes = factory.LazyAttribute(lambda o: {
        "title": random.randint(36, 48),
        "heading": random.randint(28, 36),
        "subheading": random.randint(20, 28),
        "body": random.randint(14, 18),
        "caption": random.randint(12, 14),
    })
    
    # Layout configurations
    layouts = factory.LazyAttribute(lambda o: _generate_template_layouts(o.category))
    
    # Slide transitions
    transitions = factory.LazyAttribute(lambda o: {
        "default": random.choice(["fade", "slide", "zoom", "none"]),
        "speed": random.choice(["fast", "medium", "slow"]),
        "between_sections": random.choice(["fade-through-black", "slide", "zoom-out-in"]),
    })
    
    # Components styling
    components = factory.LazyAttribute(lambda o: {
        "bullet_style": random.choice(["disc", "circle", "square", "arrow"]),
        "list_spacing": random.choice(["compact", "normal", "relaxed"]),
        "image_style": random.choice(["rounded", "square", "circle", "shadow"]),
        "chart_style": random.choice(["modern", "classic", "minimal"]),
        "table_style": random.choice(["striped", "bordered", "minimal", "modern"]),
        "code_theme": random.choice(["monokai", "github", "solarized", "dracula"]),
    })
    
    # Academic features
    academic_features = factory.LazyAttribute(
        lambda o: {
            "citation_style": random.choice(["APA", "MLA", "Chicago", "IEEE"]),
            "bibliography_position": random.choice(["end", "per_slide", "footnotes"]),
            "equation_numbering": random.choice([True, False]),
            "figure_captions": True,
            "table_captions": True,
            "section_numbering": o.category == "Academic",
        } if o.category in ["Academic", "Research", "Education"] else None
    )
    
    # Metadata
    tags = factory.LazyAttribute(lambda o: _generate_template_tags(o.category, o.style))
    
    preview_url = factory.LazyAttribute(
        lambda o: f"https://previews.slidegenie.io/templates/{o.id}/preview.png"
    )
    
    thumbnail_url = factory.LazyAttribute(
        lambda o: f"https://previews.slidegenie.io/templates/{o.id}/thumb.png"
    )
    
    # Usage statistics
    usage_count = factory.LazyAttribute(lambda o: random.randint(0, 10000))
    
    rating = factory.LazyAttribute(
        lambda o: round(random.uniform(3.5, 5.0), 1) if o.usage_count > 100 else None
    )
    
    rating_count = factory.LazyAttribute(
        lambda o: random.randint(10, o.usage_count // 10) if o.rating else 0
    )
    
    # Availability
    is_premium = factory.LazyAttribute(
        lambda o: o.category in ["Business", "Marketing"] or o.style in ["bold", "elegant"]
    )
    
    is_featured = factory.LazyAttribute(lambda o: o.rating and o.rating >= 4.5)
    
    is_new = factory.LazyAttribute(lambda o: random.random() > 0.8)
    
    # Customization options
    customizable_elements = factory.LazyAttribute(lambda o: [
        "colors", "fonts", "spacing", "transitions",
        "bullet_styles", "header_footer", "background"
    ])
    
    # Default content
    sample_slides = factory.LazyAttribute(
        lambda o: _generate_sample_slides(o.category, o.layouts)
    )
    
    # Version info
    version = factory.LazyAttribute(lambda o: f"{random.randint(1, 3)}.{random.randint(0, 9)}")
    
    created_by = factory.LazyAttribute(
        lambda o: random.choice([
            "SlideGenie Team",
            "Community",
            fake.name(),
            fake.company(),
        ])
    )
    
    created_at = factory.LazyAttribute(lambda o: BaseFactory.random_timestamp(365))
    updated_at = factory.LazyAttribute(
        lambda o: BaseFactory.random_timestamp(30) if random.random() > 0.5 else o.created_at
    )
    
    # Compatibility
    compatibility = factory.LazyAttribute(lambda o: {
        "min_version": "1.0.0",
        "export_formats": ["pdf", "pptx", "beamer", "google_slides"],
        "features_required": ["basic"] if not o.is_premium else ["basic", "premium"],
    })
    
    class Params:
        academic_template = factory.Trait(
            category="Academic",
            style="academic",
            academic_features=factory.LazyAttribute(lambda o: {
                "citation_style": "APA",
                "bibliography_position": "end",
                "equation_numbering": True,
                "figure_captions": True,
                "table_captions": True,
                "section_numbering": True,
            }),
        )
        
        minimal_template = factory.Trait(
            category="Minimal",
            style="minimalist",
            color_scheme=factory.LazyAttribute(lambda o: {
                "primary": "#000000",
                "secondary": "#666666",
                "accent": "#0066CC",
                "background": "#FFFFFF",
                "text": "#000000",
                "success": "#28a745",
                "warning": "#ffc107",
                "error": "#dc3545",
            }),
        )
        
        conference_template = factory.Trait(
            category="Conference",
            academic_features=factory.LazyAttribute(lambda o: {
                "citation_style": "IEEE",
                "bibliography_position": "end",
                "equation_numbering": True,
                "figure_captions": True,
                "table_captions": True,
                "section_numbering": False,
            }),
        )


def _generate_template_name(category: str) -> str:
    """Generate template name based on category."""
    
    prefixes = {
        "Academic": ["Scholar", "Research", "Thesis", "Academic"],
        "Business": ["Corporate", "Professional", "Executive", "Business"],
        "Creative": ["Artistic", "Creative", "Design", "Innovative"],
        "Minimal": ["Clean", "Simple", "Minimal", "Essential"],
        "Conference": ["Conference", "Summit", "Symposium", "Meeting"],
        "Education": ["Classroom", "Lecture", "Teaching", "Educational"],
        "Research": ["Lab", "Scientific", "Research", "Discovery"],
        "Marketing": ["Marketing", "Sales", "Pitch", "Brand"],
    }
    
    suffixes = [
        "Pro", "Plus", "Elite", "Master",
        "Classic", "Modern", "2024", "Essential"
    ]
    
    prefix = random.choice(prefixes.get(category, ["Standard"]))
    suffix = random.choice(suffixes) if random.random() > 0.5 else ""
    
    return f"{prefix} {suffix}".strip()


def _generate_template_layouts(category: str) -> List[Dict[str, Any]]:
    """Generate layout configurations for template."""
    
    base_layouts = [
        {
            "name": "title",
            "display_name": "Title Slide",
            "structure": {
                "title": {"position": "center", "size": "large"},
                "subtitle": {"position": "center", "size": "medium"},
                "author": {"position": "bottom", "size": "small"},
            },
        },
        {
            "name": "content",
            "display_name": "Content Slide",
            "structure": {
                "title": {"position": "top", "size": "medium"},
                "content": {"position": "center", "size": "normal"},
            },
        },
        {
            "name": "two_column",
            "display_name": "Two Column",
            "structure": {
                "title": {"position": "top", "size": "medium"},
                "left_column": {"position": "left", "width": "50%"},
                "right_column": {"position": "right", "width": "50%"},
            },
        },
        {
            "name": "image_text",
            "display_name": "Image with Text",
            "structure": {
                "title": {"position": "top", "size": "medium"},
                "image": {"position": "left", "width": "60%"},
                "text": {"position": "right", "width": "40%"},
            },
        },
    ]
    
    if category in ["Academic", "Research", "Education"]:
        base_layouts.extend([
            {
                "name": "equation",
                "display_name": "Equation Slide",
                "structure": {
                    "title": {"position": "top", "size": "medium"},
                    "equation": {"position": "center", "size": "large"},
                    "explanation": {"position": "bottom", "size": "normal"},
                },
            },
            {
                "name": "references",
                "display_name": "References",
                "structure": {
                    "title": {"position": "top", "size": "medium"},
                    "references": {"position": "center", "columns": 2},
                },
            },
            {
                "name": "methodology",
                "display_name": "Methodology",
                "structure": {
                    "title": {"position": "top", "size": "medium"},
                    "diagram": {"position": "center", "size": "large"},
                    "steps": {"position": "bottom", "format": "numbered"},
                },
            },
        ])
    
    if category in ["Business", "Marketing"]:
        base_layouts.extend([
            {
                "name": "chart",
                "display_name": "Chart Slide",
                "structure": {
                    "title": {"position": "top", "size": "medium"},
                    "chart": {"position": "center", "size": "large"},
                    "insights": {"position": "bottom", "format": "bullets"},
                },
            },
            {
                "name": "timeline",
                "display_name": "Timeline",
                "structure": {
                    "title": {"position": "top", "size": "medium"},
                    "timeline": {"position": "center", "orientation": "horizontal"},
                },
            },
        ])
    
    return base_layouts


def _generate_template_tags(category: str, style: str) -> List[str]:
    """Generate tags for template."""
    
    tags = [category.lower(), style]
    
    category_tags = {
        "Academic": ["research", "thesis", "dissertation", "scholarly"],
        "Business": ["corporate", "professional", "presentation", "meeting"],
        "Creative": ["design", "artistic", "modern", "innovative"],
        "Minimal": ["clean", "simple", "minimalist", "elegant"],
        "Conference": ["conference", "symposium", "academic", "professional"],
        "Education": ["teaching", "classroom", "lecture", "educational"],
        "Research": ["scientific", "lab", "data", "analysis"],
        "Marketing": ["sales", "pitch", "brand", "promotion"],
    }
    
    tags.extend(random.sample(
        category_tags.get(category, ["general"]),
        random.randint(2, 3)
    ))
    
    if random.random() > 0.5:
        tags.extend(random.sample([
            "animated", "interactive", "responsive",
            "printable", "accessible", "multilingual"
        ], random.randint(1, 2)))
    
    return list(set(tags))


def _generate_sample_slides(category: str, layouts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate sample slides for template preview."""
    
    sample_slides = []
    
    # Title slide
    sample_slides.append({
        "layout": "title",
        "content": {
            "title": academic_fake.research_title() if category in ["Academic", "Research"] 
                    else fake.catch_phrase(),
            "subtitle": BaseFactory.random_conference() if category == "Conference"
                       else fake.company() if category == "Business"
                       else BaseFactory.random_university(),
            "author": fake.name(),
            "date": datetime.now().strftime("%B %Y"),
        },
    })
    
    # Content slides based on category
    if category in ["Academic", "Research", "Education"]:
        sample_slides.extend([
            {
                "layout": "content",
                "content": {
                    "title": "Introduction",
                    "text": academic_fake.abstract(3),
                },
            },
            {
                "layout": "equation",
                "content": {
                    "title": "Mathematical Framework",
                    "equation": academic_fake.equation(),
                    "explanation": fake.sentence(),
                },
            },
            {
                "layout": "two_column",
                "content": {
                    "title": "Results",
                    "left": ["Finding 1: " + fake.sentence() for _ in range(3)],
                    "right": ["Finding 2: " + fake.sentence() for _ in range(3)],
                },
            },
        ])
    
    elif category in ["Business", "Marketing"]:
        sample_slides.extend([
            {
                "layout": "content",
                "content": {
                    "title": "Executive Summary",
                    "bullets": [fake.sentence() for _ in range(4)],
                },
            },
            {
                "layout": "chart",
                "content": {
                    "title": "Market Analysis",
                    "chart_type": "bar",
                    "insights": ["Growth: +25% YoY", "Market share: 15%", "Target: 20% by Q4"],
                },
            },
            {
                "layout": "timeline",
                "content": {
                    "title": "Implementation Timeline",
                    "milestones": [
                        {"date": "Q1 2024", "event": "Project kickoff"},
                        {"date": "Q2 2024", "event": "Phase 1 completion"},
                        {"date": "Q3 2024", "event": "Beta launch"},
                        {"date": "Q4 2024", "event": "Full deployment"},
                    ],
                },
            },
        ])
    
    else:  # General templates
        sample_slides.extend([
            {
                "layout": "content",
                "content": {
                    "title": fake.sentence(nb_words=4)[:-1],
                    "text": fake.paragraph(nb_sentences=4),
                },
            },
            {
                "layout": "image_text",
                "content": {
                    "title": fake.sentence(nb_words=3)[:-1],
                    "image": "sample_image.jpg",
                    "text": fake.paragraph(nb_sentences=3),
                },
            },
        ])
    
    # Add conclusion slide
    sample_slides.append({
        "layout": "content",
        "content": {
            "title": "Conclusion" if category in ["Academic", "Research"] else "Thank You",
            "text": "Questions?" if category == "Conference" else fake.sentence(),
        },
    })
    
    return sample_slides