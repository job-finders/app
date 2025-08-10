"""
Integration Tests for Job Actions API Endpoints

Tests complete API workflows including:
- Authentication flows
- Database operations
- Cache integration
- Error handling
- End-to-end user scenarios
"""

import pytest
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from tests.base import BaseTestCase
from src.database.models import JobLike, JobShare, SavedJob, ShareMethodEnum


class TestJobActionsAPIIntegration(BaseTestCase):
    """Integration tests for job actions API endpoints"""

    def setUp(self):
        super().setUp()
        self.test_user_id = "test_user_123"
        self.test_job_id = "test_job_456"
        self.test_company_id = "test_company_789"

        # Mock authentication
        self.auth_headers = {
            'Authorization': 'Bearer test_token',
            'Content-Type': 'application/json'
        }

    def test_complete_like_workflow(self):
        """Test complete like -> unlike workflow"""
        # Mock authentication
        with patch('src.authentication.auth_utils.get_current_user') as mock_auth:
            mock_auth.return_value = {'user_id': self.test_user_id}

            # Mock database operations
            with patch('src.controllers.jobs.actions.JobActionsController.like_job') as mock_like:
                mock_like.return_value = {
                    "success": True,
                    "message": "Job liked successfully",
                    "data": {"like_id": str(uuid.uuid4()), "like_count": 1}
                }

                # Test like endpoint
                response = self.client.post(
                    f'/api/jobs/{self.test_job_id}/like',
                    headers=self.auth_headers
                )

                self.assertEqual(response.status_code, 200)
                data = json.loads(response.data)
                self.assertTrue(data['success'])
                self.assertIn('like_id', data['data'])

            # Mock unlike operation
            with patch('src.controllers.jobs.actions.JobActionsController.unlike_job') as mock_unlike:
                mock_unlike.return_value = {
                    "success": True,
                    "message": "Job unliked successfully",
                    "data": {"like_count": 0}
                }

                # Test unlike endpoint
                response = self.client.delete(
                    f'/api/jobs/{self.test_job_id}/like',
                    headers=self.auth_headers
                )

                self.assertEqual(response.status_code, 200)
                data = json.loads(response.data)
                self.assertTrue(data['success'])
                self.assertEqual(data['data']['like_count'], 0)

    def test_complete_save_workflow(self):
        """Test complete save -> unsave workflow"""
        with patch('src.authentication.auth_utils.get_current_user') as mock_auth:
            mock_auth.return_value = {'user_id': self.test_user_id}

            # Mock save operation
            with patch('src.controllers.jobs.actions.JobActionsController.save_job') as mock_save:
                mock_save.return_value = {
                    "success": True,
                    "message": "Job saved successfully",
                    "data": {"saved_job_id": str(uuid.uuid4())}
                }

                # Test save endpoint
                response = self.client.post(
                    f'/api/jobs/{self.test_job_id}/save',
                    headers=self.auth_headers
                )

                self.assertEqual(response.status_code, 200)
                data = json.loads(response.data)
                self.assertTrue(data['success'])
                self.assertIn('saved_job_id', data['data'])

            # Mock unsave operation
            with patch('src.controllers.jobs.actions.JobActionsController.unsave_job') as mock_unsave:
                mock_unsave.return_value = {
                    "success": True,
                    "message": "Job unsaved successfully"
                }

                # Test unsave endpoint
                response = self.client.delete(
                    f'/api/jobs/{self.test_job_id}/save',
                    headers=self.auth_headers
                )

                self.assertEqual(response.status_code, 200)
                data = json.loads(response.data)
                self.assertTrue(data['success'])

    def test_share_job_authenticated(self):
        """Test job sharing with authenticated user"""
        with patch('src.authentication.auth_utils.get_current_user') as mock_auth:
            mock_auth.return_value = {'user_id': self.test_user_id}

            with patch('src.controllers.jobs.actions.JobActionsController.share_job') as mock_share:
                mock_share.return_value = {
                    "success": True,
                    "message": "Job shared successfully",
                    "data": {
                        "share_id": str(uuid.uuid4()),
                        "referral_code": "REF123",
                        "share_count": 1
                    }
                }

                # Test share endpoint
                share_data = {"share_method": "linkedin"}
                response = self.client.post(
                    f'/api/jobs/{self.test_job_id}/share',
                    headers=self.auth_headers,
                    data=json.dumps(share_data)
                )

                self.assertEqual(response.status_code, 200)
                data = json.loads(response.data)
                self.assertTrue(data['success'])
                self.assertIn('referral_code', data['data'])

    def test_share_job_anonymous(self):
        """Test job sharing without authentication"""
        with patch('src.controllers.jobs.actions.JobActionsController.share_job') as mock_share:
            mock_share.return_value = {
                "success": True,
                "message": "Job shared successfully",
                "data": {
                    "share_id": str(uuid.uuid4()),
                    "referral_code": None,
                    "share_count": 1
                }
            }

            # Test anonymous share
            share_data = {"share_method": "email"}
            response = self.client.post(
                f'/api/jobs/{self.test_job_id}/share',
                data=json.dumps(share_data),
                content_type='application/json'
            )

            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertTrue(data['success'])
            self.assertIsNone(data['data']['referral_code'])

    def test_get_job_actions_state(self):
        """Test retrieving job actions state"""
        with patch('src.authentication.auth_utils.get_current_user') as mock_auth:
            mock_auth.return_value = {'user_id': self.test_user_id}

            with patch('src.controllers.jobs.actions.JobActionsController.get_job_actions_state') as mock_state:
                mock_state.return_value = {
                    "success": True,
                    "data": {
                        "job_id": self.test_job_id,
                        "user_has_liked": True,
                        "user_has_saved": False,
                        "like_count": 5,
                        "share_count": 2
                    }
                }

                # Test state endpoint
                response = self.client.get(
                    f'/api/jobs/{self.test_job_id}/actions',
                    headers=self.auth_headers
                )

                self.assertEqual(response.status_code, 200)
                data = json.loads(response.data)
                self.assertTrue(data['success'])
                self.assertTrue(data['data']['user_has_liked'])
                self.assertFalse(data['data']['user_has_saved'])

    def test_authentication_required_endpoints(self):
        """Test that protected endpoints require authentication"""
        # Test like endpoint without auth
        response = self.client.post(f'/api/jobs/{self.test_job_id}/like')
        self.assertEqual(response.status_code, 401)

        # Test save endpoint without auth
        response = self.client.post(f'/api/jobs/{self.test_job_id}/save')
        self.assertEqual(response.status_code, 401)

        # Test actions state without auth
        response = self.client.get(f'/api/jobs/{self.test_job_id}/actions')
        self.assertEqual(response.status_code, 401)

    def test_invalid_job_id_handling(self):
        """Test handling of invalid job IDs"""
        with patch('src.authentication.auth_utils.get_current_user') as mock_auth:
            mock_auth.return_value = {'user_id': self.test_user_id}

            with patch('src.controllers.jobs.actions.JobActionsController.like_job') as mock_like:
                mock_like.return_value = {
                    "success": False,
                    "message": "Job not found",
                    "code": 404
                }

                # Test with invalid job ID
                response = self.client.post(
                    '/api/jobs/invalid_job_id/like',
                    headers=self.auth_headers
                )

                self.assertEqual(response.status_code, 404)
                data = json.loads(response.data)
                self.assertFalse(data['success'])

    def test_rate_limiting_integration(self):
        """Test rate limiting on job actions"""
        with patch('src.authentication.auth_utils.get_current_user') as mock_auth:
            mock_auth.return_value = {'user_id': self.test_user_id}

            with patch(
                    'src.firewall.job_actions_security.job_actions_rate_limiter.check_rate_limit') as mock_rate_limit:
                # Mock rate limit exceeded
                mock_rate_limit.return_value = {
                    "allowed": False,
                    "message": "Rate limit exceeded"
                }

                # Test rate limited request
                response = self.client.post(
                    f'/api/jobs/{self.test_job_id}/like',
                    headers=self.auth_headers
                )

                self.assertEqual(response.status_code, 429)

    def test_error_handling_integration(self):
        """Test error handling across the API"""
        with patch('src.authentication.auth_utils.get_current_user') as mock_auth:
            mock_auth.return_value = {'user_id': self.test_user_id}

            # Test database error
            with patch('src.controllers.jobs.actions.JobActionsController.like_job') as mock_like:
                mock_like.return_value = {
                    "success": False,
                    "message": "Internal server error",
                    "code": 500
                }

                response = self.client.post(
                    f'/api/jobs/{self.test_job_id}/like',
                    headers=self.auth_headers
                )

                self.assertEqual(response.status_code, 500)
                data = json.loads(response.data)
                self.assertFalse(data['success'])
                self.assertIn('error', data['message'].lower())


