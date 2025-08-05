"""Unit tests for analytics service."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any, List
import json

from app.services.analytics_service import AnalyticsService
from tests.unit.utils.test_helpers import TestDataGenerator


class TestAnalyticsService:
    """Test suite for analytics service."""
    
    @pytest.fixture
    def analytics_service(self):
        """Create analytics service instance."""
        return AnalyticsService()
    
    @pytest.fixture
    def mock_analytics_repo(self):
        """Create mock analytics repository."""
        repo = AsyncMock()
        return repo
    
    @pytest.fixture
    def mock_cache(self):
        """Create mock cache."""
        cache = AsyncMock()
        return cache
    
    @pytest.fixture
    def test_events(self):
        """Generate test analytics events."""
        events = []
        base_time = datetime.utcnow() - timedelta(days=7)
        
        event_types = [
            "presentation_created",
            "presentation_viewed",
            "slide_edited",
            "template_used",
            "export_completed"
        ]
        
        for i in range(100):
            event = {
                "id": i + 1,
                "user_id": (i % 10) + 1,
                "event_type": event_types[i % len(event_types)],
                "properties": {
                    "presentation_id": (i % 20) + 1,
                    "duration_seconds": 30 + (i * 5),
                    "slide_count": 10 + (i % 15)
                },
                "timestamp": base_time + timedelta(hours=i),
                "session_id": f"session_{i // 10}",
                "ip_address": f"192.168.1.{i % 255}",
                "user_agent": "Mozilla/5.0..."
            }
            events.append(event)
        
        return events
    
    @pytest.mark.asyncio
    async def test_track_event(self, analytics_service, mock_analytics_repo):
        """Test event tracking."""
        analytics_service.analytics_repository = mock_analytics_repo
        
        event_data = {
            "user_id": 1,
            "event_type": "presentation_created",
            "properties": {
                "presentation_id": 123,
                "slide_count": 20,
                "template_used": "academic"
            }
        }
        
        mock_analytics_repo.create_event.return_value = {
            "id": 1,
            **event_data,
            "timestamp": datetime.utcnow()
        }
        
        result = await analytics_service.track_event(
            user_id=event_data['user_id'],
            event_type=event_data['event_type'],
            properties=event_data['properties']
        )
        
        assert result['event_type'] == "presentation_created"
        assert result['properties']['slide_count'] == 20
        
        # Verify repository call
        mock_analytics_repo.create_event.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_analytics(self, analytics_service, mock_analytics_repo, test_events):
        """Test getting user analytics."""
        analytics_service.analytics_repository = mock_analytics_repo
        
        user_id = 1
        user_events = [e for e in test_events if e['user_id'] == user_id]
        
        mock_analytics_repo.get_user_events.return_value = user_events
        
        # Mock aggregated metrics
        with patch.object(analytics_service, '_calculate_user_metrics', new_callable=AsyncMock) as mock_calc:
            mock_calc.return_value = {
                "total_presentations": 5,
                "total_slides_created": 85,
                "average_presentation_size": 17,
                "most_used_template": "academic",
                "export_formats": {"pptx": 3, "pdf": 2},
                "active_days": 4,
                "last_active": datetime.utcnow()
            }
            
            result = await analytics_service.get_user_analytics(
                user_id=user_id,
                start_date=datetime.utcnow() - timedelta(days=30),
                end_date=datetime.utcnow()
            )
        
        assert result['total_presentations'] == 5
        assert result['average_presentation_size'] == 17
        assert result['most_used_template'] == "academic"
    
    @pytest.mark.asyncio
    async def test_get_system_analytics(self, analytics_service, mock_analytics_repo, test_events):
        """Test getting system-wide analytics."""
        analytics_service.analytics_repository = mock_analytics_repo
        
        mock_analytics_repo.get_all_events.return_value = test_events
        
        # Mock aggregated system metrics
        with patch.object(analytics_service, '_calculate_system_metrics', new_callable=AsyncMock) as mock_calc:
            mock_calc.return_value = {
                "total_users": 50,
                "active_users_today": 12,
                "active_users_week": 35,
                "active_users_month": 45,
                "total_presentations": 234,
                "total_slides": 3456,
                "popular_templates": [
                    {"name": "academic", "usage": 89},
                    {"name": "business", "usage": 67},
                    {"name": "creative", "usage": 45}
                ],
                "peak_usage_hours": [14, 15, 16],  # 2-5 PM
                "average_session_duration": 1250  # seconds
            }
            
            result = await analytics_service.get_system_analytics(
                period="month"
            )
        
        assert result['total_users'] == 50
        assert result['active_users_month'] == 45
        assert len(result['popular_templates']) == 3
        assert result['popular_templates'][0]['name'] == "academic"
    
    @pytest.mark.asyncio
    async def test_get_presentation_analytics(self, analytics_service, mock_analytics_repo):
        """Test getting analytics for specific presentation."""
        analytics_service.analytics_repository = mock_analytics_repo
        
        presentation_id = 123
        presentation_events = [
            {"event_type": "presentation_viewed", "user_id": 1, "timestamp": datetime.utcnow()},
            {"event_type": "presentation_viewed", "user_id": 2, "timestamp": datetime.utcnow()},
            {"event_type": "slide_edited", "properties": {"slide_id": 1}},
            {"event_type": "export_completed", "properties": {"format": "pptx"}}
        ]
        
        mock_analytics_repo.get_presentation_events.return_value = presentation_events
        
        result = await analytics_service.get_presentation_analytics(presentation_id)
        
        assert result['view_count'] >= 2
        assert result['unique_viewers'] >= 2
        assert result['edit_count'] >= 1
        assert result['export_count'] >= 1
        assert 'pptx' in result['export_formats']
    
    @pytest.mark.asyncio
    async def test_generate_analytics_report(self, analytics_service, mock_analytics_repo, mock_cache):
        """Test analytics report generation."""
        analytics_service.analytics_repository = mock_analytics_repo
        analytics_service.cache = mock_cache
        
        # Mock cache miss
        mock_cache.get.return_value = None
        
        # Mock report data
        with patch.object(analytics_service, '_compile_report_data', new_callable=AsyncMock) as mock_compile:
            mock_compile.return_value = {
                "period": {"start": "2024-01-01", "end": "2024-01-31"},
                "summary": {
                    "total_users": 100,
                    "new_users": 25,
                    "presentations_created": 450,
                    "total_slides": 6750
                },
                "trends": {
                    "user_growth": 12.5,
                    "presentation_growth": 23.4,
                    "average_slides_per_presentation": 15
                },
                "top_performers": {
                    "most_active_users": [
                        {"id": 1, "name": "User 1", "presentations": 23}
                    ],
                    "popular_presentations": [
                        {"id": 123, "title": "ML Overview", "views": 145}
                    ]
                }
            }
            
            result = await analytics_service.generate_report(
                report_type="monthly",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31)
            )
        
        assert result['summary']['total_users'] == 100
        assert result['trends']['user_growth'] == 12.5
        assert len(result['top_performers']['most_active_users']) > 0
        
        # Verify caching
        mock_cache.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_real_time_analytics(self, analytics_service, mock_analytics_repo):
        """Test real-time analytics streaming."""
        analytics_service.analytics_repository = mock_analytics_repo
        
        # Mock real-time events
        real_time_events = [
            {
                "event_type": "slide_viewed",
                "user_id": 1,
                "properties": {"slide_id": 1, "duration": 5},
                "timestamp": datetime.utcnow()
            }
        ]
        
        mock_analytics_repo.get_recent_events.return_value = real_time_events
        
        result = await analytics_service.get_real_time_analytics(
            window_minutes=5
        )
        
        assert 'active_users' in result
        assert 'recent_events' in result
        assert len(result['recent_events']) > 0
        assert result['events_per_minute'] >= 0
    
    @pytest.mark.asyncio
    async def test_export_analytics_data(self, analytics_service, mock_analytics_repo, test_events):
        """Test analytics data export."""
        analytics_service.analytics_repository = mock_analytics_repo
        
        mock_analytics_repo.get_all_events.return_value = test_events
        
        # Test CSV export
        csv_result = await analytics_service.export_analytics(
            format="csv",
            start_date=datetime.utcnow() - timedelta(days=30),
            end_date=datetime.utcnow()
        )
        
        assert csv_result['format'] == "csv"
        assert 'data' in csv_result
        assert 'event_type,user_id' in csv_result['data']  # CSV headers
        
        # Test JSON export
        json_result = await analytics_service.export_analytics(
            format="json",
            start_date=datetime.utcnow() - timedelta(days=30),
            end_date=datetime.utcnow()
        )
        
        assert json_result['format'] == "json"
        data = json.loads(json_result['data'])
        assert isinstance(data, list)
        assert len(data) > 0
    
    @pytest.mark.asyncio
    async def test_funnel_analysis(self, analytics_service, mock_analytics_repo):
        """Test conversion funnel analysis."""
        analytics_service.analytics_repository = mock_analytics_repo
        
        # Mock funnel events
        funnel_events = {
            "signup": 100,
            "first_presentation": 75,
            "complete_presentation": 60,
            "export_presentation": 45,
            "share_presentation": 30
        }
        
        with patch.object(analytics_service, '_calculate_funnel_metrics', new_callable=AsyncMock) as mock_funnel:
            mock_funnel.return_value = {
                "steps": [
                    {"name": "signup", "users": 100, "conversion": 100},
                    {"name": "first_presentation", "users": 75, "conversion": 75},
                    {"name": "complete_presentation", "users": 60, "conversion": 80},
                    {"name": "export_presentation", "users": 45, "conversion": 75},
                    {"name": "share_presentation", "users": 30, "conversion": 66.7}
                ],
                "overall_conversion": 30,
                "drop_off_points": [
                    {"step": "signup -> first_presentation", "drop_rate": 25},
                    {"step": "first_presentation -> complete", "drop_rate": 20}
                ]
            }
            
            result = await analytics_service.analyze_funnel(
                funnel_steps=list(funnel_events.keys())
            )
        
        assert len(result['steps']) == 5
        assert result['overall_conversion'] == 30
        assert len(result['drop_off_points']) > 0
    
    @pytest.mark.asyncio
    async def test_cohort_analysis(self, analytics_service, mock_analytics_repo):
        """Test user cohort analysis."""
        analytics_service.analytics_repository = mock_analytics_repo
        
        with patch.object(analytics_service, '_analyze_cohorts', new_callable=AsyncMock) as mock_cohort:
            mock_cohort.return_value = {
                "cohorts": [
                    {
                        "name": "January 2024",
                        "size": 50,
                        "retention": {
                            "week_1": 80,
                            "week_2": 65,
                            "week_4": 45,
                            "week_8": 35
                        }
                    },
                    {
                        "name": "February 2024",
                        "size": 75,
                        "retention": {
                            "week_1": 85,
                            "week_2": 70,
                            "week_4": 55
                        }
                    }
                ],
                "average_retention": {
                    "week_1": 82.5,
                    "week_2": 67.5,
                    "week_4": 50
                }
            }
            
            result = await analytics_service.analyze_cohorts(
                cohort_type="monthly",
                metric="retention"
            )
        
        assert len(result['cohorts']) == 2
        assert result['cohorts'][0]['name'] == "January 2024"
        assert result['average_retention']['week_1'] == 82.5
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self, analytics_service, mock_analytics_repo):
        """Test system performance metrics."""
        analytics_service.analytics_repository = mock_analytics_repo
        
        with patch.object(analytics_service, '_collect_performance_metrics', new_callable=AsyncMock) as mock_perf:
            mock_perf.return_value = {
                "api_metrics": {
                    "average_response_time": 125,  # ms
                    "p95_response_time": 250,
                    "p99_response_time": 500,
                    "error_rate": 0.02,
                    "requests_per_second": 45
                },
                "generation_metrics": {
                    "average_generation_time": 3.4,  # seconds
                    "success_rate": 0.98,
                    "queue_depth": 5
                },
                "resource_usage": {
                    "cpu_usage": 45.2,
                    "memory_usage": 62.8,
                    "storage_usage": 78.5
                }
            }
            
            result = await analytics_service.get_performance_metrics()
        
        assert result['api_metrics']['average_response_time'] == 125
        assert result['generation_metrics']['success_rate'] == 0.98
        assert result['resource_usage']['storage_usage'] == 78.5