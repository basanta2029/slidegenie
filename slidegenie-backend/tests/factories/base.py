"""Base factory configuration for SlideGenie tests."""

import factory
from factory.alchemy import SQLAlchemyModelFactory
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import scoped_session, sessionmaker
from datetime import datetime, timezone
import random
import string
from typing import Any, Dict, Optional

# Mock session for now - will be replaced with actual DB session in tests
_session = None


class AsyncSQLAlchemyModelFactory(SQLAlchemyModelFactory):
    """Base factory for async SQLAlchemy models."""
    
    class Meta:
        abstract = True
        sqlalchemy_session_persistence = "commit"
    
    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Override create to handle async sessions."""
        # In test setup, inject the async session
        return super()._create(model_class, *args, **kwargs)


class BaseFactory(factory.Factory):
    """Base factory with common utilities."""
    
    class Meta:
        abstract = True
    
    @staticmethod
    def random_string(length: int = 10, prefix: str = "") -> str:
        """Generate a random string."""
        chars = string.ascii_lowercase + string.digits
        random_part = ''.join(random.choice(chars) for _ in range(length))
        return f"{prefix}{random_part}" if prefix else random_part
    
    @staticmethod
    def random_email(domain: str = "test.edu") -> str:
        """Generate a random academic email."""
        username = BaseFactory.random_string(8)
        return f"{username}@{domain}"
    
    @staticmethod
    def random_academic_title() -> str:
        """Generate a random academic title."""
        prefixes = ["Dr.", "Prof.", "Assistant Prof.", "Associate Prof.", "PhD Candidate"]
        return random.choice(prefixes)
    
    @staticmethod
    def random_department() -> str:
        """Generate a random academic department."""
        departments = [
            "Computer Science",
            "Physics",
            "Mathematics",
            "Biology",
            "Chemistry",
            "Engineering",
            "Medicine",
            "Psychology",
            "Economics",
            "Philosophy",
        ]
        return random.choice(departments)
    
    @staticmethod
    def random_university() -> str:
        """Generate a random university name."""
        universities = [
            "MIT",
            "Stanford University",
            "Harvard University",
            "Oxford University",
            "Cambridge University",
            "UC Berkeley",
            "Caltech",
            "ETH Zurich",
            "Imperial College London",
            "University of Tokyo",
        ]
        return random.choice(universities)
    
    @staticmethod
    def random_conference() -> str:
        """Generate a random academic conference."""
        conferences = [
            "International Conference on Machine Learning (ICML)",
            "Neural Information Processing Systems (NeurIPS)",
            "Conference on Computer Vision and Pattern Recognition (CVPR)",
            "International Conference on Learning Representations (ICLR)",
            "Association for Computational Linguistics (ACL)",
            "International Conference on Robotics and Automation (ICRA)",
            "International Symposium on Biomedical Imaging (ISBI)",
            "American Physical Society March Meeting",
            "International Conference on Software Engineering (ICSE)",
            "Conference on Human Factors in Computing Systems (CHI)",
        ]
        return random.choice(conferences)
    
    @staticmethod
    def random_journal() -> str:
        """Generate a random academic journal."""
        journals = [
            "Nature",
            "Science",
            "Cell",
            "The Lancet",
            "Physical Review Letters",
            "Journal of Machine Learning Research",
            "IEEE Transactions on Pattern Analysis and Machine Intelligence",
            "Proceedings of the National Academy of Sciences",
            "Journal of the American Chemical Society",
            "Annual Review of Neuroscience",
        ]
        return random.choice(journals)
    
    @staticmethod
    def random_research_keywords() -> list[str]:
        """Generate random research keywords."""
        all_keywords = [
            "machine learning", "deep learning", "neural networks",
            "computer vision", "natural language processing",
            "quantum computing", "protein folding", "gene editing",
            "climate modeling", "renewable energy", "nanotechnology",
            "artificial intelligence", "robotics", "bioinformatics",
            "cryptography", "distributed systems", "algorithms",
        ]
        num_keywords = random.randint(3, 7)
        return random.sample(all_keywords, num_keywords)
    
    @staticmethod
    def random_timestamp(days_ago: int = 30) -> datetime:
        """Generate a random timestamp within the past N days."""
        now = datetime.now(timezone.utc)
        seconds_ago = random.randint(0, days_ago * 24 * 60 * 60)
        return now.replace(microsecond=0) - timedelta(seconds=seconds_ago)
    
    @staticmethod
    def random_future_timestamp(days_ahead: int = 30) -> datetime:
        """Generate a random future timestamp within the next N days."""
        now = datetime.now(timezone.utc)
        seconds_ahead = random.randint(0, days_ahead * 24 * 60 * 60)
        return now.replace(microsecond=0) + timedelta(seconds=seconds_ahead)


from datetime import timedelta


class DictFactory(BaseFactory):
    """Base factory for creating dictionary objects."""
    
    class Meta:
        abstract = True
    
    @classmethod
    def _build(cls, model_class, **kwargs) -> Dict[str, Any]:
        """Build a dictionary instead of a model instance."""
        return kwargs
    
    @classmethod
    def _create(cls, model_class, **kwargs) -> Dict[str, Any]:
        """Create returns the same as build for dict factories."""
        return cls._build(model_class, **kwargs)


# Faker instance for more sophisticated fake data
from faker import Faker
fake = Faker()

# Academic-specific faker
class AcademicFaker:
    """Faker with academic-specific methods."""
    
    @staticmethod
    def abstract(sentences: int = 5) -> str:
        """Generate an academic abstract."""
        intro = "This paper presents a novel approach to"
        problem = fake.bs()
        method = f"We propose a {fake.word()} {fake.word()} method that"
        results = f"achieves {random.randint(10, 30)}% improvement over baseline methods."
        conclusion = "Our results demonstrate the effectiveness of the proposed approach."
        
        abstract_parts = [intro, problem + ".", method, results, conclusion]
        extra_sentences = [fake.sentence() for _ in range(max(0, sentences - 5))]
        
        return " ".join(abstract_parts + extra_sentences)
    
    @staticmethod
    def research_title() -> str:
        """Generate an academic research title."""
        templates = [
            "A Novel Approach to {topic} Using {method}",
            "{method} for {topic}: A Comprehensive Study",
            "Investigating {topic} Through {method} Analysis",
            "Towards Better {topic}: {method} and Applications",
            "{topic} in the Era of {context}: Challenges and Opportunities",
        ]
        
        topics = [
            "Deep Learning", "Quantum Computing", "Protein Folding",
            "Climate Modeling", "Natural Language Processing",
            "Computer Vision", "Distributed Systems", "Bioinformatics",
        ]
        
        methods = [
            "Transformer Networks", "Graph Neural Networks",
            "Reinforcement Learning", "Bayesian Optimization",
            "Monte Carlo Methods", "Genetic Algorithms",
            "Convolutional Networks", "Attention Mechanisms",
        ]
        
        contexts = [
            "Big Data", "Edge Computing", "Quantum Supremacy",
            "Artificial General Intelligence", "Sustainable Computing",
        ]
        
        template = random.choice(templates)
        return template.format(
            topic=random.choice(topics),
            method=random.choice(methods),
            context=random.choice(contexts)
        )
    
    @staticmethod
    def equation() -> str:
        """Generate a LaTeX equation."""
        equations = [
            r"E = mc^2",
            r"\nabla \cdot \mathbf{E} = \frac{\rho}{\epsilon_0}",
            r"\frac{\partial u}{\partial t} = \alpha \nabla^2 u",
            r"H\psi = E\psi",
            r"\mathcal{L} = \frac{1}{2}m\dot{x}^2 - V(x)",
            r"F = ma",
            r"\oint_C \mathbf{B} \cdot d\mathbf{l} = \mu_0 I",
            r"\Delta G = \Delta H - T\Delta S",
        ]
        return random.choice(equations)
    
    @staticmethod
    def citation_text() -> str:
        """Generate a citation in text format."""
        authors = [fake.name() for _ in range(random.randint(1, 4))]
        if len(authors) > 2:
            author_str = f"{authors[0]} et al."
        elif len(authors) == 2:
            author_str = f"{authors[0]} and {authors[1]}"
        else:
            author_str = authors[0]
        
        year = random.randint(2015, 2024)
        return f"({author_str}, {year})"


# Export the academic faker
academic_fake = AcademicFaker()