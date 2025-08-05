"""User-related factories for testing."""

import factory
from factory import fuzzy
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
import random

from .base import BaseFactory, DictFactory, academic_fake, fake


class UserFactory(DictFactory):
    """Factory for creating user test data."""
    
    id = factory.Sequence(lambda n: f"user_{n}")
    email = factory.LazyAttribute(lambda o: BaseFactory.random_email())
    username = factory.LazyAttribute(lambda o: fake.user_name())
    full_name = factory.LazyAttribute(lambda o: fake.name())
    hashed_password = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"  # secret
    
    is_active = True
    is_verified = factory.LazyAttribute(lambda o: random.random() > 0.2)  # 80% verified
    is_admin = False
    is_premium = factory.LazyAttribute(lambda o: random.random() > 0.7)  # 30% premium
    
    created_at = factory.LazyAttribute(lambda o: BaseFactory.random_timestamp(365))
    updated_at = factory.LazyAttribute(lambda o: o.created_at)
    last_login = factory.LazyAttribute(
        lambda o: BaseFactory.random_timestamp(7) if o.is_active else None
    )
    
    email_verified_at = factory.LazyAttribute(
        lambda o: o.created_at + timedelta(hours=random.randint(1, 48)) if o.is_verified else None
    )
    
    # Academic profile
    institution = factory.LazyAttribute(lambda o: BaseFactory.random_university())
    department = factory.LazyAttribute(lambda o: BaseFactory.random_department())
    academic_title = factory.LazyAttribute(lambda o: BaseFactory.random_academic_title())
    research_interests = factory.LazyAttribute(lambda o: BaseFactory.random_research_keywords())
    
    # Subscription details
    subscription_type = factory.LazyAttribute(
        lambda o: random.choice(["premium", "enterprise", "academic"]) if o.is_premium else "free"
    )
    subscription_expires_at = factory.LazyAttribute(
        lambda o: BaseFactory.random_future_timestamp(365) if o.is_premium else None
    )
    
    # Usage limits
    monthly_generation_limit = factory.LazyAttribute(
        lambda o: {
            "free": 10,
            "premium": 100,
            "enterprise": 1000,
            "academic": 500
        }.get(o.subscription_type, 10)
    )
    monthly_generations_used = factory.LazyAttribute(
        lambda o: random.randint(0, o.monthly_generation_limit)
    )
    
    # API access
    api_key = factory.LazyAttribute(
        lambda o: f"sk_{BaseFactory.random_string(32)}" if o.is_premium else None
    )
    api_key_created_at = factory.LazyAttribute(
        lambda o: o.created_at if o.api_key else None
    )
    
    # OAuth connections
    oauth_providers = factory.LazyAttribute(
        lambda o: random.sample(["google", "microsoft", "github"], random.randint(0, 2))
    )
    
    # Preferences
    preferences = factory.LazyAttribute(lambda o: {
        "theme": random.choice(["light", "dark", "auto"]),
        "language": random.choice(["en", "es", "fr", "de", "ja"]),
        "default_template": random.choice(["academic", "business", "minimal"]),
        "auto_save": random.choice([True, False]),
        "email_notifications": random.choice([True, False]),
    })
    
    class Params:
        # Traits for different user types
        admin = factory.Trait(
            is_admin=True,
            is_verified=True,
            is_premium=True,
            subscription_type="enterprise",
        )
        
        student = factory.Trait(
            academic_title="PhD Candidate",
            subscription_type="academic",
            is_premium=True,
            monthly_generation_limit=200,
        )
        
        professor = factory.Trait(
            academic_title=factory.LazyAttribute(
                lambda o: random.choice(["Prof.", "Associate Prof.", "Assistant Prof."])
            ),
            subscription_type="academic",
            is_premium=True,
            is_verified=True,
        )
        
        free_user = factory.Trait(
            is_premium=False,
            subscription_type="free",
            api_key=None,
            monthly_generation_limit=10,
        )
        
        unverified = factory.Trait(
            is_verified=False,
            email_verified_at=None,
        )
        
        inactive = factory.Trait(
            is_active=False,
            last_login=None,
        )