class TestCompanyPublicAPIIntegration(BaseTestCase):
    """Integration tests for company public profile API endpoints"""

    def setUp(self):
        super().setUp()
        self.test_company_id = "test_company_789"

    def test_get_company_public_profile(self):
        """Test retrieving company public profile"""
        with patch('src.controllers.company.public.CompanyPublicController.get_public_profile') as mock_profile:
            mock_profile.return_value = {
                'company_id': self.test_company_id,
                'company_name': 'Test Company',
                'description': 'A test company',
                'industry': 'Technology',
                'location': 'Cape Town',
                'is_verified': True
            }

            response = self.client.get(f'/company/{self.test_company_id}')

            self.assertEqual(response.status_code, 200)
            # Check that company data is in response
            self.assertIn(b'Test Company', response.data)

    def test_get_company_jobs(self):
        """Test retrieving company job listings"""
        with patch('src.controllers.company.public.CompanyPublicController.get_company_active_jobs') as mock_jobs:
            mock_jobs.return_value = [
                {
                    'job_id': 'job1',
                    'title': 'Software Engineer',
                    'description': 'Great opportunity',
                    'location': 'Cape Town'
                },
                {
                    'job_id': 'job2',
                    'title': 'Data Scientist',
                    'description': 'Exciting role',
                    'location': 'Johannesburg'
                }
            ]

            response = self.client.get(f'/company/{self.test_company_id}/jobs')

            self.assertEqual(response.status_code, 200)
            # Check that job data is in response
            self.assertIn(b'Software Engineer', response.data)
            self.assertIn(b'Data Scientist', response.data)

    def test_company_not_found(self):
        """Test handling of non-existent company"""
        with patch('src.controllers.company.public.CompanyPublicController.get_public_profile') as mock_profile:
            mock_profile.return_value = None

            response = self.client.get('/company/nonexistent_company')

            self.assertEqual(response.status_code, 404)


