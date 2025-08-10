"""
Integration Tests for Job Actions Authentication

Tests authentication integration including:
- JWT token validation
- User session management
- Permission checks
- Anonymous vs authenticated flows
- Rate limiting integration
"""

import pytest
import json
import jwt
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

from tests.base import BaseTestCase


class TestJobActionsAuthenticationIntegration(BaseTestCase):
    """Integration tests for job actions authentication flows"""

    def setUp(self):
        super().setUp()
        self.test_user_id = "test_user_123"
        self.test_job_id = "test_job_456"
        self.test_company_id = "test_company_789"

        # Mock JWT token
        self.valid_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test_payload"
        self.auth_headers = {
            'Authorization': f'Bearer {self.valid_token}',
            'Content-Type': 'application/json'
        }

    def test_like_job_requires_authentication(self):
        """Test that like job endpoint requires authentication"""
        # Test without authentication header
        response = self.client.post(f'/api/jobs/{self.test_job_id}/like')
        self.assertEqual(response.status_code, 401)

        # Test with invalid token
        invalid_headers = {
            'Authorization': 'Bearer invalid_token',
            'Content-Type': 'application/json'
        }

        with patch('src.authentication.auth_utils.get_current_user') as mock_auth:
            mock_auth.return_value = None  # Invalid token

            response = self.client.post(
                f'/api/jobs/{self.test_job_id}/like',
                headers=invalid_headers
            )
            self.assertEqual(response.status_code, 401)

    def test_like_job_with_valid_authentication(self):
        """Test like job with valid authentication"""
        with patch('src.authentication.auth_utils.get_current_user') as mock_auth:
            mock_auth.return_value = {'user_id': self.test_user_id}

            with patch('src.controllers.jobs.actions.JobActionsController.like_job') as mock_like:
                mock_like.return_value = {
                    "success": True,
                    "message": "Job liked successfully",
                    "data": {"like_id": "like123", "like_count": 1}
                }

                response = self.client.post(
                    f'/api/jobs/{self.test_job_id}/like',
                    headers=self.auth_headers
                )

                self.assertEqual(response.status_code, 200)
                data = json.loads(response.data)
                self.assertTrue(data['success'])

                # Verify controller was called with correct user ID
                mock_like.assert_called_once_with(self.test_user_id, self.test_job_id)

    def test_save_job_requires_authentication(self):
        """Test that save job endpoint requires authentication"""
        response = self.client.post(f'/api/jobs/{self.test_job_id}/save')
        self.assertEqual(response.status_code, 401)

    def test_save_job_with_valid_authentication(self):
        """Test save job with valid authentication"""
        with patch('src.authentication.auth_utils.get_current_user') as mock_auth:
            mock_auth.return_value = {'user_id': self.test_user_id}

            with patch('src.controllers.jobs.actions.JobActionsController.save_job') as mock_save:
                mock_save.return_value = {
                    "success": True,
                    "message": "Job saved successfully",
                    "data": {"saved_job_id": "save123"}
                }

                response = self.client.post(
                    f'/api/jobs/{self.test_job_id}/save',
                    headers=self.auth_headers
                )

                self.assertEqual(response.status_code, 200)
                data = json.loads(response.data)
                self.assertTrue(data['success'])

                mock_save.assert_called_once_with(self.test_user_id, self.test_job_id)

    def test_share_job_allows_anonymous_access(self):
        """Test that share job allows anonymous access"""
        with patch('src.controllers.jobs.actions.JobActionsController.share_job') as mock_share:
            mock_share.return_value = {
                "success": True,
                "message": "Job shared successfully",
                "data": {
                    "share_id": "share123",
                    "referral_code": None,  # No referral for anonymous
                    "share_count": 1
                }
            }

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

            # Verify controller was called with None user_id for anonymous
            mock_share.assert_called_once_with(None, self.test_job_id, "email")

    def test_share_job_with_authentication_includes_referral(self):
        """Test that authenticated share includes referral code"""
        with patch('src.authentication.auth_utils.get_current_user') as mock_auth:
            mock_auth.return_value = {'user_id': self.test_user_id}

            with patch('src.controllers.jobs.actions.JobActionsController.share_job') as mock_share:
                mock_share.return_value = {
                    "success": True,
                    "message": "Job shared successfully",
                    "data": {
                        "share_id": "share123",
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
                self.assertEqual(data['data']['referral_code'], "REF123")

                # Verify controller was called with user_id
                mock_share.assert_called_once_with(self.test_user_id, self.test_job_id, "linkedin")

    def test_get_job_actions_state_requires_authentication(self):
        """Test that job actions state endpoint requires authentication"""
        response = self.client.get(f'/api/jobs/{self.test_job_id}/actions')
        self.assertEqual(response.status_code, 401)

    def test_get_job_actions_state_with_authentication(self):
        """Test job actions state with valid authentication"""
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

                response = self.client.get(
                    f'/api/jobs/{self.test_job_id}/actions',
                    headers=self.auth_headers
                )

                self.assertEqual(response.status_code, 200)
                data = json.loads(response.data)
                self.assertTrue(data['success'])
                self.assertTrue(data['data']['user_has_liked'])

                mock_state.assert_called_once_with(self.test_user_id, self.test_job_id)

    def test_jwt_token_validation(self):
        """Test JWT token validation process"""
        with patch('src.authentication.auth_utils.jwt.decode') as mock_jwt_decode:
            # Mock valid JWT payload
            mock_jwt_decode.return_value = {
                'user_id': self.test_user_id,
                'exp': datetime.now(timezone.utc) + timedelta(hours=1)
            }

            with patch('src.authentication.auth_utils.get_current_user') as mock_auth:
                mock_auth.return_value = {'user_id': self.test_user_id}

                with patch('src.controllers.jobs.actions.JobActionsController.like_job') as mock_like:
                    mock_like.return_value = {
                        "success": True,
                        "message": "Job liked successfully",
                        "data": {"like_id": "like123", "like_count": 1}
                    }

                    response = self.client.post(
                        f'/api/jobs/{self.test_job_id}/like',
                        headers=self.auth_headers
                    )

                    self.assertEqual(response.status_code, 200)

                    # Verify JWT decode was called
                    mock_jwt_decode.assert_called()

    def test_expired_jwt_token_handling(self):
        """Test handling of expired JWT tokens"""
        with patch('src.authentication.auth_utils.jwt.decode') as mock_jwt_decode:
            # Mock expired token
            mock_jwt_decode.side_effect = jwt.ExpiredSignatureError("Token has expired")

            with patch('src.authentication.auth_utils.get_current_user') as mock_auth:
                mock_auth.return_value = None  # Expired token returns None

                response = self.client.post(
                    f'/api/jobs/{self.test_job_id}/like',
                    headers=self.auth_headers
                )

                self.assertEqual(response.status_code, 401)
                data = json.loads(response.data)
                self.assertIn('expired', data['message'].lower())

    def test_invalid_jwt_token_handling(self):
        """Test handling of invalid JWT tokens"""
        with patch('src.authentication.auth_utils.jwt.decode') as mock_jwt_decode:
            # Mock invalid token
            mock_jwt_decode.side_effect = jwt.InvalidTokenError("Invalid token")

            with patch('src.authentication.auth_utils.get_current_user') as mock_auth:
                mock_auth.return_value = None  # Invalid token returns None

                response = self.client.post(
                    f'/api/jobs/{self.test_job_id}/like',
                    headers=self.auth_headers
                )

                self.assertEqual(response.status_code, 401)
                data = json.loads(response.data)
                self.assertIn('invalid', data['message'].lower())

    def test_user_session_validation(self):
        """Test user session validation"""
        with patch('src.authentication.auth_utils.get_current_user') as mock_auth:
            # Mock user session lookup
            mock_auth.return_value = {
                'user_id': self.test_user_id,
                'session_id': 'session123',
                'is_active': True
            }

            with patch('src.controllers.jobs.actions.JobActionsController.like_job') as mock_like:
                mock_like.return_value = {
                    "success": True,
                    "message": "Job liked successfully",
                    "data": {"like_id": "like123", "like_count": 1}
                }

                response = self.client.post(
                    f'/api/jobs/{self.test_job_id}/like',
                    headers=self.auth_headers
                )

                self.assertEqual(response.status_code, 200)

                # Verify user session was validated
                mock_auth.assert_called_once()

    def test_inactive_user_session_handling(self):
        """Test handling of inactive user sessions"""
        with patch('src.authentication.auth_utils.get_current_user') as mock_auth:
            # Mock inactive user session
            mock_auth.return_value = {
                'user_id': self.test_user_id,
                'session_id': 'session123',
                'is_active': False
            }

            response = self.client.post(
                f'/api/jobs/{self.test_job_id}/like',
                headers=self.auth_headers
            )

            self.assertEqual(response.status_code, 401)
            data = json.loads(response.data)
            self.assertIn('inactive', data['message'].lower())

    def test_rate_limiting_with_authentication(self):
        """Test rate limiting integration with authentication"""
        with patch('src.authentication.auth_utils.get_current_user') as mock_auth:
            mock_auth.return_value = {'user_id': self.test_user_id}

            with patch(
                    'src.firewall.job_actions_security.job_actions_rate_limiter.check_rate_limit') as mock_rate_limit:
                # Mock rate limit exceeded for authenticated user
                mock_rate_limit.return_value = {
                    "allowed": False,
                    "message": "Rate limit exceeded for user",
                    "retry_after": 60
                }

                response = self.client.post(
                    f'/api/jobs/{self.test_job_id}/like',
                    headers=self.auth_headers
                )

                self.assertEqual(response.status_code, 429)
                data = json.loads(response.data)
                self.assertIn('rate limit', data['message'].lower())

                # Verify rate limiting was checked with user context
                mock_rate_limit.assert_called_once()

    def test_anonymous_rate_limiting(self):
        """Test rate limiting for anonymous users"""
        with patch('src.firewall.job_actions_security.job_actions_rate_limiter.check_rate_limit') as mock_rate_limit:
            # Mock rate limit for anonymous user (by IP)
            mock_rate_limit.return_value = {
                "allowed": False,
                "message": "Rate limit exceeded for IP",
                "retry_after": 300  # Longer for anonymous
            }

            share_data = {"share_method": "email"}
            response = self.client.post(
                f'/api/jobs/{self.test_job_id}/share',
                data=json.dumps(share_data),
                content_type='application/json'
            )

            self.assertEqual(response.status_code, 429)

            # Verify rate limiting was applied to anonymous user
            mock_rate_limit.assert_called_once()

    def test_csrf_protection_integration(self):
        """Test CSRF protection integration"""
        with patch('src.authentication.auth_utils.get_current_user') as mock_auth:
            mock_auth.return_value = {'user_id': self.test_user_id}

            with patch('src.firewall.csrf.validate_csrf_token') as mock_csrf:
                # Mock CSRF validation failure
                mock_csrf.return_value = False

                # Add CSRF token header
                csrf_headers = self.auth_headers.copy()
                csrf_headers['X-CSRF-Token'] = 'invalid_csrf_token'

                response = self.client.post(
                    f'/api/jobs/{self.test_job_id}/like',
                    headers=csrf_headers
                )

                self.assertEqual(response.status_code, 403)
                data = json.loads(response.data)
                self.assertIn('csrf', data['message'].lower())

    def test_permission_based_access_control(self):
        """Test permission-based access control"""
        with patch('src.authentication.auth_utils.get_current_user') as mock_auth:
            # Mock user without job action permissions
            mock_auth.return_value = {
                'user_id': self.test_user_id,
                'permissions': ['read_jobs'],  # Missing 'like_jobs' permission
                'role': 'restricted_user'
            }

            with patch('src.authentication.auth_utils.check_permission') as mock_permission:
                mock_permission.return_value = False  # No permission

                response = self.client.post(
                    f'/api/jobs/{self.test_job_id}/like',
                    headers=self.auth_headers
                )

                self.assertEqual(response.status_code, 403)
                data = json.loads(response.data)
                self.assertIn('permission', data['message'].lower())

    def test_company_analytics_authentication(self):
        """Test company analytics endpoints require proper authentication"""
        # Test without authentication
        response = self.client.get(f'/api/company/{self.test_company_id}/engagement')
        self.assertEqual(response.status_code, 401)

        # Test with authentication but wrong company access
        with patch('src.authentication.auth_utils.get_current_user') as mock_auth:
            mock_auth.return_value = {'user_id': self.test_user_id, 'company_id': 'different_company'}

            with patch('src.authentication.auth_utils.check_company_access') as mock_company_access:
                mock_company_access.return_value = False  # No access to this company

                response = self.client.get(
                    f'/api/company/{self.test_company_id}/engagement',
                    headers=self.auth_headers
                )

                self.assertEqual(response.status_code, 403)

    def test_user_context_propagation(self):
        """Test that user context is properly propagated through the request"""
        with patch('src.authentication.auth_utils.get_current_user') as mock_auth:
            mock_user = {
                'user_id': self.test_user_id,
                'email': 'test@example.com',
                'role': 'job_seeker',
                'company_id': None
            }
            mock_auth.return_value = mock_user

            with patch('src.controllers.jobs.actions.JobActionsController.like_job') as mock_like:
                mock_like.return_value = {
                    "success": True,
                    "message": "Job liked successfully",
                    "data": {"like_id": "like123", "like_count": 1}
                }

                response = self.client.post(
                    f'/api/jobs/{self.test_job_id}/like',
                    headers=self.auth_headers
                )

                self.assertEqual(response.status_code, 200)

                # Verify user context was passed to controller
                mock_like.assert_called_once_with(self.test_user_id, self.test_job_id)

    def test_authentication_error_responses(self):
        """Test consistent authentication error responses"""
        test_cases = [
            # No auth header
            ({}, 401, "authentication required"),
            # Invalid auth format
            ({'Authorization': 'InvalidFormat'}, 401, "invalid authorization"),
            # Missing Bearer prefix
            ({'Authorization': 'Token abc123'}, 401, "invalid authorization"),
        ]

        for headers, expected_status, expected_message_part in test_cases:
            response = self.client.post(
                f'/api/jobs/{self.test_job_id}/like',
                headers=headers
            )

            self.assertEqual(response.status_code, expected_status)
            data = json.loads(response.data)
            self.assertIn(expected_message_part, data['message'].lower())


class TestJobActionsAuthorizationIntegration(BaseTestCase):
    """Integration tests for job actions authorization"""

    def setUp(self):
        super().setUp()
        self.test_user_id = "test_user_123"
        self.test_job_id = "test_job_456"
        self.test_company_id = "test_company_789"
        self.auth_headers = {
            'Authorization': 'Bearer valid_token',
            'Content-Type': 'application/json'
        }

    def test_job_seeker_can_like_jobs(self):
        """Test that job seekers can like jobs"""
        with patch('src.authentication.auth_utils.get_current_user') as mock_auth:
            mock_auth.return_value = {
                'user_id': self.test_user_id,
                'role': 'job_seeker',
                'permissions': ['like_jobs', 'save_jobs', 'share_jobs']
            }

            with patch('src.controllers.jobs.actions.JobActionsController.like_job') as mock_like:
                mock_like.return_value = {
                    "success": True,
                    "message": "Job liked successfully",
                    "data": {"like_id": "like123", "like_count": 1}
                }

                response = self.client.post(
                    f'/api/jobs/{self.test_job_id}/like',
                    headers=self.auth_headers
                )

                self.assertEqual(response.status_code, 200)

    def test_employer_cannot_like_own_jobs(self):
        """Test that employers cannot like their own company's jobs"""
        with patch('src.authentication.auth_utils.get_current_user') as mock_auth:
            mock_auth.return_value = {
                'user_id': self.test_user_id,
                'role': 'employer',
                'company_id': self.test_company_id
            }

            with patch('src.controllers.jobs.actions.JobActionsController.like_job') as mock_like:
                # Mock job belongs to same company
                mock_like.return_value = {
                    "success": False,
                    "message": "Cannot like your own company's jobs",
                    "code": 403
                }

                response = self.client.post(
                    f'/api/jobs/{self.test_job_id}/like',
                    headers=self.auth_headers
                )

                self.assertEqual(response.status_code, 403)

    def test_admin_can_access_all_analytics(self):
        """Test that admins can access all company analytics"""
        with patch('src.authentication.auth_utils.get_current_user') as mock_auth:
            mock_auth.return_value = {
                'user_id': self.test_user_id,
                'role': 'admin',
                'permissions': ['access_all_analytics']
            }

            with patch(
                    'src.services.job_actions_analytics.JobActionsAnalyticsService.get_company_engagement_stats') as mock_stats:
                mock_stats.return_value = {
                    'company_id': self.test_company_id,
                    'total_job_likes': 100,
                    'total_job_saves': 50
                }

                response = self.client.get(
                    f'/api/company/{self.test_company_id}/engagement',
                    headers=self.auth_headers
                )

                self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    import unittest

    unittest.main()
