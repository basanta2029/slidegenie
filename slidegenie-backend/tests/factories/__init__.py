"""Test factories for SlideGenie."""

from .user_factory import UserFactory, UserProfileFactory
from .presentation_factory import PresentationFactory, SlideFactory
from .academic_factory import (
    ResearchPaperFactory,
    ThesisFactory,
    CitationFactory,
    AcademicContentFactory,
)
from .file_factory import FileFactory, MockFileFactory
from .response_factory import MockResponseFactory, APIResponseFactory
from .job_factory import GenerationJobFactory
from .template_factory import TemplateFactory, TemplateCategoryFactory

__all__ = [
    "UserFactory",
    "UserProfileFactory",
    "PresentationFactory",
    "SlideFactory",
    "ResearchPaperFactory",
    "ThesisFactory",
    "CitationFactory",
    "AcademicContentFactory",
    "FileFactory",
    "MockFileFactory",
    "MockResponseFactory",
    "APIResponseFactory",
    "GenerationJobFactory",
    "TemplateFactory",
    "TemplateCategoryFactory",
]