class TestAnalyticsAPIIntegration(BaseTestCase):
    """Integration tests for analytics API endpoints"""

    def setUp(self):
        super().setUp()
        self.test_company_id = "test_company_789"
        self.test_job_id = "test_job_456"
        self.auth_headers = {
            'Authorization': 'Bearer test_token',
            'Content-Type': 'application/json'
        }

    def test_get_job_engagement_metrics(self):
        """Test retrieving job engagement metrics"""
        with patch(
                'src.services.job_actions_analytics.JobActionsAnalyticsService.get_job_engagement_metrics') as mock_metrics:
            mock_metrics.return_value = {
                'job_id': self.test_job_id,
                'total_likes': 10,
                'total_saves': 5,
                'total_shares': 3,
                'engagement_rate': 18.0,
                'save_to_apply_rate': 40.0
            }

            response = self.client.get(f'/api/jobs/{self.test_job_id}/engagement')

            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertTrue(data['success'])
            self.assertEqual(data['data']['total_likes'], 10)

    def test_get_popular_jobs(self):
        """Test retrieving popular jobs by engagement"""
        with patch(
                'src.services.job_actions_analytics.JobActionsAnalyticsService.get_popular_jobs_by_engagement') as mock_popular:
            mock_popular.return_value = [
                {
                    'job_id': 'job1',
                    'title': 'Popular Job 1',
                    'company_name': 'Company A',
                    'total_recent_engagement': 25
                },
                {
                    'job_id': 'job2',
                    'title': 'Popular Job 2',
                    'company_name': 'Company B',
                    'total_recent_engagement': 20
                }
            ]

            response = self.client.get('/api/jobs/popular?limit=10&days=7')

            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertTrue(data['success'])
            self.assertEqual(len(data['data']['jobs']), 2)

    def test_get_company_engagement_stats(self):
        """Test retrieving company engagement statistics"""
        with patch('src.authentication.auth_utils.get_current_user') as mock_auth:
            mock_auth.return_value = {'user_id': 'test_user'}

            with patch(
                    'src.services.job_actions_analytics.JobActionsAnalyticsService.get_company_engagement_stats') as mock_stats:
                mock_stats.return_value = {
                    'company_id': self.test_company_id,
                    'total_job_likes': 50,
                    'total_job_saves': 30,
                    'total_job_shares': 20,
                    'average_engagement_per_job': 10.0,
                    'engagement_growth_rate': 15.5
                }

                response = self.client.get(
                    f'/api/company/{self.test_company_id}/engagement',
                    headers=self.auth_headers
                )

                self.assertEqual(response.status_code, 200)
                data = json.loads(response.data)
                self.assertTrue(data['success'])
                self.assertEqual(data['data']['total_job_likes'], 50)

    def test_analytics_authentication_required(self):
        """Test that analytics endpoints require authentication"""
        # Test company engagement without auth
        response = self.client.get(f'/api/company/{self.test_company_id}/engagement')
        self.assertEqual(response.status_code, 401)

        # Test analytics report without auth
        response = self.client.get(f'/api/company/{self.test_company_id}/analytics-report')
        self.assertEqual(response.status_code, 401)


