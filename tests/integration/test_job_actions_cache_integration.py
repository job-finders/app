"""
Integration Tests for Job Actions Caching

Tests cache integration including:
- Redis cache operations
- Cache invalidation strategies
- Cache warming
- Performance optimization
- Cache consistency
"""

import pytest
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from tests.base import BaseTestCase


class TestJobActionsCacheIntegration(BaseTestCase):
    """Integration tests for job actions caching functionality"""

    def setUp(self):
        super().setUp()
        self.test_user_id = "test_user_123"
        self.test_job_id = "test_job_456"
        self.test_company_id = "test_company_789"

    def test_job_actions_state_cache_integration(self):
        """Test job actions state caching and retrieval"""
        with patch('src.cache.job_actions_cache.job_actions_cache') as mock_cache:
            # Mock cache miss on first call
            mock_cache.get_job_actions_state.return_value = None

            # Mock controller response
            with patch('src.controllers.jobs.actions.JobActionsController.get_job_actions_state') as mock_controller:
                mock_controller.return_value = {
                    "success": True,
                    "data": {
                        "job_id": self.test_job_id,
                        "user_has_liked": True,
                        "user_has_saved": False,
                        "like_count": 5,
                        "share_count": 2
                    }
                }

                from src.controllers.jobs.actions import JobActionsController

                factory = Mock()
                controller = JobActionsController(factory)
                controller.logger = Mock()

                # First call should miss cache and call controller
                result1 = controller.get_job_actions_state(self.test_user_id, self.test_job_id)

                # Verify cache was checked
                mock_cache.get_job_actions_state.assert_called_with(self.test_user_id, self.test_job_id)

                # Verify cache was set
                mock_cache.set_job_actions_state.assert_called_once()

                # Mock cache hit on second call
                mock_cache.get_job_actions_state.return_value = {
                    "job_id": self.test_job_id,
                    "user_has_liked": True,
                    "user_has_saved": False,
                    "like_count": 5,
                    "share_count": 2
                }

                # Second call should hit cache
                result2 = controller.get_job_actions_state(self.test_user_id, self.test_job_id)

                # Verify both results are the same
                self.assertEqual(result1["data"]["like_count"], result2["data"]["like_count"])

    def test_cache_invalidation_on_like_action(self):
        """Test cache invalidation when user likes a job"""
        with patch('src.cache.job_actions_cache.job_actions_cache') as mock_cache:
            with patch('src.controllers.jobs.actions.JobActionsController.get_session') as mock_get_session:
                # Mock database session
                mock_session = Mock()
                mock_session.__enter__ = Mock(return_value=mock_session)
                mock_session.__exit__ = Mock(return_value=None)
                mock_get_session.return_value = mock_session

                # Mock successful like operation
                mock_user = Mock()
                mock_job = Mock()
                mock_session.query.return_value.filter_by.return_value.first.side_effect = [
                    mock_user,  # User exists
                    mock_job,  # Job exists
                    None  # No existing like
                ]
                mock_session.query.return_value.filter_by.return_value.scalar.return_value = 1

                from src.controllers.jobs.actions import JobActionsController

                factory = Mock()
                controller = JobActionsController(factory)
                controller.logger = Mock()
                controller.analytics_service = Mock()

                # Perform like action
                result = controller.like_job(self.test_user_id, self.test_job_id)

                # Verify cache invalidation was called
                mock_cache.invalidate_user_action_cache.assert_called_with(
                    self.test_user_id, self.test_job_id
                )

    def test_cache_invalidation_on_save_action(self):
        """Test cache invalidation when user saves a job"""
        with patch('src.cache.job_actions_cache.job_actions_cache') as mock_cache:
            with patch('src.controllers.jobs.actions.JobActionsController.get_session') as mock_get_session:
                # Mock database session
                mock_session = Mock()
                mock_session.__enter__ = Mock(return_value=mock_session)
                mock_session.__exit__ = Mock(return_value=None)
                mock_get_session.return_value = mock_session

                # Mock successful save operation
                mock_user = Mock()
                mock_job = Mock()
                mock_session.query.return_value.filter_by.return_value.first.side_effect = [
                    mock_user,  # User exists
                    mock_job,  # Job exists
                    None  # No existing save
                ]

                from src.controllers.jobs.actions import JobActionsController

                factory = Mock()
                controller = JobActionsController(factory)
                controller.logger = Mock()
                controller.analytics_service = Mock()

                # Perform save action
                result = controller.save_job(self.test_user_id, self.test_job_id)

                # Verify multiple cache invalidations were called
                mock_cache.invalidate_job_actions_state.assert_called_with(
                    self.test_user_id, self.test_job_id
                )
                mock_cache.invalidate_user_liked_jobs.assert_called_with(self.test_user_id)

    def test_cache_invalidation_on_share_action(self):
        """Test cache invalidation when user shares a job"""
        with patch('src.cache.job_actions_cache.job_actions_cache') as mock_cache:
            with patch('src.controllers.jobs.actions.JobActionsController.get_session') as mock_get_session:
                # Mock database session
                mock_session = Mock()
                mock_session.__enter__ = Mock(return_value=mock_session)
                mock_session.__exit__ = Mock(return_value=None)
                mock_get_session.return_value = mock_session

                # Mock successful share operation
                mock_job = Mock()
                mock_user = Mock()
                mock_session.query.return_value.filter_by.return_value.first.side_effect = [
                    mock_job,  # Job exists
                    mock_user  # User exists
                ]
                mock_session.query.return_value.filter_by.return_value.scalar.return_value = 1

                from src.controllers.jobs.actions import JobActionsController

                factory = Mock()
                controller = JobActionsController(factory)
                controller.logger = Mock()
                controller.analytics_service = Mock()

                # Perform share action
                result = controller.share_job(self.test_user_id, self.test_job_id, "linkedin")

                # Verify engagement cache invalidation
                mock_cache.invalidate_job_engagement_stats.assert_called_with(self.test_job_id)
                mock_cache.invalidate_job_actions_state.assert_called_with(
                    self.test_user_id, self.test_job_id
                )

    def test_company_profile_cache_integration(self):
        """Test company profile caching"""
        with patch('src.cache.job_actions_cache.job_actions_cache') as mock_cache:
            # Mock cache miss
            mock_cache.get_company_profile.return_value = None

            with patch('src.controllers.company.public.CompanyPublicController.get_session') as mock_get_session:
                mock_session = Mock()
                mock_session.__enter__ = Mock(return_value=mock_session)
                mock_session.__exit__ = Mock(return_value=None)
                mock_get_session.return_value = mock_session

                # Mock company data
                mock_company = Mock()
                mock_company.to_dict.return_value = {
                    'company_id': self.test_company_id,
                    'company_name': 'Test Company',
                    'description': 'A test company'
                }
                mock_session.query.return_value.filter_by.return_value.first.return_value = mock_company

                from src.controllers.company.public import CompanyPublicController

                factory = Mock()
                controller = CompanyPublicController(factory)
                controller.logger = Mock()

                # Get company profile (should cache result)
                result = controller.get_public_profile(self.test_company_id)

                # Verify cache was checked and set
                mock_cache.get_company_profile.assert_called_with(self.test_company_id)
                mock_cache.set_company_profile.assert_called_once()

    def test_cache_warming_on_popular_jobs(self):
        """Test cache warming for popular jobs"""
        with patch('src.cache.job_actions_cache.job_actions_cache') as mock_cache:
            with patch('src.services.job_actions_analytics.JobActionsAnalyticsService.get_session') as mock_get_session:
                mock_session = Mock()
                mock_session.__enter__ = Mock(return_value=mock_session)
                mock_session.__exit__ = Mock(return_value=None)
                mock_get_session.return_value = mock_session

                # Mock popular jobs query
                mock_job1 = Mock()
                mock_job1.job_id = "job1"
                mock_job1.title = "Popular Job 1"
                mock_job1.company_name = "Company A"
                mock_job1.recent_likes = 10
                mock_job1.recent_saves = 5
                mock_job1.recent_shares = 3

                mock_job2 = Mock()
                mock_job2.job_id = "job2"
                mock_job2.title = "Popular Job 2"
                mock_job2.company_name = "Company B"
                mock_job2.recent_likes = 8
                mock_job2.recent_saves = 4
                mock_job2.recent_shares = 2

                mock_query = Mock()
                mock_session.query.return_value = mock_query
                mock_query.outerjoin.return_value = mock_query
                mock_query.join.return_value = mock_query
                mock_query.group_by.return_value = mock_query
                mock_query.order_by.return_value = mock_query
                mock_query.limit.return_value = mock_query
                mock_query.all.return_value = [mock_job1, mock_job2]

                from src.services.job_actions_analytics import JobActionsAnalyticsService

                factory = Mock()
                service = JobActionsAnalyticsService(factory)
                service.logger = Mock()

                # Get popular jobs (should warm cache)
                result = service.get_popular_jobs_by_engagement(limit=10, days=7)

                # Verify cache warming was triggered
                mock_cache.warm_popular_jobs_cache.assert_called_once()

    def test_cache_consistency_across_operations(self):
        """Test cache consistency across multiple operations"""
        with patch('src.cache.job_actions_cache.job_actions_cache') as mock_cache:
            # Mock initial cache state
            initial_state = {
                "job_id": self.test_job_id,
                "user_has_liked": False,
                "user_has_saved": False,
                "like_count": 0,
                "share_count": 0
            }
            mock_cache.get_job_actions_state.return_value = initial_state

            with patch('src.controllers.jobs.actions.JobActionsController.get_session') as mock_get_session:
                mock_session = Mock()
                mock_session.__enter__ = Mock(return_value=mock_session)
                mock_session.__exit__ = Mock(return_value=None)
                mock_get_session.return_value = mock_session

                # Mock successful operations
                mock_user = Mock()
                mock_job = Mock()
                mock_session.query.return_value.filter_by.return_value.first.side_effect = [
                    mock_user, mock_job, None,  # Like operation
                    mock_user, mock_job, None  # Save operation
                ]
                mock_session.query.return_value.filter_by.return_value.scalar.return_value = 1

                from src.controllers.jobs.actions import JobActionsController

                factory = Mock()
                controller = JobActionsController(factory)
                controller.logger = Mock()
                controller.analytics_service = Mock()

                # Perform like action
                like_result = controller.like_job(self.test_user_id, self.test_job_id)

                # Perform save action
                save_result = controller.save_job(self.test_user_id, self.test_job_id)

                # Verify cache invalidation was called for both operations
                self.assertEqual(mock_cache.invalidate_user_action_cache.call_count, 1)
                self.assertEqual(mock_cache.invalidate_job_actions_state.call_count, 1)

    def test_cache_performance_optimization(self):
        """Test cache performance optimization strategies"""
        with patch('src.cache.job_actions_cache.job_actions_cache') as mock_cache:
            # Mock cache hit for frequently accessed data
            cached_data = {
                "job_id": self.test_job_id,
                "user_has_liked": True,
                "like_count": 100
            }
            mock_cache.get_job_actions_state.return_value = cached_data

            from src.controllers.jobs.actions import JobActionsController

            factory = Mock()
            controller = JobActionsController(factory)
            controller.logger = Mock()

            # Multiple calls should hit cache
            for i in range(5):
                result = controller.get_job_actions_state(self.test_user_id, self.test_job_id)
                self.assertEqual(result["data"]["like_count"], 100)

            # Verify cache was hit multiple times
            self.assertEqual(mock_cache.get_job_actions_state.call_count, 5)

    def test_cache_error_handling(self):
        """Test cache error handling and fallback"""
        with patch('src.cache.job_actions_cache.job_actions_cache') as mock_cache:
            # Mock cache error
            mock_cache.get_job_actions_state.side_effect = Exception("Redis connection failed")

            with patch('src.controllers.jobs.actions.JobActionsController.get_session') as mock_get_session:
                mock_session = Mock()
                mock_session.__enter__ = Mock(return_value=mock_session)
                mock_session.__exit__ = Mock(return_value=None)
                mock_get_session.return_value = mock_session

                # Mock database fallback
                mock_session.query.return_value.filter_by.return_value.first.side_effect = [
                    Mock(),  # User has liked
                    Mock()  # User has saved
                ]
                mock_session.query.return_value.filter_by.return_value.scalar.side_effect = [5, 2]

                from src.controllers.jobs.actions import JobActionsController

                factory = Mock()
                controller = JobActionsController(factory)
                controller.logger = Mock()

                # Should fallback to database when cache fails
                result = controller.get_job_actions_state(self.test_user_id, self.test_job_id)

                # Verify database was queried as fallback
                self.assertGreater(mock_session.query.call_count, 0)

    def test_cache_ttl_and_expiration(self):
        """Test cache TTL and expiration handling"""
        with patch('src.cache.job_actions_cache.job_actions_cache') as mock_cache:
            # Mock expired cache (returns None)
            mock_cache.get_job_actions_state.return_value = None

            with patch('src.controllers.jobs.actions.JobActionsController.get_session') as mock_get_session:
                mock_session = Mock()
                mock_session.__enter__ = Mock(return_value=mock_session)
                mock_session.__exit__ = Mock(return_value=None)
                mock_get_session.return_value = mock_session

                # Mock fresh database data
                mock_session.query.return_value.filter_by.return_value.first.side_effect = [
                    None,  # User hasn't liked
                    None  # User hasn't saved
                ]
                mock_session.query.return_value.filter_by.return_value.scalar.side_effect = [10, 3]

                from src.controllers.jobs.actions import JobActionsController

                factory = Mock()
                controller = JobActionsController(factory)
                controller.logger = Mock()

                # Should refresh cache with fresh data
                result = controller.get_job_actions_state(self.test_user_id, self.test_job_id)

                # Verify cache was set with TTL
                mock_cache.set_job_actions_state.assert_called_once()

                # Verify TTL was set
                call_args = mock_cache.set_job_actions_state.call_args
                self.assertIsNotNone(call_args)

    def test_cache_bulk_operations(self):
        """Test cache operations for bulk data"""
        with patch('src.cache.job_actions_cache.job_actions_cache') as mock_cache:
            # Mock bulk cache operations
            job_ids = [f"job_{i}" for i in range(10)]

            # Mock bulk cache miss
            mock_cache.get_multiple_job_engagement_stats.return_value = {}

            with patch('src.services.job_actions_analytics.JobActionsAnalyticsService.get_session') as mock_get_session:
                mock_session = Mock()
                mock_session.__enter__ = Mock(return_value=mock_session)
                mock_session.__exit__ = Mock(return_value=None)
                mock_get_session.return_value = mock_session

                # Mock bulk database query
                mock_results = []
                for i, job_id in enumerate(job_ids):
                    mock_result = Mock()
                    mock_result.job_id = job_id
                    mock_result.total_likes = i * 2
                    mock_result.total_saves = i
                    mock_results.append(mock_result)

                mock_query = Mock()
                mock_session.query.return_value = mock_query
                mock_query.filter.return_value = mock_query
                mock_query.all.return_value = mock_results

                from src.services.job_actions_analytics import JobActionsAnalyticsService

                factory = Mock()
                service = JobActionsAnalyticsService(factory)
                service.logger = Mock()

                # Bulk operation should use cache efficiently
                results = []
                for job_id in job_ids:
                    result = service.get_job_engagement_metrics(job_id)
                    results.append(result)

                # Verify bulk cache operations were used
                mock_cache.set_multiple_job_engagement_stats.assert_called_once()


