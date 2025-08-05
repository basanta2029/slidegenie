"""
Benchmark Datasets and Evaluation Metrics Module.

Provides benchmark datasets for testing and evaluation metrics for assessment.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.metrics import precision_recall_fscore_support, cohen_kappa_score

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class BenchmarkCase:
    """A single benchmark test case."""
    id: str
    category: str
    input_data: Dict[str, Any]
    expected_output: Dict[str, Any]
    quality_criteria: Dict[str, float]  # Expected quality scores
    metadata: Dict[str, Any]


@dataclass
class BenchmarkResult:
    """Result of benchmark evaluation."""
    case_id: str
    actual_scores: Dict[str, float]
    expected_scores: Dict[str, float]
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    execution_time_ms: int
    passed: bool
    issues: List[str]


class BenchmarkDataset:
    """Manages benchmark datasets for AI quality testing."""
    
    def __init__(self):
        self.datasets = {
            "academic_writing": self._create_academic_writing_dataset(),
            "citations": self._create_citation_dataset(),
            "statistics": self._create_statistics_dataset(),
            "specialized_content": self._create_specialized_content_dataset(),
        }
    
    def get_dataset(self, category: str) -> List[BenchmarkCase]:
        """Get benchmark dataset by category."""
        return self.datasets.get(category, [])
    
    def get_all_cases(self) -> List[BenchmarkCase]:
        """Get all benchmark cases."""
        all_cases = []
        for cases in self.datasets.values():
            all_cases.extend(cases)
        return all_cases
    
    def _create_academic_writing_dataset(self) -> List[BenchmarkCase]:
        """Create academic writing benchmark cases."""
        return [
            BenchmarkCase(
                id="aw_001",
                category="academic_writing",
                input_data={
                    "prompt": "Generate an introduction slide for a paper on machine learning in healthcare",
                    "context": {
                        "paper_title": "Deep Learning Applications in Medical Imaging",
                        "abstract": "This paper presents a comprehensive review of deep learning techniques...",
                    }
                },
                expected_output={
                    "has_formal_tone": True,
                    "has_clear_structure": True,
                    "contains_key_points": True,
                },
                quality_criteria={
                    "coherence": 0.85,
                    "academic_tone": 0.90,
                    "readability": 0.80,
                },
                metadata={"difficulty": "medium", "domain": "computer_science"}
            ),
            BenchmarkCase(
                id="aw_002",
                category="academic_writing",
                input_data={
                    "prompt": "Create methodology slides for experimental research",
                    "context": {
                        "methodology": "Randomized controlled trial with 500 participants...",
                        "statistical_approach": "ANOVA with post-hoc Bonferroni correction",
                    }
                },
                expected_output={
                    "has_clear_steps": True,
                    "includes_sample_size": True,
                    "mentions_statistics": True,
                },
                quality_criteria={
                    "coherence": 0.90,
                    "accuracy": 0.95,
                    "completeness": 0.85,
                },
                metadata={"difficulty": "hard", "domain": "medical_research"}
            ),
        ]
    
    def _create_citation_dataset(self) -> List[BenchmarkCase]:
        """Create citation benchmark cases."""
        return [
            BenchmarkCase(
                id="cit_001",
                category="citations",
                input_data={
                    "content": "Recent studies have shown significant improvements in accuracy (Smith et al., 2023).",
                    "references": [
                        {
                            "id": "smith2023",
                            "authors": ["Smith, J.", "Doe, A."],
                            "title": "Advances in Neural Networks",
                            "year": 2023,
                            "journal": "Nature Machine Intelligence",
                        }
                    ]
                },
                expected_output={
                    "citation_present": True,
                    "citation_format": "author_year",
                    "reference_match": True,
                },
                quality_criteria={
                    "citation_accuracy": 1.0,
                    "format_consistency": 1.0,
                },
                metadata={"citation_style": "APA"}
            ),
            BenchmarkCase(
                id="cit_002",
                category="citations",
                input_data={
                    "content": "Multiple studies [1-3] demonstrate the effectiveness of this approach.",
                    "references": [
                        {"id": "1", "authors": ["Author A"], "year": 2022},
                        {"id": "2", "authors": ["Author B"], "year": 2023},
                        {"id": "3", "authors": ["Author C"], "year": 2023},
                    ]
                },
                expected_output={
                    "citation_present": True,
                    "citation_format": "numbered",
                    "all_references_valid": True,
                },
                quality_criteria={
                    "citation_accuracy": 1.0,
                    "completeness": 1.0,
                },
                metadata={"citation_style": "IEEE"}
            ),
        ]
    
    def _create_statistics_dataset(self) -> List[BenchmarkCase]:
        """Create statistics benchmark cases."""
        return [
            BenchmarkCase(
                id="stat_001",
                category="statistics",
                input_data={
                    "content": "The results showed a significant improvement (p < 0.001) with 85% accuracy.",
                },
                expected_output={
                    "has_p_value": True,
                    "has_percentage": True,
                    "values_valid": True,
                },
                quality_criteria={
                    "statistical_validity": 1.0,
                    "precision": 1.0,
                },
                metadata={"stat_types": ["p_value", "percentage"]}
            ),
            BenchmarkCase(
                id="stat_002",
                category="statistics",
                input_data={
                    "content": "Mean response time was 250ms ± 50ms (95% CI: 200-300ms, n=100)",
                },
                expected_output={
                    "has_mean": True,
                    "has_std": True,
                    "has_ci": True,
                    "has_sample_size": True,
                },
                quality_criteria={
                    "statistical_validity": 1.0,
                    "completeness": 1.0,
                },
                metadata={"stat_types": ["descriptive", "confidence_interval"]}
            ),
        ]
    
    def _create_specialized_content_dataset(self) -> List[BenchmarkCase]:
        """Create specialized content benchmark cases."""
        return [
            BenchmarkCase(
                id="spec_001",
                category="specialized_content",
                input_data={
                    "content": "The equation $E = mc^2$ demonstrates mass-energy equivalence.",
                },
                expected_output={
                    "has_equation": True,
                    "equation_format": "latex",
                    "equation_valid": True,
                },
                quality_criteria={
                    "equation_accuracy": 1.0,
                    "formatting": 1.0,
                },
                metadata={"content_type": "physics_equation"}
            ),
            BenchmarkCase(
                id="spec_002",
                category="specialized_content",
                input_data={
                    "content": "```python\ndef factorial(n):\n    return 1 if n <= 1 else n * factorial(n-1)\n```",
                },
                expected_output={
                    "has_code": True,
                    "code_language": "python",
                    "syntax_valid": True,
                },
                quality_criteria={
                    "code_validity": 1.0,
                    "formatting": 1.0,
                },
                metadata={"content_type": "code_snippet"}
            ),
        ]


class EvaluationMetrics:
    """Calculates evaluation metrics for quality assessment."""
    
    def __init__(self):
        self.metric_history = []
    
    def evaluate_benchmark(
        self,
        benchmark_case: BenchmarkCase,
        actual_output: Dict[str, Any],
        actual_scores: Dict[str, float],
        execution_time_ms: int
    ) -> BenchmarkResult:
        """
        Evaluate a single benchmark case.
        
        Args:
            benchmark_case: The benchmark case
            actual_output: Actual output produced
            actual_scores: Actual quality scores achieved
            execution_time_ms: Time taken to execute
            
        Returns:
            BenchmarkResult with evaluation metrics
        """
        # Calculate accuracy metrics
        accuracy = self._calculate_accuracy(
            benchmark_case.expected_output,
            actual_output
        )
        
        # Calculate quality score metrics
        score_metrics = self._calculate_score_metrics(
            benchmark_case.quality_criteria,
            actual_scores
        )
        
        # Determine if test passed
        passed = (
            accuracy >= 0.8 and 
            score_metrics["avg_deviation"] <= 0.15
        )
        
        # Identify issues
        issues = self._identify_issues(
            benchmark_case,
            actual_output,
            actual_scores
        )
        
        result = BenchmarkResult(
            case_id=benchmark_case.id,
            actual_scores=actual_scores,
            expected_scores=benchmark_case.quality_criteria,
            accuracy=accuracy,
            precision=score_metrics["precision"],
            recall=score_metrics["recall"],
            f1_score=score_metrics["f1_score"],
            execution_time_ms=execution_time_ms,
            passed=passed,
            issues=issues
        )
        
        # Store for historical analysis
        self.metric_history.append(result)
        
        return result
    
    def calculate_aggregate_metrics(
        self,
        results: List[BenchmarkResult]
    ) -> Dict[str, Any]:
        """
        Calculate aggregate metrics across multiple benchmark results.
        
        Args:
            results: List of benchmark results
            
        Returns:
            Aggregate metrics and statistics
        """
        if not results:
            return {}
        
        # Basic statistics
        pass_rate = sum(1 for r in results if r.passed) / len(results)
        avg_accuracy = np.mean([r.accuracy for r in results])
        avg_f1 = np.mean([r.f1_score for r in results])
        avg_execution_time = np.mean([r.execution_time_ms for r in results])
        
        # Performance by category
        category_metrics = self._calculate_category_metrics(results)
        
        # Quality score deviations
        score_deviations = self._calculate_score_deviations(results)
        
        # Identify systematic issues
        systematic_issues = self._identify_systematic_issues(results)
        
        return {
            "overall_metrics": {
                "pass_rate": pass_rate,
                "average_accuracy": avg_accuracy,
                "average_f1_score": avg_f1,
                "average_execution_time_ms": avg_execution_time,
                "total_cases": len(results),
                "passed_cases": sum(1 for r in results if r.passed),
            },
            "category_breakdown": category_metrics,
            "score_deviations": score_deviations,
            "systematic_issues": systematic_issues,
            "performance_trend": self._calculate_performance_trend(),
        }
    
    def calculate_human_agreement(
        self,
        human_scores: List[Dict[str, float]],
        ai_scores: List[Dict[str, float]]
    ) -> Dict[str, float]:
        """
        Calculate agreement between human and AI quality assessments.
        
        Args:
            human_scores: Human-provided quality scores
            ai_scores: AI-generated quality scores
            
        Returns:
            Agreement metrics including Cohen's kappa
        """
        if not human_scores or not ai_scores:
            return {}
        
        # Flatten scores for comparison
        human_flat = []
        ai_flat = []
        
        for h_score, a_score in zip(human_scores, ai_scores):
            for key in h_score.keys():
                if key in a_score:
                    # Convert to categorical (binned) for kappa
                    human_flat.append(self._bin_score(h_score[key]))
                    ai_flat.append(self._bin_score(a_score[key]))
        
        if not human_flat:
            return {}
        
        # Calculate agreement metrics
        exact_agreement = sum(1 for h, a in zip(human_flat, ai_flat) if h == a) / len(human_flat)
        
        # Cohen's kappa for inter-rater reliability
        kappa = cohen_kappa_score(human_flat, ai_flat)
        
        # Calculate correlation for continuous scores
        human_continuous = []
        ai_continuous = []
        
        for h_score, a_score in zip(human_scores, ai_scores):
            for key in h_score.keys():
                if key in a_score:
                    human_continuous.append(h_score[key])
                    ai_continuous.append(a_score[key])
        
        correlation = np.corrcoef(human_continuous, ai_continuous)[0, 1]
        
        return {
            "exact_agreement": exact_agreement,
            "cohens_kappa": kappa,
            "correlation": correlation,
            "sample_size": len(human_flat),
            "interpretation": self._interpret_kappa(kappa),
        }
    
    def _calculate_accuracy(
        self,
        expected: Dict[str, Any],
        actual: Dict[str, Any]
    ) -> float:
        """Calculate accuracy between expected and actual outputs."""
        if not expected:
            return 1.0
        
        correct = 0
        total = len(expected)
        
        for key, expected_value in expected.items():
            if key in actual:
                if isinstance(expected_value, bool):
                    if actual[key] == expected_value:
                        correct += 1
                elif isinstance(expected_value, str):
                    if actual[key] == expected_value:
                        correct += 1
                elif isinstance(expected_value, (int, float)):
                    if abs(actual[key] - expected_value) < 0.01:
                        correct += 1
                else:
                    # For complex types, check equality
                    if actual[key] == expected_value:
                        correct += 1
        
        return correct / total if total > 0 else 0.0
    
    def _calculate_score_metrics(
        self,
        expected_scores: Dict[str, float],
        actual_scores: Dict[str, float]
    ) -> Dict[str, float]:
        """Calculate metrics for quality scores."""
        if not expected_scores or not actual_scores:
            return {
                "precision": 0.0,
                "recall": 0.0,
                "f1_score": 0.0,
                "avg_deviation": 1.0,
            }
        
        # Calculate deviations
        deviations = []
        matches = 0
        
        for key, expected in expected_scores.items():
            if key in actual_scores:
                deviation = abs(actual_scores[key] - expected)
                deviations.append(deviation)
                
                # Consider a match if within 10% of expected
                if deviation <= 0.1:
                    matches += 1
        
        # Calculate precision/recall based on score matches
        precision = matches / len(actual_scores) if actual_scores else 0.0
        recall = matches / len(expected_scores) if expected_scores else 0.0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        avg_deviation = np.mean(deviations) if deviations else 1.0
        
        return {
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "avg_deviation": avg_deviation,
        }
    
    def _identify_issues(
        self,
        benchmark_case: BenchmarkCase,
        actual_output: Dict[str, Any],
        actual_scores: Dict[str, float]
    ) -> List[str]:
        """Identify specific issues in benchmark execution."""
        issues = []
        
        # Check missing expected outputs
        for key in benchmark_case.expected_output:
            if key not in actual_output:
                issues.append(f"Missing expected output: {key}")
        
        # Check score deviations
        for key, expected in benchmark_case.quality_criteria.items():
            if key in actual_scores:
                deviation = abs(actual_scores[key] - expected)
                if deviation > 0.2:
                    issues.append(
                        f"Large deviation in {key}: expected {expected:.2f}, got {actual_scores[key]:.2f}"
                    )
            else:
                issues.append(f"Missing quality score: {key}")
        
        return issues
    
    def _calculate_category_metrics(
        self,
        results: List[BenchmarkResult]
    ) -> Dict[str, Dict[str, float]]:
        """Calculate metrics broken down by category."""
        # This would need category information from benchmark cases
        # For now, return empty dict
        return {}
    
    def _calculate_score_deviations(
        self,
        results: List[BenchmarkResult]
    ) -> Dict[str, float]:
        """Calculate average score deviations by dimension."""
        deviations = {}
        
        for result in results:
            for key in result.expected_scores:
                if key in result.actual_scores:
                    deviation = abs(result.actual_scores[key] - result.expected_scores[key])
                    if key not in deviations:
                        deviations[key] = []
                    deviations[key].append(deviation)
        
        return {
            key: np.mean(devs) for key, devs in deviations.items()
        }
    
    def _identify_systematic_issues(
        self,
        results: List[BenchmarkResult]
    ) -> List[str]:
        """Identify systematic issues across results."""
        systematic_issues = []
        
        # Check for consistent failures
        issue_counts = {}
        for result in results:
            for issue in result.issues:
                issue_counts[issue] = issue_counts.get(issue, 0) + 1
        
        # Issues appearing in >30% of cases are systematic
        threshold = len(results) * 0.3
        for issue, count in issue_counts.items():
            if count > threshold:
                systematic_issues.append(
                    f"{issue} (appears in {count}/{len(results)} cases)"
                )
        
        return systematic_issues
    
    def _calculate_performance_trend(self) -> Dict[str, Any]:
        """Calculate performance trend over time."""
        if len(self.metric_history) < 2:
            return {"trend": "insufficient_data"}
        
        # Get recent history
        recent = self.metric_history[-10:]
        
        # Calculate trend
        accuracies = [r.accuracy for r in recent]
        times = list(range(len(accuracies)))
        
        # Simple linear regression for trend
        if len(accuracies) >= 3:
            slope = np.polyfit(times, accuracies, 1)[0]
            
            trend = "improving" if slope > 0.01 else "declining" if slope < -0.01 else "stable"
            
            return {
                "trend": trend,
                "slope": slope,
                "recent_average": np.mean(accuracies),
                "sample_size": len(accuracies),
            }
        
        return {"trend": "insufficient_data"}
    
    def _bin_score(self, score: float) -> str:
        """Bin continuous score for categorical comparison."""
        if score >= 0.9:
            return "excellent"
        elif score >= 0.8:
            return "good"
        elif score >= 0.7:
            return "fair"
        elif score >= 0.6:
            return "poor"
        else:
            return "very_poor"
    
    def _interpret_kappa(self, kappa: float) -> str:
        """Interpret Cohen's kappa value."""
        if kappa < 0:
            return "poor_agreement"
        elif kappa < 0.20:
            return "slight_agreement"
        elif kappa < 0.40:
            return "fair_agreement"
        elif kappa < 0.60:
            return "moderate_agreement"
        elif kappa < 0.80:
            return "substantial_agreement"
        else:
            return "almost_perfect_agreement"