class TestCacheIntegration(BaseTestCase):
    """Integration tests for caching functionality"""

    def setUp(self):
        super().setUp()
        self.test_user_id = "test_user_123"
        self.test_job_id = "test_job_456"

    def test_job_actions_state_caching(self):
        """Test caching of job actions state"""
        with patch('src.cache.job_actions_cache.job_actions_cache') as mock_cache:
            # Mock cache miss, then hit
            mock_cache.get_job_actions_state.side_effect = [None, {
                'job_id': self.test_job_id,
                'user_has_liked': True,
                'like_count': 5
            }]

            with patch('src.controllers.jobs.actions.JobActionsController.get_job_actions_state') as mock_controller:
                mock_controller.return_value = {
                    "success": True,
                    "data": {
                        'job_id': self.test_job_id,
                        'user_has_liked': True,
                        'like_count': 5
                    }
                }

                # First call should miss cache and call controller
                response1 = self.client.get(f'/api/jobs/{self.test_job_id}/actions')

                # Second call should hit cache
                response2 = self.client.get(f'/api/jobs/{self.test_job_id}/actions')

                # Both should return same data
                self.assertEqual(response1.status_code, 200)
                self.assertEqual(response2.status_code, 200)

    def test_cache_invalidation_on_actions(self):
        """Test cache invalidation when user performs actions"""
        with patch('src.cache.job_actions_cache.job_actions_cache') as mock_cache:
            with patch('src.controllers.jobs.actions.JobActionsController.like_job') as mock_like:
                mock_like.return_value = {
                    "success": True,
                    "message": "Job liked successfully",
                    "data": {"like_id": str(uuid.uuid4()), "like_count": 1}
                }

                # Perform like action
                response = self.client.post(f'/api/jobs/{self.test_job_id}/like')

                # Verify cache invalidation was called
                mock_cache.invalidate_user_action_cache.assert_called()


class TestDatabaseIntegration(BaseTestCase):
    """Integration tests for database operations"""

    def setUp(self):
        super().setUp()
        self.test_user_id = "test_user_123"
        self.test_job_id = "test_job_456"

    def test_database_transaction_rollback(self):
        """Test database transaction rollback on errors"""
        with patch('src.controllers.jobs.actions.JobActionsController.get_session') as mock_session:
            # Mock session that raises exception on commit
            mock_db_session = Mock()
            mock_db_session.__enter__ = Mock(return_value=mock_db_session)
            mock_db_session.__exit__ = Mock(return_value=None)
            mock_db_session.commit.side_effect = Exception("Database error")

            mock_session.return_value = mock_db_session

            with patch('src.controllers.jobs.actions.JobActionsController.like_job') as mock_like:
                mock_like.return_value = {
                    "success": False,
                    "message": "Internal server error",
                    "code": 500
                }

                response = self.client.post(f'/api/jobs/{self.test_job_id}/like')

                # Should handle error gracefully
                self.assertEqual(response.status_code, 500)
                # Verify rollback was called
                mock_db_session.rollback.assert_called()

    def test_database_constraint_violations(self):
        """Test handling of database constraint violations"""
        with patch('src.controllers.jobs.actions.JobActionsController.like_job') as mock_like:
            # Mock duplicate key error
            mock_like.return_value = {
                "success": False,
                "message": "Job already liked",
                "code": 409
            }

            response = self.client.post(f'/api/jobs/{self.test_job_id}/like')

            self.assertEqual(response.status_code, 409)
            data = json.loads(response.data)
            self.assertFalse(data['success'])


