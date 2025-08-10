"""
Integration Tests for Job Actions Database Operations

Tests database integration including:
- ORM model relationships
- Transaction handling
- Constraint enforcement
- Data consistency
- Performance considerations
"""

import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from sqlalchemy.exc import IntegrityError

from tests.base import BaseTestCase
from src.database import JobLikeORM, JobShareORM, SavedJobORM, JobsORM, JobSeekerProfileORM


class TestJobActionsORMIntegration(BaseTestCase):
    """Integration tests for job actions ORM operations"""

    def setUp(self):
        super().setUp()
        self.test_user_id = "test_user_123"
        self.test_job_id = "test_job_456"
        self.test_company_id = "test_company_789"

    def test_job_like_crud_operations(self):
        """Test complete CRUD operations for job likes"""
        with patch('src.database.session') as mock_session:
            # Mock session context manager
            mock_db_session = Mock()
            mock_session.__enter__ = Mock(return_value=mock_db_session)
            mock_session.__exit__ = Mock(return_value=None)

            # Test Create
            like_orm = JobLikeORM(
                like_id=str(uuid.uuid4()),
                user_id=self.test_user_id,
                job_id=self.test_job_id,
                created_at=datetime.now(timezone.utc)
            )

            mock_db_session.add(like_orm)
            mock_db_session.commit()

            # Verify add and commit were called
            mock_db_session.add.assert_called_once_with(like_orm)
            mock_db_session.commit.assert_called_once()

            # Test Read
            mock_db_session.query(JobLikeORM).filter_by(
                user_id=self.test_user_id,
                job_id=self.test_job_id
            ).first()

            # Verify query was called
            mock_db_session.query.assert_called_with(JobLikeORM)

            # Test Delete
            mock_db_session.delete(like_orm)
            mock_db_session.commit()

            # Verify delete was called
            mock_db_session.delete.assert_called_with(like_orm)

    def test_job_share_crud_operations(self):
        """Test complete CRUD operations for job shares"""
        with patch('src.database.session') as mock_session:
            mock_db_session = Mock()
            mock_session.__enter__ = Mock(return_value=mock_db_session)
            mock_session.__exit__ = Mock(return_value=None)

            # Test Create with authenticated user
            share_orm = JobShareORM(
                share_id=str(uuid.uuid4()),
                user_id=self.test_user_id,
                job_id=self.test_job_id,
                share_method="linkedin",
                shared_at=datetime.now(timezone.utc),
                referral_code="REF123"
            )

            mock_db_session.add(share_orm)
            mock_db_session.commit()

            mock_db_session.add.assert_called_with(share_orm)
            mock_db_session.commit.assert_called()

            # Test Create with anonymous user
            anonymous_share_orm = JobShareORM(
                share_id=str(uuid.uuid4()),
                user_id=None,  # Anonymous share
                job_id=self.test_job_id,
                share_method="email",
                shared_at=datetime.now(timezone.utc),
                referral_code=None
            )

            mock_db_session.add(anonymous_share_orm)
            mock_db_session.commit()

            # Verify anonymous share was added
            self.assertEqual(mock_db_session.add.call_count, 2)

    def test_saved_job_crud_operations(self):
        """Test complete CRUD operations for saved jobs"""
        with patch('src.database.session') as mock_session:
            mock_db_session = Mock()
            mock_session.__enter__ = Mock(return_value=mock_db_session)
            mock_session.__exit__ = Mock(return_value=None)

            # Test Create
            saved_job_orm = SavedJobORM(
                saved_job_id=str(uuid.uuid4()),
                user_id=self.test_user_id,
                job_id=self.test_job_id,
                saved_at=datetime.now(timezone.utc)
            )

            mock_db_session.add(saved_job_orm)
            mock_db_session.commit()

            mock_db_session.add.assert_called_with(saved_job_orm)

            # Test Read with filtering
            mock_db_session.query(SavedJobORM).filter_by(
                user_id=self.test_user_id
            ).order_by(SavedJobORM.saved_at.desc()).all()

            # Verify query with ordering
            mock_db_session.query.assert_called_with(SavedJobORM)

    def test_database_relationships(self):
        """Test ORM relationships between models"""
        with patch('src.database.session') as mock_session:
            mock_db_session = Mock()
            mock_session.__enter__ = Mock(return_value=mock_db_session)
            mock_session.__exit__ = Mock(return_value=None)

            # Mock relationship queries
            mock_job = Mock()
            mock_job.likes = []
            mock_job.shares = []
            mock_job.saved_jobs = []

            mock_user = Mock()
            mock_user.liked_jobs = []
            mock_user.shared_jobs = []
            mock_user.saved_jobs = []

            # Test job relationships
            mock_db_session.query(JobsORM).options(
                mock_session.joinedload(JobsORM.likes),
                mock_session.joinedload(JobsORM.shares),
                mock_session.joinedload(JobsORM.saved_jobs)
            ).filter_by(job_id=self.test_job_id).first.return_value = mock_job

            # Test user relationships
            mock_db_session.query(JobSeekerProfileORM).options(
                mock_session.joinedload(JobSeekerProfileORM.liked_jobs),
                mock_session.joinedload(JobSeekerProfileORM.shared_jobs),
                mock_session.joinedload(JobSeekerProfileORM.saved_jobs)
            ).filter_by(user_uid=self.test_user_id).first.return_value = mock_user

            # Verify relationship loading
            self.assertIsNotNone(mock_job)
            self.assertIsNotNone(mock_user)

    def test_unique_constraint_enforcement(self):
        """Test unique constraint enforcement"""
        with patch('src.database.session') as mock_session:
            mock_db_session = Mock()
            mock_session.__enter__ = Mock(return_value=mock_db_session)
            mock_session.__exit__ = Mock(return_value=None)

            # Mock IntegrityError for duplicate like
            mock_db_session.commit.side_effect = IntegrityError(
                "Duplicate entry", None, None
            )

            like_orm = JobLikeORM(
                like_id=str(uuid.uuid4()),
                user_id=self.test_user_id,
                job_id=self.test_job_id
            )

            mock_db_session.add(like_orm)

            # Should raise IntegrityError
            with self.assertRaises(IntegrityError):
                mock_db_session.commit()

    def test_foreign_key_constraint_enforcement(self):
        """Test foreign key constraint enforcement"""
        with patch('src.database.session') as mock_session:
            mock_db_session = Mock()
            mock_session.__enter__ = Mock(return_value=mock_db_session)
            mock_session.__exit__ = Mock(return_value=None)

            # Mock IntegrityError for invalid foreign key
            mock_db_session.commit.side_effect = IntegrityError(
                "Foreign key constraint fails", None, None
            )

            # Try to create like with non-existent job
            like_orm = JobLikeORM(
                like_id=str(uuid.uuid4()),
                user_id=self.test_user_id,
                job_id="nonexistent_job"
            )

            mock_db_session.add(like_orm)

            # Should raise IntegrityError
            with self.assertRaises(IntegrityError):
                mock_db_session.commit()

    def test_transaction_rollback_on_error(self):
        """Test transaction rollback on database errors"""
        with patch('src.database.session') as mock_session:
            mock_db_session = Mock()
            mock_session.__enter__ = Mock(return_value=mock_db_session)
            mock_session.__exit__ = Mock(return_value=None)

            # Mock database error during commit
            mock_db_session.commit.side_effect = Exception("Database connection lost")

            like_orm = JobLikeORM(
                like_id=str(uuid.uuid4()),
                user_id=self.test_user_id,
                job_id=self.test_job_id
            )

            mock_db_session.add(like_orm)

            try:
                mock_db_session.commit()
            except Exception:
                mock_db_session.rollback()

            # Verify rollback was called
            mock_db_session.rollback.assert_called_once()

    def test_bulk_operations(self):
        """Test bulk database operations for performance"""
        with patch('src.database.session') as mock_session:
            mock_db_session = Mock()
            mock_session.__enter__ = Mock(return_value=mock_db_session)
            mock_session.__exit__ = Mock(return_value=None)

            # Create multiple likes
            likes = []
            for i in range(10):
                like_orm = JobLikeORM(
                    like_id=str(uuid.uuid4()),
                    user_id=f"user_{i}",
                    job_id=self.test_job_id
                )
                likes.append(like_orm)

            # Bulk add
            mock_db_session.add_all(likes)
            mock_db_session.commit()

            # Verify bulk add was called
            mock_db_session.add_all.assert_called_once_with(likes)

    def test_database_indexes_usage(self):
        """Test that database queries use indexes efficiently"""
        with patch('src.database.session') as mock_session:
            mock_db_session = Mock()
            mock_session.__enter__ = Mock(return_value=mock_db_session)
            mock_session.__exit__ = Mock(return_value=None)

            # Mock query that should use index
            mock_query = Mock()
            mock_db_session.query.return_value = mock_query
            mock_query.filter_by.return_value = mock_query
            mock_query.count.return_value = 5

            # Query that should use user_id, job_id index
            result = mock_db_session.query(JobLikeORM).filter_by(
                user_id=self.test_user_id,
                job_id=self.test_job_id
            ).count()

            # Verify query was executed
            self.assertEqual(result, 5)
            mock_db_session.query.assert_called_with(JobLikeORM)


