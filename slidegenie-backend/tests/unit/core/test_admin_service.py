"""Unit tests for admin service."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any, List

from app.services.admin_service import AdminService
from tests.unit.utils.test_helpers import TestDataGenerator


class TestAdminService:
    """Test suite for admin service."""
    
    @pytest.fixture
    def admin_service(self):
        """Create admin service instance."""
        return AdminService()
    
    @pytest.fixture
    def mock_repos(self):
        """Create mock repositories."""
        return {
            'user_repo': AsyncMock(),
            'presentation_repo': AsyncMock(),
            'template_repo': AsyncMock(),
            'analytics_repo': AsyncMock()
        }
    
    @pytest.fixture
    def admin_user(self):
        """Generate admin user data."""
        return TestDataGenerator.generate_user(
            user_id=1,
            email="admin@example.com",
            role="admin"
        )
    
    @pytest.mark.asyncio
    async def test_get_dashboard_stats(self, admin_service, mock_repos):
        """Test admin dashboard statistics."""
        admin_service.user_repository = mock_repos['user_repo']
        admin_service.presentation_repository = mock_repos['presentation_repo']
        admin_service.template_repository = mock_repos['template_repo']
        
        # Mock repository responses
        mock_repos['user_repo'].count.return_value = 150
        mock_repos['user_repo'].count_active.return_value = 45
        mock_repos['presentation_repo'].count.return_value = 567
        mock_repos['template_repo'].count.return_value = 23
        
        # Mock additional metrics
        with patch.object(admin_service, '_calculate_growth_metrics', new_callable=AsyncMock) as mock_growth:
            mock_growth.return_value = {
                "user_growth": 12.5,
                "presentation_growth": 23.4,
                "revenue_growth": 15.8
            }
            
            result = await admin_service.get_dashboard_stats()
        
        assert result['total_users'] == 150
        assert result['active_users'] == 45
        assert result['total_presentations'] == 567
        assert result['total_templates'] == 23
        assert result['growth_metrics']['user_growth'] == 12.5
    
    @pytest.mark.asyncio
    async def test_manage_user_status(self, admin_service, mock_repos):
        """Test user status management (activate/deactivate)."""
        admin_service.user_repository = mock_repos['user_repo']
        
        test_user = TestDataGenerator.generate_user(user_id=10, is_active=True)
        mock_repos['user_repo'].get.return_value = test_user
        
        # Deactivate user
        deactivated_user = {**test_user, "is_active": False}
        mock_repos['user_repo'].update.return_value = deactivated_user
        
        result = await admin_service.update_user_status(
            user_id=10,
            is_active=False,
            reason="Terms violation"
        )
        
        assert result['is_active'] is False
        
        # Verify audit log
        update_call = mock_repos['user_repo'].update.call_args[0]
        assert update_call[1]['is_active'] is False
    
    @pytest.mark.asyncio
    async def test_bulk_user_operations(self, admin_service, mock_repos):
        """Test bulk operations on users."""
        admin_service.user_repository = mock_repos['user_repo']
        
        user_ids = [1, 2, 3, 4, 5]
        
        # Test bulk deactivation
        mock_repos['user_repo'].bulk_update.return_value = 5
        
        result = await admin_service.bulk_update_users(
            user_ids=user_ids,
            updates={"is_active": False}
        )
        
        assert result['updated_count'] == 5
        mock_repos['user_repo'].bulk_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_content_moderation(self, admin_service, mock_repos):
        """Test content moderation capabilities."""
        admin_service.presentation_repository = mock_repos['presentation_repo']
        
        # Mock flagged content
        flagged_presentations = [
            {
                "id": 1,
                "title": "Flagged Content 1",
                "flag_reason": "inappropriate_content",
                "flagged_at": datetime.utcnow()
            },
            {
                "id": 2,
                "title": "Flagged Content 2",
                "flag_reason": "copyright_violation",
                "flagged_at": datetime.utcnow()
            }
        ]
        
        mock_repos['presentation_repo'].get_flagged.return_value = flagged_presentations
        
        result = await admin_service.get_flagged_content(
            content_type="presentation",
            status="pending_review"
        )
        
        assert len(result) == 2
        assert result[0]['flag_reason'] == "inappropriate_content"
    
    @pytest.mark.asyncio
    async def test_system_configuration(self, admin_service):
        """Test system configuration management."""
        # Mock configuration storage
        with patch.object(admin_service, '_get_config', new_callable=AsyncMock) as mock_get:
            with patch.object(admin_service, '_set_config', new_callable=AsyncMock) as mock_set:
                # Get current config
                mock_get.return_value = {
                    "max_file_size_mb": 50,
                    "allowed_file_types": [".pdf", ".docx"],
                    "rate_limits": {
                        "api_calls_per_minute": 60,
                        "generations_per_hour": 10
                    }
                }
                
                current_config = await admin_service.get_system_config()
                assert current_config['max_file_size_mb'] == 50
                
                # Update config
                new_config = {
                    "max_file_size_mb": 100,
                    "rate_limits": {
                        "api_calls_per_minute": 120,
                        "generations_per_hour": 20
                    }
                }
                
                await admin_service.update_system_config(new_config)
                mock_set.assert_called_once_with(new_config)
    
    @pytest.mark.asyncio
    async def test_audit_log_retrieval(self, admin_service, mock_repos):
        """Test audit log retrieval."""
        admin_service.audit_repository = mock_repos['analytics_repo']
        
        # Mock audit logs
        audit_logs = [
            {
                "id": 1,
                "user_id": 1,
                "action": "user.login",
                "details": {"ip": "192.168.1.1"},
                "timestamp": datetime.utcnow()
            },
            {
                "id": 2,
                "user_id": 2,
                "action": "presentation.create",
                "details": {"presentation_id": 123},
                "timestamp": datetime.utcnow() - timedelta(hours=1)
            }
        ]
        
        mock_repos['analytics_repo'].get_audit_logs.return_value = audit_logs
        
        result = await admin_service.get_audit_logs(
            start_date=datetime.utcnow() - timedelta(days=7),
            end_date=datetime.utcnow(),
            user_id=None,
            action_type=None
        )
        
        assert len(result) == 2
        assert result[0]['action'] == "user.login"
    
    @pytest.mark.asyncio
    async def test_generate_admin_report(self, admin_service, mock_repos):
        """Test admin report generation."""
        # Mock report data collection
        with patch.object(admin_service, '_collect_report_data', new_callable=AsyncMock) as mock_collect:
            mock_collect.return_value = {
                "period": "2024-01",
                "user_metrics": {
                    "new_users": 45,
                    "active_users": 234,
                    "churn_rate": 5.2
                },
                "usage_metrics": {
                    "presentations_created": 567,
                    "total_slides": 8901,
                    "exports": {"pptx": 234, "pdf": 123}
                },
                "revenue_metrics": {
                    "total_revenue": 12345.67,
                    "arpu": 52.75,
                    "growth": 15.3
                },
                "performance_metrics": {
                    "uptime": 99.95,
                    "average_response_time": 125,
                    "error_rate": 0.02
                }
            }
            
            result = await admin_service.generate_report(
                report_type="monthly",
                period="2024-01"
            )
        
        assert result['period'] == "2024-01"
        assert result['user_metrics']['new_users'] == 45
        assert result['revenue_metrics']['total_revenue'] == 12345.67
        assert result['performance_metrics']['uptime'] == 99.95
    
    @pytest.mark.asyncio
    async def test_system_health_check(self, admin_service):
        """Test system health monitoring."""
        # Mock health checks
        with patch.object(admin_service, '_check_service_health', new_callable=AsyncMock) as mock_health:
            mock_health.side_effect = [
                {"service": "database", "status": "healthy", "latency": 5},
                {"service": "redis", "status": "healthy", "latency": 2},
                {"service": "s3", "status": "healthy", "latency": 45},
                {"service": "ai_service", "status": "degraded", "latency": 2500}
            ]
            
            result = await admin_service.check_system_health()
        
        assert result['overall_status'] == "degraded"  # One service degraded
        assert len(result['services']) == 4
        assert any(s['service'] == 'ai_service' and s['status'] == 'degraded' 
                  for s in result['services'])
    
    @pytest.mark.asyncio
    async def test_feature_flags_management(self, admin_service):
        """Test feature flags management."""
        # Mock feature flags storage
        with patch.object(admin_service, '_get_feature_flags', new_callable=AsyncMock) as mock_get:
            with patch.object(admin_service, '_set_feature_flag', new_callable=AsyncMock) as mock_set:
                # Get current flags
                mock_get.return_value = {
                    "new_editor": {"enabled": False, "rollout_percentage": 0},
                    "ai_suggestions": {"enabled": True, "rollout_percentage": 100},
                    "beta_exports": {"enabled": True, "rollout_percentage": 25}
                }
                
                flags = await admin_service.get_feature_flags()
                assert flags['new_editor']['enabled'] is False
                assert flags['beta_exports']['rollout_percentage'] == 25
                
                # Update flag
                await admin_service.update_feature_flag(
                    flag_name="new_editor",
                    enabled=True,
                    rollout_percentage=50
                )
                
                mock_set.assert_called_once_with(
                    "new_editor",
                    {"enabled": True, "rollout_percentage": 50}
                )
    
    @pytest.mark.asyncio
    async def test_backup_management(self, admin_service):
        """Test backup creation and management."""
        # Mock backup operations
        with patch.object(admin_service, '_create_backup', new_callable=AsyncMock) as mock_backup:
            with patch.object(admin_service, '_list_backups', new_callable=AsyncMock) as mock_list:
                # Create backup
                mock_backup.return_value = {
                    "backup_id": "backup_20240115_120000",
                    "size_mb": 1234.5,
                    "duration_seconds": 45,
                    "status": "completed"
                }
                
                backup_result = await admin_service.create_backup(
                    backup_type="full",
                    include_user_data=True
                )
                
                assert backup_result['status'] == "completed"
                assert backup_result['size_mb'] == 1234.5
                
                # List backups
                mock_list.return_value = [
                    {
                        "backup_id": "backup_20240115_120000",
                        "created_at": datetime.utcnow(),
                        "size_mb": 1234.5,
                        "type": "full"
                    },
                    {
                        "backup_id": "backup_20240114_120000",
                        "created_at": datetime.utcnow() - timedelta(days=1),
                        "size_mb": 1189.2,
                        "type": "full"
                    }
                ]
                
                backups = await admin_service.list_backups(limit=10)
                assert len(backups) == 2
                assert backups[0]['backup_id'] == "backup_20240115_120000"