#!/usr/bin/env python3
"""Seed test database with sample data."""

import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Any
import json
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.infrastructure.database.models import (
    User,
    UserProfile,
    Presentation,
    Slide,
    Template,
    TemplateCategory,
    GenerationJob,
    APIKey,
)
from app.infrastructure.database.base import Base
from app.core.security import get_password_hash


class TestDataSeeder:
    """Seed test database with sample data."""
    
    def __init__(self, database_url: str):
        self.engine = create_async_engine(database_url, echo=False)
        self.async_session = async_sessionmaker(self.engine, expire_on_commit=False)
        self.created_data = {
            "users": [],
            "presentations": [],
            "templates": [],
        }
    
    async def setup_database(self):
        """Create all tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def load_fixtures(self) -> Dict[str, Any]:
        """Load fixture data."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        
        with open(fixtures_dir / "seed_data.json", "r") as f:
            return json.load(f)
    
    async def seed_users(self, session: AsyncSession, users_data: List[Dict]) -> List[User]:
        """Seed user data."""
        users = []
        
        for user_data in users_data:
            # Create user
            user = User(
                email=user_data["email"],
                username=user_data["username"],
                full_name=user_data["full_name"],
                hashed_password=get_password_hash("testpass123"),
                is_active=user_data.get("is_active", True),
                is_verified=user_data.get("is_verified", True),
                is_admin=user_data.get("is_admin", False),
                is_premium=user_data.get("is_premium", False),
                created_at=datetime.now(timezone.utc),
            )
            session.add(user)
            await session.flush()
            
            # Create user profile
            profile = UserProfile(
                user_id=user.id,
                institution=user_data.get("institution"),
                department=user_data.get("department"),
                academic_title=user_data.get("academic_title"),
                bio="Test user profile",
                created_at=datetime.now(timezone.utc),
            )
            session.add(profile)
            
            # Create API key for premium users
            if user.is_premium:
                api_key = APIKey(
                    user_id=user.id,
                    name="Test API Key",
                    key_prefix="sk_test_",
                    key_hash=get_password_hash(f"test_key_{user.id}"),
                    permissions=["read", "write"],
                    created_at=datetime.now(timezone.utc),
                )
                session.add(api_key)
            
            users.append(user)
        
        await session.commit()
        return users
    
    async def seed_templates(self, session: AsyncSession, templates_data: List[Dict]) -> List[Template]:
        """Seed template data."""
        templates = []
        
        # Create categories first
        categories = {
            "Academic": TemplateCategory(
                name="Academic",
                slug="academic",
                description="Academic presentation templates",
                icon="graduation-cap",
            ),
            "Business": TemplateCategory(
                name="Business",
                slug="business",
                description="Business presentation templates",
                icon="briefcase",
            ),
            "Conference": TemplateCategory(
                name="Conference",
                slug="conference",
                description="Conference presentation templates",
                icon="users",
            ),
        }
        
        for category in categories.values():
            session.add(category)
        await session.flush()
        
        # Create templates
        for template_data in templates_data:
            category_name = template_data.get("category", "Academic")
            category = categories.get(category_name)
            
            template = Template(
                name=template_data["name"],
                category_id=category.id if category else None,
                description=template_data.get("description", "Test template"),
                style=template_data.get("style", "modern"),
                color_scheme=json.dumps(template_data.get("color_scheme", {})),
                fonts=json.dumps(template_data.get("fonts", {})),
                layouts=json.dumps(template_data.get("layouts", [])),
                is_premium=template_data.get("is_premium", False),
                usage_count=template_data.get("usage_count", 0),
                created_at=datetime.now(timezone.utc),
            )
            session.add(template)
            templates.append(template)
        
        await session.commit()
        return templates
    
    async def seed_presentations(
        self,
        session: AsyncSession,
        presentations_data: List[Dict],
        users: List[User],
        templates: List[Template]
    ) -> List[Presentation]:
        """Seed presentation data."""
        presentations = []
        
        for i, pres_data in enumerate(presentations_data):
            # Assign to users in round-robin fashion
            user = users[i % len(users)]
            template = templates[i % len(templates)] if templates else None
            
            presentation = Presentation(
                user_id=user.id,
                title=pres_data["title"],
                description=pres_data.get("description", "Test presentation"),
                presentation_type=pres_data.get("presentation_type", "conference"),
                duration_minutes=pres_data.get("duration_minutes", 20),
                template_id=template.id if template else None,
                theme=pres_data.get("theme", "academic_blue"),
                status=pres_data.get("status", "draft"),
                is_public=pres_data.get("is_public", False),
                created_at=datetime.now(timezone.utc),
            )
            session.add(presentation)
            await session.flush()
            
            # Create slides
            slide_count = pres_data.get("slide_count", 10)
            for slide_num in range(1, slide_count + 1):
                slide_type = "title" if slide_num == 1 else "content"
                
                slide = Slide(
                    presentation_id=presentation.id,
                    slide_number=slide_num,
                    slide_type=slide_type,
                    title=f"Slide {slide_num}",
                    content=json.dumps({
                        "text": f"Content for slide {slide_num}",
                        "bullets": [f"Point {i}" for i in range(1, 4)],
                    }),
                    layout=json.dumps({"template": slide_type}),
                    duration_seconds=60,
                    created_at=datetime.now(timezone.utc),
                )
                session.add(slide)
            
            presentations.append(presentation)
        
        await session.commit()
        return presentations
    
    async def seed_generation_jobs(
        self,
        session: AsyncSession,
        users: List[User],
        presentations: List[Presentation]
    ):
        """Seed generation job data."""
        for i, user in enumerate(users[:3]):  # Create jobs for first 3 users
            job = GenerationJob(
                user_id=user.id,
                job_type="presentation_generation",
                config=json.dumps({
                    "template_id": "template_1",
                    "slide_count": 15,
                }),
                status="completed" if i == 0 else "processing" if i == 1 else "queued",
                progress=100 if i == 0 else 50 if i == 1 else 0,
                result=json.dumps({
                    "presentation_id": presentations[i].id if i < len(presentations) else None
                }) if i == 0 else None,
                created_at=datetime.now(timezone.utc),
            )
            session.add(job)
        
        await session.commit()
    
    async def verify_seeded_data(self, session: AsyncSession):
        """Verify seeded data."""
        # Count records
        user_count = await session.scalar(select(User).count())
        presentation_count = await session.scalar(select(Presentation).count())
        slide_count = await session.scalar(select(Slide).count())
        template_count = await session.scalar(select(Template).count())
        
        print(f"\n✅ Seeded data summary:")
        print(f"  - Users: {user_count}")
        print(f"  - Presentations: {presentation_count}")
        print(f"  - Slides: {slide_count}")
        print(f"  - Templates: {template_count}")
    
    async def run(self):
        """Run the seeding process."""
        print("🌱 Seeding test database...")
        
        # Load fixtures
        fixtures = await self.load_fixtures()
        
        async with self.async_session() as session:
            # Seed data in order
            users = await self.seed_users(session, fixtures.get("users", []))
            self.created_data["users"] = users
            
            templates = await self.seed_templates(session, fixtures.get("templates", []))
            self.created_data["templates"] = templates
            
            presentations = await self.seed_presentations(
                session,
                fixtures.get("presentations", []),
                users,
                templates
            )
            self.created_data["presentations"] = presentations
            
            # Seed additional data
            await self.seed_generation_jobs(session, users, presentations)
            
            # Verify
            await self.verify_seeded_data(session)
        
        print("\n✅ Test database seeded successfully!")
        
        # Save created data IDs for reference
        created_ids = {
            "user_ids": [u.id for u in self.created_data["users"]],
            "presentation_ids": [p.id for p in self.created_data["presentations"]],
            "template_ids": [t.id for t in self.created_data["templates"]],
        }
        
        with open(Path(__file__).parent.parent / "fixtures" / "seeded_ids.json", "w") as f:
            json.dump(created_ids, f, indent=2)


async def main():
    """Main entry point."""
    import os
    
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://slidegenie_test:testpass123@localhost:5433/slidegenie_test"
    )
    
    # Convert to async URL if needed
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
    
    seeder = TestDataSeeder(database_url)
    
    # Create tables and seed data
    await seeder.setup_database()
    await seeder.run()


if __name__ == "__main__":
    asyncio.run(main())