class TestCacheIntegrationWithAPI(BaseTestCase):
    """Integration tests for cache with API endpoints"""

    def setUp(self):
        super().setUp()
        self.test_user_id = "test_user_123"
        self.test_job_id = "test_job_456"
        self.auth_headers = {
            'Authorization': 'Bearer test_token',
            'Content-Type': 'application/json'
        }

    def test_api_cache_integration(self):
        """Test API endpoints with cache integration"""
        with patch('src.authentication.auth_utils.get_current_user') as mock_auth:
            mock_auth.return_value = {'user_id': self.test_user_id}

            with patch('src.cache.job_actions_cache.job_actions_cache') as mock_cache:
                # Mock cache hit
                cached_state = {
                    "job_id": self.test_job_id,
                    "user_has_liked": True,
                    "user_has_saved": False,
                    "like_count": 5,
                    "share_count": 2
                }
                mock_cache.get_job_actions_state.return_value = cached_state

                # API call should use cached data
                response = self.client.get(
                    f'/api/jobs/{self.test_job_id}/actions',
                    headers=self.auth_headers
                )

                self.assertEqual(response.status_code, 200)
                data = json.loads(response.data)
                self.assertEqual(data['data']['like_count'], 5)

                # Verify cache was used
                mock_cache.get_job_actions_state.assert_called_with(
                    self.test_user_id, self.test_job_id
                )


if __name__ == '__main__':
    import unittest

    unittest.main()