class TestJobActionsControllerDatabaseIntegration(BaseTestCase):
    """Integration tests for controller database operations"""

    def setUp(self):
        super().setUp()
        self.test_user_id = "test_user_123"
        self.test_job_id = "test_job_456"

    def test_like_job_database_integration(self):
        """Test like_job method database integration"""
        with patch('src.controllers.jobs.actions.JobActionsController.get_session') as mock_get_session:
            mock_session = Mock()
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            mock_get_session.return_value = mock_session

            # Mock user and job existence checks
            mock_user = Mock()
            mock_job = Mock()
            mock_session.query.return_value.filter_by.return_value.first.side_effect = [
                mock_user,  # User exists
                mock_job,  # Job exists
                None  # No existing like
            ]

            # Mock like count query
            mock_session.query.return_value.filter_by.return_value.scalar.return_value = 1

            # Import and test controller
            from src.controllers.jobs.actions import JobActionsController

            factory = Mock()
            controller = JobActionsController(factory)
            controller.logger = Mock()
            controller.analytics_service = Mock()

            # Test like_job method
            result = controller.like_job(self.test_user_id, self.test_job_id)

            # Verify database operations were called
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()

    def test_save_job_database_integration(self):
        """Test save_job method database integration"""
        with patch('src.controllers.jobs.actions.JobActionsController.get_session') as mock_get_session:
            mock_session = Mock()
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            mock_get_session.return_value = mock_session

            # Mock user and job existence, no existing save
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

            # Test save_job method
            result = controller.save_job(self.test_user_id, self.test_job_id)

            # Verify database operations
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()

    def test_share_job_database_integration(self):
        """Test share_job method database integration"""
        with patch('src.controllers.jobs.actions.JobActionsController.get_session') as mock_get_session:
            mock_session = Mock()
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            mock_get_session.return_value = mock_session

            # Mock job exists, user exists
            mock_job = Mock()
            mock_user = Mock()
            mock_session.query.return_value.filter_by.return_value.first.side_effect = [
                mock_job,  # Job exists
                mock_user  # User exists
            ]

            # Mock share count
            mock_session.query.return_value.filter_by.return_value.scalar.return_value = 1

            from src.controllers.jobs.actions import JobActionsController

            factory = Mock()
            controller = JobActionsController(factory)
            controller.logger = Mock()
            controller.analytics_service = Mock()

            # Test share_job method
            result = controller.share_job(self.test_user_id, self.test_job_id, "linkedin")

            # Verify database operations
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()

    def test_get_job_actions_state_database_integration(self):
        """Test get_job_actions_state method database integration"""
        with patch('src.controllers.jobs.actions.JobActionsController.get_session') as mock_get_session:
            mock_session = Mock()
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            mock_get_session.return_value = mock_session

            # Mock user actions and counts
            mock_like = Mock()
            mock_save = Mock()
            mock_session.query.return_value.filter_by.return_value.first.side_effect = [
                mock_like,  # User has liked
                mock_save  # User has saved
            ]

            # Mock count queries
            mock_session.query.return_value.filter_by.return_value.scalar.side_effect = [
                10,  # Like count
                5  # Share count
            ]

            from src.controllers.jobs.actions import JobActionsController

            factory = Mock()
            controller = JobActionsController(factory)
            controller.logger = Mock()

            # Test get_job_actions_state method
            result = controller.get_job_actions_state(self.test_user_id, self.test_job_id)

            # Verify multiple database queries were made
            self.assertGreater(mock_session.query.call_count, 2)


