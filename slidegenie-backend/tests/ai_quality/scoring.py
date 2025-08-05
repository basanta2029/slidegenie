"""
Quality Scoring Algorithms Module.

Provides comprehensive scoring algorithms for AI quality assessment.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.preprocessing import MinMaxScaler

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class QualityScore:
    """Comprehensive quality score."""
    overall_score: float  # 0.0 to 1.0
    dimension_scores: Dict[str, float]
    weighted_score: float
    confidence: float
    grade: str  # A+, A, B+, B, C, D, F
    percentile: float
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]


class QualityScorer:
    """Calculates and interprets quality scores."""
    
    def __init__(self):
        # Weight configuration for different dimensions
        self.dimension_weights = {
            "prompt_effectiveness": {
                "relevance": 0.25,
                "efficiency": 0.20,
                "consistency": 0.20,
                "injection_resistance": 0.15,
                "context_utilization": 0.20,
            },
            "output_quality": {
                "coherence": 0.20,
                "grammar": 0.15,
                "academic_tone": 0.20,
                "visual_balance": 0.15,
                "consistency": 0.15,
                "readability": 0.15,
            },
            "academic_accuracy": {
                "facts": 0.25,
                "citations": 0.25,
                "references": 0.20,
                "terminology": 0.15,
                "statistics": 0.15,
            },
            "specialized_content": {
                "equations": 0.25,
                "code": 0.20,
                "formulas": 0.20,
                "diagrams": 0.20,
                "tables": 0.15,
            },
        }
        
        # Overall category weights
        self.category_weights = {
            "prompt_effectiveness": 0.20,
            "output_quality": 0.35,
            "academic_accuracy": 0.30,
            "specialized_content": 0.15,
        }
        
        # Grade thresholds
        self.grade_thresholds = {
            "A+": 0.95,
            "A": 0.90,
            "A-": 0.85,
            "B+": 0.80,
            "B": 0.75,
            "B-": 0.70,
            "C+": 0.65,
            "C": 0.60,
            "C-": 0.55,
            "D": 0.50,
            "F": 0.0,
        }
        
        # Historical scores for percentile calculation
        self.historical_scores = []
    
    def calculate_overall_score(self, results: Dict[str, Any]) -> QualityScore:
        """
        Calculate comprehensive quality score from all test results.
        
        Args:
            results: Dictionary containing all test results
            
        Returns:
            QualityScore with detailed breakdown
        """
        # Extract dimension scores
        dimension_scores = self._extract_dimension_scores(results)
        
        # Calculate weighted scores
        category_scores = self._calculate_category_scores(dimension_scores)
        
        # Calculate overall weighted score
        weighted_score = self._calculate_weighted_score(category_scores)
        
        # Calculate simple average for comparison
        all_scores = []
        for category_dims in dimension_scores.values():
            all_scores.extend(category_dims.values())
        overall_score = np.mean(all_scores) if all_scores else 0.0
        
        # Calculate confidence based on score consistency
        confidence = self._calculate_confidence(dimension_scores)
        
        # Determine grade
        grade = self._determine_grade(weighted_score)
        
        # Calculate percentile
        percentile = self._calculate_percentile(weighted_score)
        
        # Identify strengths and weaknesses
        strengths = self._identify_strengths(dimension_scores, results)
        weaknesses = self._identify_weaknesses(dimension_scores, results)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(dimension_scores, results)
        
        return QualityScore(
            overall_score=float(overall_score),
            dimension_scores=self._flatten_dimension_scores(dimension_scores),
            weighted_score=float(weighted_score),
            confidence=float(confidence),
            grade=grade,
            percentile=float(percentile),
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
        )
    
    def _extract_dimension_scores(self, results: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
        """Extract dimension scores from test results."""
        dimension_scores = {}
        
        # Prompt effectiveness scores
        if "prompt_effectiveness" in results:
            pe_result = results["prompt_effectiveness"]
            dimension_scores["prompt_effectiveness"] = {
                "relevance": pe_result.relevance_score,
                "efficiency": pe_result.token_efficiency,
                "consistency": pe_result.consistency_score,
                "injection_resistance": 1.0 if pe_result.injection_resistance else 0.0,
                "context_utilization": pe_result.context_utilization,
            }
        
        # Output quality scores
        if "output_quality" in results:
            oq_result = results["output_quality"]
            dimension_scores["output_quality"] = {
                "coherence": oq_result.coherence_score,
                "grammar": oq_result.grammar_score,
                "academic_tone": oq_result.academic_tone_score,
                "visual_balance": oq_result.visual_balance_score,
                "consistency": oq_result.consistency_score,
                "readability": oq_result.readability_score,
            }
        
        # Academic accuracy scores
        if "academic_accuracy" in results:
            aa_result = results["academic_accuracy"]
            dimension_scores["academic_accuracy"] = {
                "facts": aa_result.fact_accuracy_score,
                "citations": aa_result.citation_accuracy_score,
                "references": aa_result.reference_validity_score,
                "terminology": aa_result.terminology_consistency_score,
                "statistics": aa_result.statistical_validity_score,
            }
        
        # Specialized content scores
        if "specialized_content" in results:
            sc_result = results["specialized_content"]
            dimension_scores["specialized_content"] = {
                "equations": sc_result.equation_accuracy,
                "code": sc_result.code_validity,
                "formulas": sc_result.formula_accuracy,
                "diagrams": sc_result.diagram_quality,
                "tables": sc_result.table_integrity,
            }
        
        return dimension_scores
    
    def _calculate_category_scores(self, dimension_scores: Dict[str, Dict[str, float]]) -> Dict[str, float]:
        """Calculate weighted scores for each category."""
        category_scores = {}
        
        for category, dimensions in dimension_scores.items():
            if category in self.dimension_weights:
                weights = self.dimension_weights[category]
                weighted_sum = sum(
                    dimensions.get(dim, 0.0) * weight
                    for dim, weight in weights.items()
                )
                total_weight = sum(
                    weight for dim, weight in weights.items()
                    if dim in dimensions
                )
                category_scores[category] = weighted_sum / total_weight if total_weight > 0 else 0.0
            else:
                # Simple average if no weights defined
                category_scores[category] = np.mean(list(dimensions.values()))
        
        return category_scores
    
    def _calculate_weighted_score(self, category_scores: Dict[str, float]) -> float:
        """Calculate overall weighted score."""
        weighted_sum = sum(
            category_scores.get(cat, 0.0) * weight
            for cat, weight in self.category_weights.items()
        )
        total_weight = sum(
            weight for cat, weight in self.category_weights.items()
            if cat in category_scores
        )
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def _calculate_confidence(self, dimension_scores: Dict[str, Dict[str, float]]) -> float:
        """Calculate confidence based on score consistency."""
        all_scores = []
        for dimensions in dimension_scores.values():
            all_scores.extend(dimensions.values())
        
        if len(all_scores) < 2:
            return 0.5
        
        # Calculate standard deviation
        std_dev = np.std(all_scores)
        
        # Lower std dev = higher confidence
        # Map std dev to confidence (0.5 std = 0.5 confidence, 0 std = 1.0 confidence)
        confidence = max(0.0, 1.0 - std_dev)
        
        # Adjust for number of dimensions tested
        dimension_count = sum(len(dims) for dims in dimension_scores.values())
        expected_dimensions = sum(len(weights) for weights in self.dimension_weights.values())
        
        coverage_ratio = dimension_count / expected_dimensions if expected_dimensions > 0 else 0.0
        confidence *= coverage_ratio
        
        return confidence
    
    def _determine_grade(self, score: float) -> str:
        """Determine letter grade from score."""
        for grade, threshold in self.grade_thresholds.items():
            if score >= threshold:
                return grade
        return "F"
    
    def _calculate_percentile(self, score: float) -> float:
        """Calculate percentile based on historical scores."""
        # Add current score to history
        self.historical_scores.append(score)
        
        # If we have enough historical data
        if len(self.historical_scores) >= 10:
            # Calculate percentile
            scores_below = sum(1 for s in self.historical_scores if s < score)
            percentile = (scores_below / len(self.historical_scores)) * 100
        else:
            # Estimate percentile based on score distribution
            # Assume normal distribution with mean 0.7, std 0.15
            from scipy.stats import norm
            percentile = norm.cdf(score, loc=0.7, scale=0.15) * 100
        
        return min(99.9, max(0.1, percentile))
    
    def _identify_strengths(self, dimension_scores: Dict[str, Dict[str, float]], 
                           results: Dict[str, Any]) -> List[str]:
        """Identify strengths based on high scores."""
        strengths = []
        
        # Find dimensions with excellent scores (>= 0.9)
        for category, dimensions in dimension_scores.items():
            for dim, score in dimensions.items():
                if score >= 0.9:
                    strength = self._format_strength(category, dim, score)
                    if strength:
                        strengths.append(strength)
        
        # Add specific achievements from results
        if "academic_accuracy" in results:
            verified_facts = results["academic_accuracy"].verified_facts
            if len(verified_facts) >= 5:
                strengths.append(f"Strong factual accuracy with {len(verified_facts)} verified claims")
        
        if "specialized_content" in results:
            verified_content = results["specialized_content"].verified_content
            if len(verified_content) >= 3:
                strengths.append(f"Excellent handling of specialized content ({len(verified_content)} verified elements)")
        
        return strengths[:5]  # Limit to top 5 strengths
    
    def _identify_weaknesses(self, dimension_scores: Dict[str, Dict[str, float]], 
                            results: Dict[str, Any]) -> List[str]:
        """Identify weaknesses based on low scores."""
        weaknesses = []
        
        # Find dimensions with poor scores (< 0.6)
        for category, dimensions in dimension_scores.items():
            for dim, score in dimensions.items():
                if score < 0.6:
                    weakness = self._format_weakness(category, dim, score)
                    if weakness:
                        weaknesses.append(weakness)
        
        # Add critical issues from results
        all_issues = []
        for result_key in ["output_quality", "academic_accuracy", "specialized_content"]:
            if result_key in results and hasattr(results[result_key], "issues"):
                all_issues.extend(results[result_key].issues)
        
        critical_issues = [i for i in all_issues if i.get("severity") == "critical"]
        if critical_issues:
            weaknesses.append(f"Critical issues found: {len(critical_issues)} requiring immediate attention")
        
        return weaknesses[:5]  # Limit to top 5 weaknesses
    
    def _generate_recommendations(self, dimension_scores: Dict[str, Dict[str, float]], 
                                 results: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        # Priority 1: Address critical issues
        critical_recs = self._get_critical_recommendations(results)
        recommendations.extend(critical_recs)
        
        # Priority 2: Improve lowest scoring dimensions
        lowest_dims = self._get_lowest_dimensions(dimension_scores, n=3)
        for category, dim, score in lowest_dims:
            rec = self._get_dimension_recommendation(category, dim, score)
            if rec:
                recommendations.append(rec)
        
        # Priority 3: Optimization suggestions for good scores
        if len(recommendations) < 5:
            optimization_recs = self._get_optimization_recommendations(dimension_scores)
            recommendations.extend(optimization_recs)
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    def _flatten_dimension_scores(self, dimension_scores: Dict[str, Dict[str, float]]) -> Dict[str, float]:
        """Flatten nested dimension scores."""
        flattened = {}
        for category, dimensions in dimension_scores.items():
            for dim, score in dimensions.items():
                flattened[f"{category}.{dim}"] = score
        return flattened
    
    def _format_strength(self, category: str, dimension: str, score: float) -> Optional[str]:
        """Format a strength description."""
        strength_map = {
            ("prompt_effectiveness", "relevance"): "Highly relevant and focused prompts",
            ("prompt_effectiveness", "injection_resistance"): "Excellent security against prompt injection",
            ("output_quality", "coherence"): "Outstanding logical flow and coherence",
            ("output_quality", "academic_tone"): "Exemplary academic writing style",
            ("academic_accuracy", "citations"): "Comprehensive and accurate citations",
            ("academic_accuracy", "facts"): "Exceptional factual accuracy",
            ("specialized_content", "equations"): "Perfect mathematical equation formatting",
        }
        
        key = (category, dimension)
        if key in strength_map:
            return f"{strength_map[key]} (score: {score:.2f})"
        
        return None
    
    def _format_weakness(self, category: str, dimension: str, score: float) -> Optional[str]:
        """Format a weakness description."""
        weakness_map = {
            ("prompt_effectiveness", "relevance"): "Prompts lack clear focus and relevance",
            ("prompt_effectiveness", "efficiency"): "Inefficient token usage in prompts",
            ("output_quality", "grammar"): "Grammar and spelling errors present",
            ("output_quality", "readability"): "Content is difficult to read and understand",
            ("academic_accuracy", "citations"): "Missing or incorrect citations",
            ("academic_accuracy", "references"): "Invalid or incomplete references",
            ("specialized_content", "equations"): "Mathematical equations contain errors",
        }
        
        key = (category, dimension)
        if key in weakness_map:
            return f"{weakness_map[key]} (score: {score:.2f})"
        
        return None
    
    def _get_critical_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Get recommendations for critical issues."""
        recommendations = []
        
        # Check for critical issues in each category
        if "output_quality" in results:
            issues = results["output_quality"].issues
            critical = [i for i in issues if i.get("severity") == "critical"]
            if critical:
                recommendations.append(
                    f"Address {len(critical)} critical output quality issues immediately"
                )
        
        if "academic_accuracy" in results:
            if results["academic_accuracy"].citation_accuracy_score < 0.5:
                recommendations.append(
                    "Urgently fix citation accuracy - over 50% of citations have issues"
                )
        
        return recommendations
    
    def _get_lowest_dimensions(self, dimension_scores: Dict[str, Dict[str, float]], 
                               n: int = 3) -> List[Tuple[str, str, float]]:
        """Get the n lowest scoring dimensions."""
        all_dims = []
        for category, dimensions in dimension_scores.items():
            for dim, score in dimensions.items():
                all_dims.append((category, dim, score))
        
        # Sort by score
        all_dims.sort(key=lambda x: x[2])
        
        return all_dims[:n]
    
    def _get_dimension_recommendation(self, category: str, dimension: str, score: float) -> Optional[str]:
        """Get specific recommendation for a dimension."""
        recommendations = {
            ("prompt_effectiveness", "relevance"): 
                "Improve prompt clarity with specific instructions and examples",
            ("prompt_effectiveness", "efficiency"): 
                "Optimize prompts to reduce token usage while maintaining quality",
            ("output_quality", "coherence"): 
                "Add transition phrases and ensure logical flow between slides",
            ("output_quality", "grammar"): 
                "Implement automated grammar checking in content pipeline",
            ("academic_accuracy", "citations"): 
                "Ensure all claims have proper citations in standard format",
            ("academic_accuracy", "statistics"): 
                "Verify all statistical claims and add confidence intervals",
            ("specialized_content", "equations"): 
                "Validate LaTeX syntax and mathematical notation",
        }
        
        key = (category, dimension)
        if key in recommendations:
            return recommendations[key]
        
        return None
    
    def _get_optimization_recommendations(self, dimension_scores: Dict[str, Dict[str, float]]) -> List[str]:
        """Get optimization recommendations for already good scores."""
        recommendations = []
        
        # Calculate category averages
        category_avgs = {}
        for category, dimensions in dimension_scores.items():
            category_avgs[category] = np.mean(list(dimensions.values()))
        
        # If output quality is good but could be excellent
        if 0.7 <= category_avgs.get("output_quality", 0) < 0.9:
            recommendations.append(
                "Consider A/B testing different output formats to optimize quality further"
            )
        
        # If academic accuracy is good
        if category_avgs.get("academic_accuracy", 0) >= 0.8:
            recommendations.append(
                "Maintain high academic standards with regular quality audits"
            )
        
        return recommendations
    
    def generate_detailed_report(self, score: QualityScore, results: Dict[str, Any]) -> str:
        """Generate a detailed quality report."""
        report = []
        
        # Header
        report.append("="*60)
        report.append("AI QUALITY ASSESSMENT REPORT")
        report.append("="*60)
        report.append("")
        
        # Overall Score
        report.append(f"Overall Score: {score.weighted_score:.2%}")
        report.append(f"Grade: {score.grade}")
        report.append(f"Percentile: {score.percentile:.1f}%")
        report.append(f"Confidence: {score.confidence:.2%}")
        report.append("")
        
        # Category Breakdown
        report.append("Category Scores:")
        report.append("-"*40)
        
        categories = {}
        for key, value in score.dimension_scores.items():
            category, dimension = key.split(".")
            if category not in categories:
                categories[category] = []
            categories[category].append((dimension, value))
        
        for category, dimensions in categories.items():
            cat_scores = [s for _, s in dimensions]
            cat_avg = np.mean(cat_scores)
            report.append(f"\n{category.replace('_', ' ').title()}: {cat_avg:.2%}")
            
            for dim, score_val in sorted(dimensions, key=lambda x: x[1], reverse=True):
                report.append(f"  - {dim.replace('_', ' ').title()}: {score_val:.2%}")
        
        # Strengths
        if score.strengths:
            report.append("\nStrengths:")
            report.append("-"*40)
            for i, strength in enumerate(score.strengths, 1):
                report.append(f"{i}. {strength}")
        
        # Weaknesses
        if score.weaknesses:
            report.append("\nAreas for Improvement:")
            report.append("-"*40)
            for i, weakness in enumerate(score.weaknesses, 1):
                report.append(f"{i}. {weakness}")
        
        # Recommendations
        if score.recommendations:
            report.append("\nRecommendations:")
            report.append("-"*40)
            for i, rec in enumerate(score.recommendations, 1):
                report.append(f"{i}. {rec}")
        
        # Issue Summary
        total_issues = 0
        critical_issues = 0
        
        for result_key in ["output_quality", "academic_accuracy", "specialized_content"]:
            if result_key in results and hasattr(results[result_key], "issues"):
                issues = results[result_key].issues
                total_issues += len(issues)
                critical_issues += len([i for i in issues if i.get("severity") == "critical"])
        
        report.append("\nIssue Summary:")
        report.append("-"*40)
        report.append(f"Total Issues: {total_issues}")
        report.append(f"Critical Issues: {critical_issues}")
        
        report.append("\n" + "="*60)
        
        return "\n".join(report)