class UserProfileFactory(DictFactory):
    """Factory for user profile data."""
    
    user_id = factory.Sequence(lambda n: f"user_{n}")
    
    # Academic information
    orcid_id = factory.LazyAttribute(
        lambda o: f"{random.randint(1000, 9999)}-{random.randint(1000, 9999)}-"
                   f"{random.randint(1000, 9999)}-{random.randint(1000, 9999)}"
    )
    google_scholar_id = factory.LazyAttribute(lambda o: BaseFactory.random_string(12))
    
    # Professional details
    bio = factory.LazyAttribute(lambda o: fake.paragraph(nb_sentences=3))
    website = factory.LazyAttribute(lambda o: fake.url())
    linkedin = factory.LazyAttribute(
        lambda o: f"https://linkedin.com/in/{fake.user_name()}"
    )
    twitter = factory.LazyAttribute(
        lambda o: f"https://twitter.com/{fake.user_name()}" if random.random() > 0.5 else None
    )
    
    # Academic metrics
    h_index = factory.LazyAttribute(lambda o: random.randint(0, 50))
    total_citations = factory.LazyAttribute(lambda o: random.randint(0, 5000))
    publications_count = factory.LazyAttribute(lambda o: random.randint(0, 100))
    
    # Presentation stats
    total_presentations = factory.LazyAttribute(lambda o: random.randint(0, 50))
    total_slides_created = factory.LazyAttribute(lambda o: o.total_presentations * random.randint(10, 30))
    favorite_templates = factory.LazyAttribute(
        lambda o: random.sample(["academic", "minimal", "modern", "classic"], random.randint(1, 3))
    )
    
    # Settings
    default_citation_style = factory.LazyAttribute(
        lambda o: random.choice(["APA", "MLA", "Chicago", "IEEE", "Harvard"])
    )
    default_slide_duration = factory.LazyAttribute(lambda o: random.randint(30, 120))
    preferred_aspect_ratio = factory.LazyAttribute(
        lambda o: random.choice(["16:9", "4:3", "16:10"])
    )
    
    # Privacy settings
    profile_visibility = factory.LazyAttribute(
        lambda o: random.choice(["public", "academic", "private"])
    )
    show_email = factory.LazyAttribute(lambda o: random.choice([True, False]))
    show_institution = True
    
    created_at = factory.LazyAttribute(lambda o: BaseFactory.random_timestamp(365))
    updated_at = factory.LazyAttribute(lambda o: o.created_at)


class AuthTokenFactory(DictFactory):
    """Factory for authentication tokens."""
    
    access_token = factory.LazyAttribute(
        lambda o: f"eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.{BaseFactory.random_string(100)}"
    )
    refresh_token = factory.LazyAttribute(
        lambda o: f"eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.{BaseFactory.random_string(100)}"
    )
    token_type = "bearer"
    expires_in = 3600
    refresh_expires_in = 86400
    
    user_id = factory.Sequence(lambda n: f"user_{n}")
    scopes = factory.LazyAttribute(
        lambda o: random.sample(
            ["read", "write", "admin", "presentations", "templates", "export"],
            random.randint(2, 4)
        )
    )
    
    created_at = factory.LazyFunction(datetime.now)
    expires_at = factory.LazyAttribute(
        lambda o: o.created_at + timedelta(seconds=o.expires_in)
    )


class APIKeyFactory(DictFactory):
    """Factory for API keys."""
    
    id = factory.Sequence(lambda n: f"apikey_{n}")
    user_id = factory.Sequence(lambda n: f"user_{n}")
    
    name = factory.LazyAttribute(
        lambda o: random.choice([
            "Production API Key",
            "Development Key",
            "CI/CD Pipeline",
            "Research Script",
            "Mobile App",
        ])
    )
    
    key_prefix = "sk_"
    key_suffix = factory.LazyAttribute(lambda o: BaseFactory.random_string(32))
    key = factory.LazyAttribute(lambda o: f"{o.key_prefix}{o.key_suffix}")
    key_hash = factory.LazyAttribute(lambda o: f"$2b$12${BaseFactory.random_string(53)}")
    
    permissions = factory.LazyAttribute(
        lambda o: random.sample([
            "presentations:read",
            "presentations:write",
            "templates:read",
            "slides:generate",
            "export:pdf",
            "export:pptx",
            "analytics:read",
        ], random.randint(3, 6))
    )
    
    rate_limit = factory.LazyAttribute(
        lambda o: random.choice([100, 500, 1000, 5000])
    )
    
    last_used_at = factory.LazyAttribute(
        lambda o: BaseFactory.random_timestamp(30) if random.random() > 0.3 else None
    )
    
    expires_at = factory.LazyAttribute(
        lambda o: BaseFactory.random_future_timestamp(365) if random.random() > 0.5 else None
    )
    
    is_active = True
    created_at = factory.LazyAttribute(lambda o: BaseFactory.random_timestamp(180))
    updated_at = factory.LazyAttribute(lambda o: o.created_at)