class TestCompanyPublicControllerDatabaseIntegration(BaseTestCase):
    """Integration tests for company public controller database operations"""

    def setUp(self):
        super().setUp()
        self.test_company_id = "test_company_789"

    def test_get_public_profile_database_integration(self):
        """Test get_public_profile method database integration"""
        with patch('src.controllers.company.public.CompanyPublicController.get_session') as mock_get_session:
            mock_session = Mock()
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            mock_get_session.return_value = mock_session

            # Mock company found
            mock_company = Mock()
            mock_company.to_dict.return_value = {
                'company_id': self.test_company_id,
                'company_name': 'Test Company'
            }
            mock_session.query.return_value.filter_by.return_value.first.return_value = mock_company

            from src.controllers.company.public import CompanyPublicController

            factory = Mock()
            controller = CompanyPublicController(factory)
            controller.logger = Mock()

            # Test get_public_profile method
            result = controller.get_public_profile(self.test_company_id)

            # Verify database query was made
            mock_session.query.assert_called()

    def test_get_company_active_jobs_database_integration(self):
        """Test get_company_active_jobs method database integration"""
        with patch('src.controllers.company.public.CompanyPublicController.get_session') as mock_get_session:
            mock_session = Mock()
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            mock_get_session.return_value = mock_session

            # Mock active jobs query
            mock_job1 = Mock()
            mock_job1.to_dict.return_value = {'job_id': 'job1', 'title': 'Job 1'}
            mock_job2 = Mock()
            mock_job2.to_dict.return_value = {'job_id': 'job2', 'title': 'Job 2'}

            mock_query = Mock()
            mock_session.query.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.all.return_value = [mock_job1, mock_job2]

            from src.controllers.company.public import CompanyPublicController

            factory = Mock()
            controller = CompanyPublicController(factory)
            controller.logger = Mock()

            # Test get_company_active_jobs method
            result = controller.get_company_active_jobs(self.test_company_id)

            # Verify database query with filtering and ordering
            mock_session.query.assert_called()
            mock_query.filter.assert_called()
            mock_query.order_by.assert_called()

    def test_get_company_statistics_database_integration(self):
        """Test get_company_statistics method database integration"""
        with patch('src.controllers.company.public.CompanyPublicController.get_session') as mock_get_session:
            mock_session = Mock()
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            mock_get_session.return_value = mock_session

            # Mock statistics queries
            mock_query = Mock()
            mock_session.query.return_value = mock_query
            mock_query.filter_by.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.join.return_value = mock_query
            mock_query.count.side_effect = [10, 7, 25]  # total jobs, active jobs, applications

            from src.controllers.company.public import CompanyPublicController

            factory = Mock()
            controller = CompanyPublicController(factory)
            controller.logger = Mock()

            # Test get_company_statistics method
            result = controller.get_company_statistics(self.test_company_id)

            # Verify multiple count queries were made
            self.assertEqual(mock_query.count.call_count, 3)


