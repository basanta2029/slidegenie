"""
Comprehensive test suite for AI quality testing.

Demonstrates usage of all AI quality testing components.
"""
import asyncio
import time
from typing import Any, Dict, List

import pytest

from app.domain.schemas.generation import Citation
from app.services.ai.base import AIProviderBase

from . import (
    PromptEffectivenessTest,
    OutputQualityValidator,
    AcademicAccuracyTest,
    SpecializedContentTest,
    QualityScorer,
    ReferenceValidator,
    ContentValidator,
    BenchmarkDataset,
    EvaluationMetrics,
)
from .human_validation import HumanValidationInterface, ValidationTask
from .prompt_effectiveness import PromptStrategy


class TestAIQualitySuite:
    """Test suite demonstrating AI quality testing capabilities."""
    
    @pytest.fixture
    def sample_presentation_content(self):
        """Sample presentation content for testing."""
        return {
            "slides": [
                {
                    "title": "Introduction to Deep Learning",
                    "content": "Deep learning has revolutionized artificial intelligence...",
                    "bullet_points": [
                        "Neural networks with multiple hidden layers",
                        "Automatic feature extraction from raw data",
                        "State-of-the-art performance in many domains"
                    ],
                    "speaker_notes": "Emphasize the transformative impact of deep learning",
                    "has_figure": True,
                    "figure_caption": "Figure 1: Deep neural network architecture"
                },
                {
                    "title": "Methodology",
                    "content": "We employed a convolutional neural network (CNN) architecture...",
                    "bullet_points": [
                        "Dataset: ImageNet with 1.2 million images",
                        "Architecture: ResNet-50 with batch normalization",
                        "Training: SGD with learning rate 0.1, momentum 0.9"
                    ],
                    "has_equation": True,
                    "equations": ["$L = -\\sum_{i=1}^{N} y_i \\log(\\hat{y}_i)$"]
                },
                {
                    "title": "Results",
                    "content": "Our experiments demonstrate significant improvements...",
                    "bullet_points": [
                        "Accuracy improved from 76.3% to 94.2% (p < 0.001)",
                        "Processing time reduced by 45% compared to baseline",
                        "Model size decreased from 238MB to 87MB"
                    ],
                    "has_table": True,
                    "citations": ["(Smith et al., 2023)", "[1]", "[2-4]"]
                }
            ],
            "references": [
                Citation(
                    id="1",
                    authors=["Smith, J.", "Doe, A."],
                    title="Advances in Deep Learning Architecture",
                    year=2023,
                    journal="Nature Machine Intelligence",
                    volume=5,
                    issue=3,
                    pages="234-245",
                    doi="10.1038/s42256-023-00123-4"
                ),
                Citation(
                    id="2",
                    authors=["Johnson, M."],
                    title="Efficient Neural Network Training",
                    year=2022,
                    conference="ICML",
                    pages="1234-1243"
                )
            ],
            "prompt": "Generate a presentation on deep learning advances",
            "context": {
                "content_type": "content_to_slides",
                "academic_level": "graduate",
                "target_duration": 15,
                "audience": "ML researchers"
            }
        }
    
    def test_prompt_effectiveness(self, sample_presentation_content):
        """Test prompt effectiveness evaluation."""
        test = PromptEffectivenessTest()
        
        # Test single prompt
        result = test.evaluate(sample_presentation_content)
        
        assert result.relevance_score > 0.5
        assert result.injection_resistance is True
        assert result.context_utilization > 0.0
        
        # Test prompt strategy comparison
        strategies = [
            PromptStrategy(
                name="detailed",
                template="Generate a {academic_level} presentation on {topic} with detailed explanations",
                temperature=0.7
            ),
            PromptStrategy(
                name="concise",
                template="Create slides about {topic} for {audience}. Be concise.",
                temperature=0.5
            ),
            PromptStrategy(
                name="structured",
                template="Presentation outline:\n1. Introduction to {topic}\n2. Methodology\n3. Results\n4. Conclusion",
                temperature=0.3
            )
        ]
        
        comparison = test.compare_strategies(
            strategies,
            {
                "topic": "deep learning advances",
                "academic_level": "graduate",
                "audience": "ML researchers"
            }
        )
        
        assert comparison["best_strategy"] is not None
        assert len(comparison["rankings"]) == 3
        
        # Test context optimization
        full_context = {
            "abstract": "This paper presents...",
            "introduction": "Deep learning has...",
            "methodology": "We employed...",
            "results": "Our experiments...",
            "figures": ["fig1", "fig2", "fig3"],
            "tables": ["table1", "table2"]
        }
        
        optimized = test.optimize_context_window(
            sample_presentation_content["prompt"],
            full_context,
            target_tokens=2000
        )
        
        assert optimized["token_count"] <= 2000
        assert optimized["utilization"] > 0.8
    
    def test_output_quality_validation(self, sample_presentation_content):
        """Test output quality validation."""
        validator = OutputQualityValidator()
        
        metrics = validator.validate(sample_presentation_content)
        
        # Check metrics
        assert 0.0 <= metrics.coherence_score <= 1.0
        assert 0.0 <= metrics.grammar_score <= 1.0
        assert 0.0 <= metrics.academic_tone_score <= 1.0
        assert 0.0 <= metrics.visual_balance_score <= 1.0
        assert 0.0 <= metrics.consistency_score <= 1.0
        assert 0.0 <= metrics.readability_score <= 1.0
        
        # Check for issues
        assert isinstance(metrics.issues, list)
        
        # Check metadata
        assert metrics.metadata["slide_count"] == 3
        assert metrics.metadata["avg_text_length"] > 0
        assert 0.0 <= metrics.metadata["vocabulary_diversity"] <= 1.0
    
    def test_academic_accuracy(self, sample_presentation_content):
        """Test academic accuracy assessment."""
        test = AcademicAccuracyTest()
        
        result = test.assess(sample_presentation_content)
        
        # Check accuracy scores
        assert 0.0 <= result.fact_accuracy_score <= 1.0
        assert 0.0 <= result.citation_accuracy_score <= 1.0
        assert 0.0 <= result.reference_validity_score <= 1.0
        assert 0.0 <= result.terminology_consistency_score <= 1.0
        assert 0.0 <= result.statistical_validity_score <= 1.0
        
        # Check for verified facts
        assert isinstance(result.verified_facts, list)
        
        # Check metadata
        assert result.metadata["total_claims"] >= 0
        assert result.metadata["statistical_claims"] >= 1  # We have p-value and percentages
    
    def test_specialized_content(self, sample_presentation_content):
        """Test specialized content verification."""
        test = SpecializedContentTest()
        
        result = test.verify(sample_presentation_content)
        
        # Check content accuracy scores
        assert 0.0 <= result.equation_accuracy <= 1.0
        assert 0.0 <= result.code_validity <= 1.0
        assert 0.0 <= result.formula_accuracy <= 1.0
        assert 0.0 <= result.diagram_quality <= 1.0
        assert 0.0 <= result.table_integrity <= 1.0
        
        # Check verified content
        assert isinstance(result.verified_content, list)
        assert result.metadata["equation_count"] >= 1  # We have one equation
    
    def test_quality_scoring(self, sample_presentation_content):
        """Test comprehensive quality scoring."""
        # Run all tests
        prompt_test = PromptEffectivenessTest()
        output_validator = OutputQualityValidator()
        accuracy_test = AcademicAccuracyTest()
        specialized_test = SpecializedContentTest()
        
        results = {
            "prompt_effectiveness": prompt_test.evaluate(sample_presentation_content),
            "output_quality": output_validator.validate(sample_presentation_content),
            "academic_accuracy": accuracy_test.assess(sample_presentation_content),
            "specialized_content": specialized_test.verify(sample_presentation_content),
        }
        
        # Calculate overall score
        scorer = QualityScorer()
        quality_score = scorer.calculate_overall_score(results)
        
        # Check score properties
        assert 0.0 <= quality_score.overall_score <= 1.0
        assert 0.0 <= quality_score.weighted_score <= 1.0
        assert 0.0 <= quality_score.confidence <= 1.0
        assert quality_score.grade in ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D", "F"]
        assert 0.0 <= quality_score.percentile <= 100.0
        
        # Check insights
        assert isinstance(quality_score.strengths, list)
        assert isinstance(quality_score.weaknesses, list)
        assert isinstance(quality_score.recommendations, list)
        
        # Generate detailed report
        report = scorer.generate_detailed_report(quality_score, results)
        assert isinstance(report, str)
        assert "Overall Score:" in report
        assert "Grade:" in report
    
    def test_reference_validation(self, sample_presentation_content):
        """Test reference and citation validation."""
        validator = ReferenceValidator()
        
        # Validate individual references
        for ref in sample_presentation_content["references"]:
            result = validator.validate_reference(ref)
            
            assert isinstance(result["valid"], bool)
            assert isinstance(result["issues"], list)
            assert isinstance(result["warnings"], list)
            assert 0.0 <= result["completeness_score"] <= 1.0
        
        # Check citation consistency
        consistency = validator.validate_citation_consistency(
            sample_presentation_content["references"]
        )
        
        assert isinstance(consistency["consistent"], bool)
        assert isinstance(consistency["issues"], list)
    
    def test_content_validation(self, sample_presentation_content):
        """Test content integrity validation."""
        validator = ContentValidator()
        
        # Combine all slide content
        all_content = " ".join(
            slide.get("content", "") + " ".join(slide.get("bullet_points", []))
            for slide in sample_presentation_content["slides"]
        )
        
        result = validator.validate_content(
            all_content,
            sample_presentation_content["references"]
        )
        
        assert isinstance(result["valid"], bool)
        assert isinstance(result["issues"], list)
        assert result["metrics"]["claim_count"] >= 0
        assert result["metrics"]["statistical_claims"] >= 1
    
    def test_benchmark_evaluation(self, sample_presentation_content):
        """Test benchmark dataset evaluation."""
        dataset = BenchmarkDataset()
        metrics = EvaluationMetrics()
        
        # Get benchmark cases
        cases = dataset.get_dataset("academic_writing")
        assert len(cases) > 0
        
        # Simulate evaluation of a benchmark case
        case = cases[0]
        
        # Mock actual output and scores
        actual_output = {
            "has_formal_tone": True,
            "has_clear_structure": True,
            "contains_key_points": True,
        }
        
        actual_scores = {
            "coherence": 0.82,
            "academic_tone": 0.88,
            "readability": 0.79,
        }
        
        # Evaluate benchmark
        start_time = time.time()
        result = metrics.evaluate_benchmark(
            case,
            actual_output,
            actual_scores,
            int((time.time() - start_time) * 1000)
        )
        
        assert result.case_id == case.id
        assert 0.0 <= result.accuracy <= 1.0
        assert 0.0 <= result.f1_score <= 1.0
        assert isinstance(result.passed, bool)
        
        # Test aggregate metrics
        aggregate = metrics.calculate_aggregate_metrics([result])
        
        assert "overall_metrics" in aggregate
        assert aggregate["overall_metrics"]["total_cases"] == 1
    
    def test_human_validation_interface(self, sample_presentation_content):
        """Test human-in-the-loop validation interface."""
        interface = HumanValidationInterface()
        
        # Create validation tasks
        quality_task = interface.create_quality_rating_task(
            sample_presentation_content["slides"][0],
            ["coherence", "accuracy", "clarity"],
            validator_id="test_validator"
        )
        
        assert quality_task.task_type == "quality_rating"
        assert quality_task.assigned_to == "test_validator"
        
        # Start validation session
        session = interface.start_validation_session("test_validator")
        assert session.validator_id == "test_validator"
        assert session.total_tasks > 0
        
        # Get next task
        next_task = interface.get_next_task(session.id)
        assert next_task is not None
        assert next_task.id == quality_task.id
        
        # Submit response
        response = {
            "ratings": {
                "coherence": 4,
                "accuracy": 5,
                "clarity": 4
            },
            "feedback": "Well-structured introduction with clear points"
        }
        
        success = interface.submit_task_response(
            quality_task.id,
            response,
            confidence=0.85,
            time_spent_seconds=45
        )
        assert success is True
        
        # End session
        completed_session = interface.end_validation_session(session.id)
        assert completed_session is not None
        assert completed_session.tasks_completed == 1
        
        # Generate validation report
        report = interface.generate_validation_report()
        
        assert "summary" in report
        assert report["summary"]["total_tasks"] == 1
        assert report["summary"]["average_confidence"] == 0.85
    
    def test_human_ai_agreement(self):
        """Test human-AI agreement calculation."""
        metrics = EvaluationMetrics()
        
        # Mock human and AI scores
        human_scores = [
            {"coherence": 0.85, "accuracy": 0.90, "clarity": 0.80},
            {"coherence": 0.80, "accuracy": 0.95, "clarity": 0.85},
            {"coherence": 0.90, "accuracy": 0.85, "clarity": 0.75},
        ]
        
        ai_scores = [
            {"coherence": 0.82, "accuracy": 0.92, "clarity": 0.78},
            {"coherence": 0.85, "accuracy": 0.90, "clarity": 0.82},
            {"coherence": 0.88, "accuracy": 0.87, "clarity": 0.80},
        ]
        
        agreement = metrics.calculate_human_agreement(human_scores, ai_scores)
        
        assert 0.0 <= agreement["exact_agreement"] <= 1.0
        assert -1.0 <= agreement["cohens_kappa"] <= 1.0
        assert -1.0 <= agreement["correlation"] <= 1.0
        assert agreement["interpretation"] in [
            "poor_agreement", "slight_agreement", "fair_agreement",
            "moderate_agreement", "substantial_agreement", "almost_perfect_agreement"
        ]
    
    @pytest.mark.asyncio
    async def test_full_quality_pipeline(self, sample_presentation_content):
        """Test the complete quality assessment pipeline."""
        from . import run_full_quality_suite
        
        # Run full quality suite
        results = run_full_quality_suite(sample_presentation_content)
        
        # Verify all components ran
        assert "prompt_effectiveness" in results
        assert "output_quality" in results
        assert "academic_accuracy" in results
        assert "specialized_content" in results
        assert "overall_score" in results
        
        # Check overall score
        overall = results["overall_score"]
        assert 0.0 <= overall.weighted_score <= 1.0
        assert overall.grade is not None
        
        # Print summary for debugging
        print(f"\nQuality Assessment Summary:")
        print(f"Overall Score: {overall.weighted_score:.2%}")
        print(f"Grade: {overall.grade}")
        print(f"Confidence: {overall.confidence:.2%}")
        print(f"\nStrengths:")
        for strength in overall.strengths[:3]:
            print(f"  - {strength}")
        print(f"\nAreas for Improvement:")
        for weakness in overall.weaknesses[:3]:
            print(f"  - {weakness}")
        print(f"\nTop Recommendations:")
        for rec in overall.recommendations[:3]:
            print(f"  - {rec}")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])