class TestEndToEndWorkflows(BaseTestCase):
    """End-to-end integration tests for complete user workflows"""

    def setUp(self):
        super().setUp()
        self.test_user_id = "test_user_123"
        self.test_job_id = "test_job_456"
        self.test_company_id = "test_company_789"
        self.auth_headers = {
            'Authorization': 'Bearer test_token',
            'Content-Type': 'application/json'
        }

    def test_complete_job_engagement_workflow(self):
        """Test complete user engagement workflow"""
        with patch('src.authentication.auth_utils.get_current_user') as mock_auth:
            mock_auth.return_value = {'user_id': self.test_user_id}

            # Step 1: View job actions state (empty)
            with patch('src.controllers.jobs.actions.JobActionsController.get_job_actions_state') as mock_state:
                mock_state.return_value = {
                    "success": True,
                    "data": {
                        "job_id": self.test_job_id,
                        "user_has_liked": False,
                        "user_has_saved": False,
                        "like_count": 0,
                        "share_count": 0
                    }
                }

                response = self.client.get(
                    f'/api/jobs/{self.test_job_id}/actions',
                    headers=self.auth_headers
                )

                self.assertEqual(response.status_code, 200)
                data = json.loads(response.data)
                self.assertFalse(data['data']['user_has_liked'])
                self.assertFalse(data['data']['user_has_saved'])

            # Step 2: Like the job
            with patch('src.controllers.jobs.actions.JobActionsController.like_job') as mock_like:
                mock_like.return_value = {
                    "success": True,
                    "message": "Job liked successfully",
                    "data": {"like_id": str(uuid.uuid4()), "like_count": 1}
                }

                response = self.client.post(
                    f'/api/jobs/{self.test_job_id}/like',
                    headers=self.auth_headers
                )

                self.assertEqual(response.status_code, 200)
                data = json.loads(response.data)
                self.assertTrue(data['success'])

            # Step 3: Save the job
            with patch('src.controllers.jobs.actions.JobActionsController.save_job') as mock_save:
                mock_save.return_value = {
                    "success": True,
                    "message": "Job saved successfully",
                    "data": {"saved_job_id": str(uuid.uuid4())}
                }

                response = self.client.post(
                    f'/api/jobs/{self.test_job_id}/save',
                    headers=self.auth_headers
                )

                self.assertEqual(response.status_code, 200)
                data = json.loads(response.data)
                self.assertTrue(data['success'])

            # Step 4: Share the job
            with patch('src.controllers.jobs.actions.JobActionsController.share_job') as mock_share:
                mock_share.return_value = {
                    "success": True,
                    "message": "Job shared successfully",
                    "data": {
                        "share_id": str(uuid.uuid4()),
                        "referral_code": "REF123",
                        "share_count": 1
                    }
                }

                share_data = {"share_method": "linkedin"}
                response = self.client.post(
                    f'/api/jobs/{self.test_job_id}/share',
                    headers=self.auth_headers,
                    data=json.dumps(share_data)
                )

                self.assertEqual(response.status_code, 200)
                data = json.loads(response.data)
                self.assertTrue(data['success'])

            # Step 5: Check final state
            with patch('src.controllers.jobs.actions.JobActionsController.get_job_actions_state') as mock_final_state:
                mock_final_state.return_value = {
                    "success": True,
                    "data": {
                        "job_id": self.test_job_id,
                        "user_has_liked": True,
                        "user_has_saved": True,
                        "like_count": 1,
                        "share_count": 1
                    }
                }

                response = self.client.get(
                    f'/api/jobs/{self.test_job_id}/actions',
                    headers=self.auth_headers
                )

                self.assertEqual(response.status_code, 200)
                data = json.loads(response.data)
                self.assertTrue(data['data']['user_has_liked'])
                self.assertTrue(data['data']['user_has_saved'])

    def test_company_profile_to_job_engagement_workflow(self):
        """Test workflow from company profile to job engagement"""
        # Step 1: View company profile
        with patch('src.controllers.company.public.CompanyPublicController.get_public_profile') as mock_profile:
            mock_profile.return_value = {
                'company_id': self.test_company_id,
                'company_name': 'Test Company',
                'description': 'A great company'
            }

            response = self.client.get(f'/company/{self.test_company_id}')
            self.assertEqual(response.status_code, 200)

        # Step 2: View company jobs
        with patch('src.controllers.company.public.CompanyPublicController.get_company_active_jobs') as mock_jobs:
            mock_jobs.return_value = [
                {
                    'job_id': self.test_job_id,
                    'title': 'Software Engineer',
                    'company_id': self.test_company_id
                }
            ]

            response = self.client.get(f'/company/{self.test_company_id}/jobs')
            self.assertEqual(response.status_code, 200)

        # Step 3: Engage with job from company page
        with patch('src.authentication.auth_utils.get_current_user') as mock_auth:
            mock_auth.return_value = {'user_id': self.test_user_id}

            with patch('src.controllers.jobs.actions.JobActionsController.like_job') as mock_like:
                mock_like.return_value = {
                    "success": True,
                    "message": "Job liked successfully",
                    "data": {"like_id": str(uuid.uuid4()), "like_count": 1}
                }

                response = self.client.post(
                    f'/api/jobs/{self.test_job_id}/like',
                    headers=self.auth_headers
                )

                self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    import unittest

    unittest.main()
