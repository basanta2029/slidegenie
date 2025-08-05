"""
Prompt Effectiveness Testing Module.

Tests the effectiveness of prompts used for AI content generation,
including relevance, injection resistance, and optimization.
"""
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from statistics import mean, stdev

import structlog
from pydantic import BaseModel, Field

from app.services.ai.base import AIProviderBase, ContentType

logger = structlog.get_logger(__name__)


@dataclass
class PromptTestResult:
    """Result of a prompt effectiveness test."""
    relevance_score: float  # 0.0 to 1.0
    response_time_ms: int
    token_efficiency: float  # output_quality / tokens_used
    injection_resistance: bool
    context_utilization: float  # How well context was used
    consistency_score: float  # Consistency across multiple runs
    metadata: Dict[str, Any]


class PromptStrategy(BaseModel):
    """A prompt strategy configuration."""
    name: str
    template: str
    system_prompt: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    variables: List[str] = Field(default_factory=list)
    

class PromptEffectivenessTest:
    """Tests prompt effectiveness for AI content generation."""
    
    def __init__(self, ai_provider: Optional[AIProviderBase] = None):
        self.ai_provider = ai_provider
        self.injection_patterns = [
            "ignore previous instructions",
            "disregard the above",
            "new task:",
            "system prompt:",
            "forget everything",
            "</system>",
            "```system",
            "ADMIN MODE:",
            "DEBUG:",
        ]
        
        self.quality_indicators = {
            "academic_tone": [
                r'\b(?:research|study|analysis|findings|methodology|hypothesis)\b',
                r'\b(?:demonstrate|indicate|suggest|reveal|evidence)\b',
                r'\b(?:significant|correlation|implications|framework)\b',
            ],
            "structure": [
                r'(?:first|second|third|finally|in conclusion)',
                r'(?:introduction|background|methods|results|discussion)',
                r'\b(?:however|moreover|furthermore|nevertheless|therefore)\b',
            ],
            "precision": [
                r'\d+(?:\.\d+)?%',  # Percentages
                r'\b(?:approximately|roughly|about|nearly)\s+\d+',
                r'p\s*[<>=]\s*0\.\d+',  # p-values
                r'n\s*=\s*\d+',  # sample sizes
            ],
        }
    
    def evaluate(self, content: Dict[str, Any]) -> PromptTestResult:
        """
        Evaluate prompt effectiveness for content generation.
        
        Args:
            content: Content configuration including prompt and context
            
        Returns:
            PromptTestResult with comprehensive metrics
        """
        prompt = content.get("prompt", "")
        context = content.get("context", {})
        
        # Test response relevance
        relevance_score = self._test_relevance(prompt, context)
        
        # Test response time
        response_time = self._measure_response_time(prompt)
        
        # Test token efficiency
        token_efficiency = self._calculate_token_efficiency(prompt, context)
        
        # Test injection resistance
        injection_resistant = self._test_injection_resistance(prompt)
        
        # Test context utilization
        context_utilization = self._measure_context_utilization(prompt, context)
        
        # Test consistency
        consistency_score = self._test_consistency(prompt, context)
        
        return PromptTestResult(
            relevance_score=relevance_score,
            response_time_ms=response_time,
            token_efficiency=token_efficiency,
            injection_resistance=injection_resistant,
            context_utilization=context_utilization,
            consistency_score=consistency_score,
            metadata={
                "prompt_length": len(prompt),
                "context_size": len(str(context)),
                "quality_indicators": self._count_quality_indicators(prompt),
            }
        )
    
    def compare_strategies(
        self,
        strategies: List[PromptStrategy],
        test_content: Dict[str, Any],
        iterations: int = 3
    ) -> Dict[str, Any]:
        """
        Compare different prompt strategies.
        
        Args:
            strategies: List of prompt strategies to compare
            test_content: Content to test with
            iterations: Number of test iterations per strategy
            
        Returns:
            Comparison results with rankings
        """
        results = {}
        
        for strategy in strategies:
            strategy_results = []
            
            for _ in range(iterations):
                # Format prompt with strategy
                formatted_prompt = strategy.template.format(**test_content)
                
                # Run evaluation
                result = self.evaluate({
                    "prompt": formatted_prompt,
                    "context": test_content.get("context", {}),
                    "system_prompt": strategy.system_prompt,
                })
                
                strategy_results.append(result)
            
            # Aggregate results
            results[strategy.name] = {
                "avg_relevance": mean([r.relevance_score for r in strategy_results]),
                "avg_response_time": mean([r.response_time_ms for r in strategy_results]),
                "avg_token_efficiency": mean([r.token_efficiency for r in strategy_results]),
                "consistency": mean([r.consistency_score for r in strategy_results]),
                "injection_resistant": all([r.injection_resistance for r in strategy_results]),
            }
        
        # Rank strategies
        rankings = self._rank_strategies(results)
        
        return {
            "results": results,
            "rankings": rankings,
            "best_strategy": rankings[0] if rankings else None,
        }
    
    def optimize_context_window(
        self,
        prompt: str,
        full_context: Dict[str, Any],
        target_tokens: int = 4000
    ) -> Dict[str, Any]:
        """
        Optimize context window usage for maximum effectiveness.
        
        Args:
            prompt: Base prompt
            full_context: Full available context
            target_tokens: Target token count
            
        Returns:
            Optimized context configuration
        """
        # Prioritize context elements
        prioritized_elements = self._prioritize_context_elements(full_context)
        
        # Build optimized context within token limit
        optimized_context = {}
        current_tokens = self._estimate_tokens(prompt)
        
        for element, priority in prioritized_elements:
            element_tokens = self._estimate_tokens(str(element))
            
            if current_tokens + element_tokens <= target_tokens:
                key = element.get("type", "unknown")
                if key not in optimized_context:
                    optimized_context[key] = []
                optimized_context[key].append(element)
                current_tokens += element_tokens
        
        return {
            "optimized_context": optimized_context,
            "token_count": current_tokens,
            "utilization": current_tokens / target_tokens,
            "excluded_elements": len(full_context) - len(optimized_context),
        }
    
    def _test_relevance(self, prompt: str, context: Dict[str, Any]) -> float:
        """Test how relevant the response would be to the prompt."""
        score = 0.0
        
        # Check for clear instructions
        if any(word in prompt.lower() for word in ["create", "generate", "write", "explain"]):
            score += 0.2
        
        # Check for specific requirements
        requirements = re.findall(r'(?:include|contain|must have|should have)([^.]+)', prompt, re.I)
        if requirements:
            score += 0.2
        
        # Check for academic context
        if context.get("content_type") in ["abstract_to_outline", "content_to_slides"]:
            score += 0.2
        
        # Check for quality indicators
        indicator_count = self._count_quality_indicators(prompt)
        if indicator_count["total"] > 5:
            score += 0.2
        
        # Check prompt structure
        if len(prompt.split('\n')) > 1 and any(char in prompt for char in ['•', '-', '1.', '*']):
            score += 0.2
        
        return min(score, 1.0)
    
    def _measure_response_time(self, prompt: str) -> int:
        """Measure simulated response time based on prompt complexity."""
        # Base time
        base_time = 100
        
        # Add time for length
        length_factor = len(prompt) // 100 * 10
        
        # Add time for complexity
        complexity_factor = len(re.findall(r'[.!?]', prompt)) * 5
        
        # Add time for special requirements
        special_requirements = len(re.findall(r'\b(?:ensure|must|specific|detailed|comprehensive)\b', prompt, re.I))
        requirement_factor = special_requirements * 20
        
        return base_time + length_factor + complexity_factor + requirement_factor
    
    def _calculate_token_efficiency(self, prompt: str, context: Dict[str, Any]) -> float:
        """Calculate token efficiency score."""
        prompt_tokens = self._estimate_tokens(prompt)
        context_tokens = self._estimate_tokens(str(context))
        total_tokens = prompt_tokens + context_tokens
        
        # Estimate output quality based on input
        quality_score = self._count_quality_indicators(prompt)["total"] / 10
        
        # Calculate efficiency
        if total_tokens > 0:
            efficiency = quality_score / (total_tokens / 1000)
            return min(efficiency, 1.0)
        
        return 0.0
    
    def _test_injection_resistance(self, prompt: str) -> bool:
        """Test if prompt is resistant to injection attacks."""
        prompt_lower = prompt.lower()
        
        # Check for injection patterns
        for pattern in self.injection_patterns:
            if pattern in prompt_lower:
                return False
        
        # Check for suspicious formatting
        if "```" in prompt and "system" in prompt_lower:
            return False
        
        # Check for role switching attempts
        if re.search(r'\b(?:you are now|act as|pretend to be)\b', prompt_lower):
            return False
        
        return True
    
    def _measure_context_utilization(self, prompt: str, context: Dict[str, Any]) -> float:
        """Measure how well the prompt utilizes available context."""
        if not context:
            return 1.0  # Perfect if no context needed
        
        utilization_score = 0.0
        context_str = str(context).lower()
        
        # Check for context references in prompt
        context_references = [
            "based on", "according to", "from the", "using the",
            "as shown", "as described", "mentioned", "provided"
        ]
        
        for ref in context_references:
            if ref in prompt.lower():
                utilization_score += 0.1
        
        # Check for specific context element references
        if "abstract" in context and "abstract" in prompt.lower():
            utilization_score += 0.2
        
        if "methodology" in context and any(word in prompt.lower() for word in ["method", "approach"]):
            utilization_score += 0.2
        
        if "results" in context and any(word in prompt.lower() for word in ["results", "findings"]):
            utilization_score += 0.2
        
        return min(utilization_score, 1.0)
    
    def _test_consistency(self, prompt: str, context: Dict[str, Any], runs: int = 3) -> float:
        """Test consistency of outputs across multiple runs."""
        # Simulate consistency based on prompt characteristics
        consistency_score = 1.0
        
        # Reduce consistency for vague prompts
        vague_terms = ["some", "maybe", "possibly", "might", "could", "various"]
        vague_count = sum(1 for term in vague_terms if term in prompt.lower())
        consistency_score -= vague_count * 0.1
        
        # Increase consistency for structured prompts
        if re.search(r'\b\d+\.', prompt):  # Numbered lists
            consistency_score += 0.1
        
        if "format:" in prompt.lower() or "structure:" in prompt.lower():
            consistency_score += 0.1
        
        # Temperature affects consistency
        temperature = context.get("temperature", 0.7)
        consistency_score -= (temperature - 0.3) * 0.2
        
        return max(0.0, min(consistency_score, 1.0))
    
    def _count_quality_indicators(self, text: str) -> Dict[str, int]:
        """Count quality indicators in text."""
        counts = {}
        total = 0
        
        for category, patterns in self.quality_indicators.items():
            category_count = 0
            for pattern in patterns:
                matches = re.findall(pattern, text, re.I)
                category_count += len(matches)
            counts[category] = category_count
            total += category_count
        
        counts["total"] = total
        return counts
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        # Rough approximation: 1 token ≈ 4 characters
        return len(text) // 4
    
    def _prioritize_context_elements(self, context: Dict[str, Any]) -> List[Tuple[Any, float]]:
        """Prioritize context elements by importance."""
        prioritized = []
        
        # Define priorities for different element types
        priorities = {
            "abstract": 0.9,
            "key_findings": 0.85,
            "methodology": 0.8,
            "results": 0.75,
            "figures": 0.7,
            "tables": 0.65,
            "citations": 0.6,
            "background": 0.5,
        }
        
        for key, value in context.items():
            priority = priorities.get(key, 0.3)
            if isinstance(value, list):
                for item in value:
                    prioritized.append(({"type": key, "content": item}, priority))
            else:
                prioritized.append(({"type": key, "content": value}, priority))
        
        # Sort by priority
        prioritized.sort(key=lambda x: x[1], reverse=True)
        
        return prioritized
    
    def _rank_strategies(self, results: Dict[str, Dict[str, float]]) -> List[str]:
        """Rank strategies based on results."""
        # Calculate composite scores
        scores = {}
        
        for strategy, metrics in results.items():
            # Weighted scoring
            score = (
                metrics["avg_relevance"] * 0.3 +
                metrics["avg_token_efficiency"] * 0.25 +
                metrics["consistency"] * 0.2 +
                (1.0 if metrics["injection_resistant"] else 0.0) * 0.15 +
                (1.0 - min(metrics["avg_response_time"] / 1000, 1.0)) * 0.1
            )
            scores[strategy] = score
        
        # Sort by score
        return sorted(scores.keys(), key=lambda x: scores[x], reverse=True)