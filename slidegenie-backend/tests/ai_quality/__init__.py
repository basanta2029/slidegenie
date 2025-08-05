"""
AI Quality Testing Suite for SlideGenie.

This module provides comprehensive testing for AI-generated content quality,
including prompt effectiveness, output validation, academic accuracy, and
specialized content verification.
"""
from typing import Dict, Any

from .prompt_effectiveness import PromptEffectivenessTest
from .output_quality import OutputQualityValidator
from .academic_accuracy import AcademicAccuracyTest
from .specialized_content import SpecializedContentTest
from .scoring import QualityScorer
from .validators import ReferenceValidator, ContentValidator
from .benchmarks import BenchmarkDataset, EvaluationMetrics

__all__ = [
    "PromptEffectivenessTest",
    "OutputQualityValidator",
    "AcademicAccuracyTest",
    "SpecializedContentTest",
    "QualityScorer",
    "ReferenceValidator",
    "ContentValidator",
    "BenchmarkDataset",
    "EvaluationMetrics",
]


def run_full_quality_suite(content: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the complete AI quality test suite on generated content.
    
    Args:
        content: Generated content to evaluate
        
    Returns:
        Comprehensive quality report
    """
    results = {
        "prompt_effectiveness": PromptEffectivenessTest().evaluate(content),
        "output_quality": OutputQualityValidator().validate(content),
        "academic_accuracy": AcademicAccuracyTest().assess(content),
        "specialized_content": SpecializedContentTest().verify(content),
    }
    
    # Calculate overall score
    scorer = QualityScorer()
    results["overall_score"] = scorer.calculate_overall_score(results)
    
    return results