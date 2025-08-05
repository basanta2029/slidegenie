"""Unit tests for cost optimizer."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any, List

from app.services.ai.cost_optimizer import CostOptimizer, ModelConfig, UsageMetrics


class TestCostOptimizer:
    """Test suite for AI cost optimizer."""
    
    @pytest.fixture
    def optimizer(self):
        """Create cost optimizer instance."""
        return CostOptimizer()
    
    @pytest.fixture
    def model_configs(self):
        """Sample model configurations."""
        return {
            "gpt-4": ModelConfig(
                name="gpt-4",
                provider="openai",
                cost_per_1k_input_tokens=0.03,
                cost_per_1k_output_tokens=0.06,
                max_tokens=8192,
                quality_score=0.95,
                speed_score=0.7
            ),
            "gpt-3.5-turbo": ModelConfig(
                name="gpt-3.5-turbo",
                provider="openai",
                cost_per_1k_input_tokens=0.001,
                cost_per_1k_output_tokens=0.002,
                max_tokens=4096,
                quality_score=0.85,
                speed_score=0.9
            ),
            "claude-3-opus": ModelConfig(
                name="claude-3-opus",
                provider="anthropic",
                cost_per_1k_input_tokens=0.015,
                cost_per_1k_output_tokens=0.075,
                max_tokens=200000,
                quality_score=0.98,
                speed_score=0.6
            ),
            "claude-3-sonnet": ModelConfig(
                name="claude-3-sonnet",
                provider="anthropic",
                cost_per_1k_input_tokens=0.003,
                cost_per_1k_output_tokens=0.015,
                max_tokens=200000,
                quality_score=0.9,
                speed_score=0.8
            )
        }
    
    @pytest.fixture
    def usage_history(self):
        """Sample usage history."""
        return [
            UsageMetrics(
                model="gpt-4",
                timestamp=datetime.utcnow() - timedelta(hours=1),
                input_tokens=1500,
                output_tokens=800,
                cost=0.093,  # (1.5 * 0.03) + (0.8 * 0.06)
                task_type="complex_analysis",
                success=True
            ),
            UsageMetrics(
                model="gpt-3.5-turbo",
                timestamp=datetime.utcnow() - timedelta(hours=2),
                input_tokens=2000,
                output_tokens=1000,
                cost=0.004,  # (2 * 0.001) + (1 * 0.002)
                task_type="simple_generation",
                success=True
            ),
            UsageMetrics(
                model="claude-3-opus",
                timestamp=datetime.utcnow() - timedelta(hours=3),
                input_tokens=5000,
                output_tokens=2000,
                cost=0.225,  # (5 * 0.015) + (2 * 0.075)
                task_type="complex_analysis",
                success=True
            )
        ]
    
    def test_calculate_token_cost(self, optimizer, model_configs):
        """Test token cost calculation for different models."""
        optimizer.model_configs = model_configs
        
        # Test GPT-4 cost
        gpt4_cost = optimizer.calculate_cost(
            model="gpt-4",
            input_tokens=1000,
            output_tokens=500
        )
        assert gpt4_cost == 0.06  # (1 * 0.03) + (0.5 * 0.06)
        
        # Test Claude-3-Sonnet cost
        claude_cost = optimizer.calculate_cost(
            model="claude-3-sonnet",
            input_tokens=3000,
            output_tokens=1500
        )
        assert claude_cost == 0.0315  # (3 * 0.003) + (1.5 * 0.015)
    
    def test_select_optimal_model_for_task(self, optimizer, model_configs):
        """Test optimal model selection based on task requirements."""
        optimizer.model_configs = model_configs
        
        # Test for high-quality task
        high_quality_model = optimizer.select_model(
            task_type="complex_analysis",
            estimated_tokens=5000,
            quality_requirement=0.9,
            budget_constraint=1.0
        )
        assert high_quality_model in ["claude-3-opus", "gpt-4", "claude-3-sonnet"]
        
        # Test for cost-sensitive task
        budget_model = optimizer.select_model(
            task_type="simple_generation",
            estimated_tokens=2000,
            quality_requirement=0.8,
            budget_constraint=0.01
        )
        assert budget_model == "gpt-3.5-turbo"
        
        # Test for speed-critical task
        fast_model = optimizer.select_model(
            task_type="real_time_response",
            estimated_tokens=1000,
            quality_requirement=0.85,
            speed_requirement=0.85
        )
        assert fast_model in ["gpt-3.5-turbo", "claude-3-sonnet"]
    
    def test_track_usage_metrics(self, optimizer):
        """Test usage metrics tracking."""
        # Track multiple uses
        optimizer.track_usage(
            model="gpt-4",
            input_tokens=1000,
            output_tokens=500,
            cost=0.06,
            task_type="analysis",
            success=True
        )
        
        optimizer.track_usage(
            model="gpt-3.5-turbo",
            input_tokens=2000,
            output_tokens=1000,
            cost=0.004,
            task_type="generation",
            success=True
        )
        
        # Verify tracking
        assert len(optimizer.usage_history) == 2
        assert optimizer.usage_history[0].model == "gpt-4"
        assert optimizer.usage_history[1].model == "gpt-3.5-turbo"
        assert optimizer.usage_history[0].cost == 0.06
    
    def test_calculate_usage_statistics(self, optimizer, usage_history):
        """Test usage statistics calculation."""
        optimizer.usage_history = usage_history
        
        stats = optimizer.calculate_statistics(period_hours=24)
        
        assert 'total_cost' in stats
        assert 'total_tokens' in stats
        assert 'model_breakdown' in stats
        assert 'task_breakdown' in stats
        
        # Verify totals
        assert stats['total_cost'] == sum(u.cost for u in usage_history)
        assert stats['total_tokens'] == sum(u.input_tokens + u.output_tokens for u in usage_history)
        
        # Verify model breakdown
        assert 'gpt-4' in stats['model_breakdown']
        assert 'claude-3-opus' in stats['model_breakdown']
        assert stats['model_breakdown']['gpt-4']['usage_count'] == 1
    
    def test_budget_monitoring(self, optimizer, usage_history):
        """Test budget monitoring and alerts."""
        optimizer.usage_history = usage_history
        optimizer.daily_budget_limit = 0.5  # $0.50 daily limit
        optimizer.monthly_budget_limit = 15.0  # $15 monthly limit
        
        # Check daily budget
        daily_usage = optimizer.get_daily_usage()
        daily_remaining = optimizer.get_remaining_daily_budget()
        
        assert daily_usage == sum(u.cost for u in usage_history)
        assert daily_remaining == 0.5 - daily_usage
        
        # Test budget exceeded alert
        is_exceeded, message = optimizer.check_budget_exceeded()
        assert not is_exceeded  # Should not be exceeded with test data
        
        # Add more usage to exceed budget
        optimizer.track_usage(
            model="claude-3-opus",
            input_tokens=10000,
            output_tokens=5000,
            cost=0.525,  # This will exceed daily budget
            task_type="complex_analysis",
            success=True
        )
        
        is_exceeded, message = optimizer.check_budget_exceeded()
        assert is_exceeded
        assert "daily budget" in message.lower()
    
    def test_cost_prediction(self, optimizer, model_configs, usage_history):
        """Test cost prediction for tasks."""
        optimizer.model_configs = model_configs
        optimizer.usage_history = usage_history
        
        # Predict cost for a presentation generation task
        predicted_cost = optimizer.predict_cost(
            task_type="presentation_generation",
            slide_count=20,
            content_complexity="high",
            include_images=True
        )
        
        assert predicted_cost > 0
        assert 'estimated_tokens' in predicted_cost
        assert 'recommended_model' in predicted_cost
        assert 'estimated_cost' in predicted_cost
        assert 'cost_breakdown' in predicted_cost
    
    def test_model_performance_tracking(self, optimizer):
        """Test model performance metrics tracking."""
        # Track successful and failed attempts
        optimizer.track_usage("gpt-4", 1000, 500, 0.06, "analysis", success=True)
        optimizer.track_usage("gpt-4", 1000, 500, 0.06, "analysis", success=True)
        optimizer.track_usage("gpt-4", 1000, 500, 0.06, "analysis", success=False)
        
        performance = optimizer.get_model_performance("gpt-4")
        
        assert performance['total_uses'] == 3
        assert performance['success_rate'] == 2/3
        assert performance['average_cost'] == 0.06
    
    def test_cost_optimization_recommendations(self, optimizer, model_configs, usage_history):
        """Test cost optimization recommendations."""
        optimizer.model_configs = model_configs
        optimizer.usage_history = usage_history
        
        recommendations = optimizer.generate_recommendations()
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        
        # Check recommendation structure
        for rec in recommendations:
            assert 'type' in rec
            assert 'description' in rec
            assert 'potential_savings' in rec
            assert 'implementation' in rec
    
    def test_dynamic_model_switching(self, optimizer, model_configs):
        """Test dynamic model switching based on load."""
        optimizer.model_configs = model_configs
        
        # Simulate high load on primary model
        optimizer.model_loads = {
            "gpt-4": 0.95,  # 95% loaded
            "gpt-3.5-turbo": 0.3,
            "claude-3-opus": 0.8,
            "claude-3-sonnet": 0.4
        }
        
        # Should switch to alternative model
        selected_model = optimizer.select_model_with_load_balancing(
            preferred_model="gpt-4",
            task_type="analysis"
        )
        
        assert selected_model != "gpt-4"  # Should avoid overloaded model
        assert selected_model in ["claude-3-sonnet", "gpt-3.5-turbo"]
    
    def test_token_estimation(self, optimizer):
        """Test token estimation for different content types."""
        # Test text token estimation
        text = "This is a sample presentation about machine learning." * 10
        text_tokens = optimizer.estimate_tokens(text, content_type="text")
        assert text_tokens > 0
        
        # Test slide content estimation
        slide_content = {
            "title": "Introduction to ML",
            "bullet_points": [
                "What is machine learning?",
                "Types of ML algorithms",
                "Applications in real world"
            ],
            "speaker_notes": "Explain each type with examples"
        }
        slide_tokens = optimizer.estimate_tokens(slide_content, content_type="slide")
        assert slide_tokens > 0
        
        # Test document estimation
        document_tokens = optimizer.estimate_tokens(
            {"pages": 10, "avg_words_per_page": 300},
            content_type="document"
        )
        assert document_tokens > 0
    
    def test_batch_processing_optimization(self, optimizer, model_configs):
        """Test batch processing cost optimization."""
        optimizer.model_configs = model_configs
        
        # Single request costs
        single_costs = []
        for i in range(5):
            cost = optimizer.calculate_cost("gpt-4", 500, 200)
            single_costs.append(cost)
        
        total_single_cost = sum(single_costs)
        
        # Batch request cost (should be more efficient)
        batch_cost = optimizer.calculate_batch_cost(
            model="gpt-4",
            requests=[{"input_tokens": 500, "output_tokens": 200} for _ in range(5)],
            batch_discount=0.1  # 10% discount for batching
        )
        
        assert batch_cost < total_single_cost
        assert batch_cost == total_single_cost * 0.9
    
    def test_fallback_model_strategy(self, optimizer, model_configs):
        """Test fallback model selection when primary fails."""
        optimizer.model_configs = model_configs
        
        # Define fallback chain
        fallback_chain = optimizer.create_fallback_chain(
            primary_model="claude-3-opus",
            task_requirements={
                "quality_threshold": 0.85,
                "max_cost_per_request": 0.5
            }
        )
        
        assert len(fallback_chain) >= 2
        assert fallback_chain[0] == "claude-3-opus"
        assert all(
            model_configs[model].quality_score >= 0.85 
            for model in fallback_chain
        )