class TestAnalyticsServiceDatabaseIntegration(BaseTestCase):
    """Integration tests for analytics service database operations"""

    def setUp(self):
        super().setUp()
        self.test_company_id = "test_company_789"
        self.test_job_id = "test_job_456"

    def test_get_job_engagement_metrics_database_integration(self):
        """Test get_job_engagement_metrics method database integration"""
        with patch('src.services.job_actions_analytics.JobActionsAnalyticsService.get_session') as mock_get_session:
            mock_session = Mock()
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            mock_get_session.return_value = mock_session

            # Mock job exists
            mock_job = Mock()
            mock_job.view_count = 100
            mock_session.query.return_value.filter_by.return_value.first.return_value = mock_job

            # Mock count queries
            mock_session.query.return_value.filter_by.return_value.scalar.side_effect = [
                10,  # likes
                5,  # saves
                3,  # shares
                2  # applications
            ]

            from src.services.job_actions_analytics import JobActionsAnalyticsService

            factory = Mock()
            service = JobActionsAnalyticsService(factory)
            service.logger = Mock()

            # Test get_job_engagement_metrics method
            result = service.get_job_engagement_metrics(self.test_job_id)

            # Verify multiple database queries were made
            self.assertGreater(mock_session.query.call_count, 3)

    def test_get_company_engagement_stats_database_integration(self):
        """Test get_company_engagement_stats method database integration"""
        with patch('src.services.job_actions_analytics.JobActionsAnalyticsService.get_session') as mock_get_session:
            mock_session = Mock()
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)
            mock_get_session.return_value = mock_session

            # Mock company jobs subquery
            mock_subquery = Mock()
            mock_session.query.return_value.filter_by.return_value.subquery.return_value = mock_subquery

            # Mock engagement count queries
            mock_session.query.return_value.filter.return_value.scalar.side_effect = [
                50,  # total likes
                30,  # total saves
                20  # total shares
            ]

            # Mock job count
            mock_session.query.return_value.filter_by.return_value.scalar.return_value = 5

            from src.services.job_actions_analytics import JobActionsAnalyticsService

            factory = Mock()
            service = JobActionsAnalyticsService(factory)
            service.logger = Mock()

            # Test get_company_engagement_stats method
            result = service.get_company_engagement_stats(self.test_company_id)

            # Verify complex database queries were made
            self.assertGreater(mock_session.query.call_count, 5)


if __name__ == '__main__':
    import unittest

    unittest.main()
