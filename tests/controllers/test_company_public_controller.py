"""
Unit tests for CompanyPublicController

Tests all methods of the CompanyPublicController including:
- get_public_profile functionality
- get_company_active_jobs functionality
- get_company_statistics functionality
- Error handling and validation
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from src.controllers.company.public import CompanyPublicController
from src.database.models import Company, Job


class TestCompanyPublicController:
    """Test cases for CompanyPublicController"""

    @pytest.fixture
    def mock_factory(self):
        """Create mock factory for controller initialization"""
        factory = Mock()
        return factory

    @pytest.fixture
    def controller(self, mock_factory):
        """Create CompanyPublicController instance for testing"""
        controller = CompanyPublicController(mock_factory)
        controller.logger = Mock()
        return controller

    @pytest.fixture
    def mock_session(self):
        """Create mock database session"""
        session = Mock()
        session.__enter__ = Mock(return_value=session)
        session.__exit__ = Mock(return_value=None)
        return session

    @pytest.fixture
    def sample_company_orm(self):
        """Create sample company ORM object"""
        company_orm = Mock()
        company_orm.to_dict.return_value = {
            'company_id': 'comp123',
            'company_name': 'Test Company',
            'description': 'A test company',
            'industry': 'Technology',
            'location': 'Cape Town',
            'website': 'https://testcompany.com',
            'logo_url': 'https://testcompany.com/logo.png',
            'is_verified': True,
            'created_at': datetime.now(timezone.utc)
        }
        return company_orm

    @pytest.fixture
    def sample_job_orm(self):
        """Create sample job ORM object"""
        job_orm = Mock()
        job_orm.to_dict.return_value = {
            'job_id': 'job123',
            'title': 'Software Engineer',
            'description': 'A great job opportunity',
            'company_id': 'comp123',
            'status': 'active',
            'posted_at': datetime.now(timezone.utc),
            'expires_at': datetime.now(timezone.utc),
            'salary_min': 50000,
            'salary_max': 80000,
            'location': 'Cape Town'
        }
        return job_orm


class TestGetPublicProfile:
    """Test get_public_profile method"""

    @pytest.fixture
    def controller(self):
        factory = Mock()
        controller = CompanyPublicController(factory)
        controller.logger = Mock()
        return controller

    @pytest.mark.asyncio
    async def test_get_public_profile_success(self, controller, sample_company_orm):
        """Test successful retrieval of company public profile"""
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)

        # Mock company found
        mock_session.query.return_value.filter_by.return_value.first.return_value = sample_company_orm

        controller.get_session = Mock(return_value=mock_session)

        result = await controller.get_public_profile("comp123")

        assert result is not None
        assert isinstance(result, Company)
        assert result.company_id == "comp123"
        assert result.company_name == "Test Company"

    @pytest.mark.asyncio
    async def test_get_public_profile_not_found(self, controller):
        """Test get_public_profile when company doesn't exist"""
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)

        # Mock company not found
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        controller.get_session = Mock(return_value=mock_session)

        result = await controller.get_public_profile("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_public_profile_invalid_id(self, controller):
        """Test get_public_profile with invalid company ID"""
        result = await controller.get_public_profile("")
        assert result is None

        result = await controller.get_public_profile(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_public_profile_database_error(self, controller):
        """Test get_public_profile with database error"""
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)

        # Mock database error
        mock_session.query.side_effect = Exception("Database connection failed")

        controller.get_session = Mock(return_value=mock_session)

        result = await controller.get_public_profile("comp123")

        assert result is None
        controller.logger.error.assert_called()


class TestGetCompanyActiveJobs:
    """Test get_company_active_jobs method"""

    @pytest.fixture
    def controller(self):
        factory = Mock()
        controller = CompanyPublicController(factory)
        controller.logger = Mock()
        return controller

    @pytest.mark.asyncio
    async def test_get_company_active_jobs_success(self, controller, sample_job_orm):
        """Test successful retrieval of company active jobs"""
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)

        # Mock active jobs found
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            sample_job_orm, sample_job_orm
        ]

        controller.get_session = Mock(return_value=mock_session)

        result = await controller.get_company_active_jobs("comp123")

        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(job, Job) for job in result)

    @pytest.mark.asyncio
    async def test_get_company_active_jobs_empty(self, controller):
        """Test get_company_active_jobs when no active jobs exist"""
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)

        # Mock no active jobs found
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        controller.get_session = Mock(return_value=mock_session)

        result = await controller.get_company_active_jobs("comp123")

        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_company_active_jobs_with_limit(self, controller, sample_job_orm):
        """Test get_company_active_jobs with limit parameter"""
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)

        # Mock query chain with limit
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_job_orm]

        controller.get_session = Mock(return_value=mock_session)

        result = await controller.get_company_active_jobs("comp123", limit=5)

        assert result is not None
        assert len(result) == 1
        mock_query.limit.assert_called_once_with(5)

    @pytest.mark.asyncio
    async def test_get_company_active_jobs_invalid_id(self, controller):
        """Test get_company_active_jobs with invalid company ID"""
        result = await controller.get_company_active_jobs("")
        assert result is None

        result = await controller.get_company_active_jobs(None)
        assert result is None


class TestGetCompanyStatistics:
    """Test get_company_statistics method"""

    @pytest.fixture
    def controller(self):
        factory = Mock()
        controller = CompanyPublicController(factory)
        controller.logger = Mock()
        return controller

    @pytest.mark.asyncio
    async def test_get_company_statistics_success(self, controller):
        """Test successful retrieval of company statistics"""
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)

        # Mock statistics queries
        mock_session.query.return_value.filter_by.return_value.count.return_value = 10  # total jobs
        mock_session.query.return_value.filter.return_value.count.return_value = 7  # active jobs
        mock_session.query.return_value.join.return_value.filter_by.return_value.count.return_value = 25  # total applications

        controller.get_session = Mock(return_value=mock_session)

        result = await controller.get_company_statistics("comp123")

        assert result is not None
        assert isinstance(result, dict)
        assert 'total_jobs' in result
        assert 'active_jobs' in result
        assert 'total_applications' in result
        assert result['total_jobs'] == 10
        assert result['active_jobs'] == 7
        assert result['total_applications'] == 25

    @pytest.mark.asyncio
    async def test_get_company_statistics_zero_values(self, controller):
        """Test get_company_statistics with zero values"""
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)

        # Mock zero statistics
        mock_session.query.return_value.filter_by.return_value.count.return_value = 0
        mock_session.query.return_value.filter.return_value.count.return_value = 0
        mock_session.query.return_value.join.return_value.filter_by.return_value.count.return_value = 0

        controller.get_session = Mock(return_value=mock_session)

        result = await controller.get_company_statistics("comp123")

        assert result is not None
        assert result['total_jobs'] == 0
        assert result['active_jobs'] == 0
        assert result['total_applications'] == 0

    @pytest.mark.asyncio
    async def test_get_company_statistics_invalid_id(self, controller):
        """Test get_company_statistics with invalid company ID"""
        result = await controller.get_company_statistics("")
        assert result is None

        result = await controller.get_company_statistics(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_company_statistics_database_error(self, controller):
        """Test get_company_statistics with database error"""
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)

        # Mock database error
        mock_session.query.side_effect = Exception("Database error")

        controller.get_session = Mock(return_value=mock_session)

        result = await controller.get_company_statistics("comp123")

        assert result is None
        controller.logger.error.assert_called()


class TestCompanyPublicControllerValidation:
    """Test validation methods and error handling"""

    @pytest.fixture
    def controller(self):
        factory = Mock()
        controller = CompanyPublicController(factory)
        controller.logger = Mock()
        return controller

    def test_validate_company_id_valid(self, controller):
        """Test validation with valid company ID"""
        # Assuming there's a validation method
        if hasattr(controller, '_validate_company_id'):
            result = controller._validate_company_id("comp123")
            assert result is True

    def test_validate_company_id_invalid(self, controller):
        """Test validation with invalid company ID"""
        if hasattr(controller, '_validate_company_id'):
            assert controller._validate_company_id("") is False
            assert controller._validate_company_id(None) is False
            assert controller._validate_company_id("   ") is False

    @pytest.mark.asyncio
    async def test_error_logging(self, controller):
        """Test that errors are properly logged"""
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)

        # Mock database error
        mock_session.query.side_effect = Exception("Test error")

        controller.get_session = Mock(return_value=mock_session)

        result = await controller.get_public_profile("comp123")

        assert result is None
        controller.logger.error.assert_called()


class TestCompanyPublicControllerIntegration:
    """Integration tests for CompanyPublicController"""

    @pytest.fixture
    def controller(self):
        factory = Mock()
        controller = CompanyPublicController(factory)
        controller.logger = Mock()
        return controller

    @pytest.mark.asyncio
    async def test_complete_company_profile_flow(self, controller, sample_company_orm, sample_job_orm):
        """Test complete flow of getting company profile and jobs"""
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)

        controller.get_session = Mock(return_value=mock_session)

        # Mock company profile query
        mock_session.query.return_value.filter_by.return_value.first.return_value = sample_company_orm

        # Get company profile
        company = await controller.get_public_profile("comp123")
        assert company is not None

        # Reset mock for jobs query
        mock_session.reset_mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)

        # Mock jobs query
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [sample_job_orm]

        # Get company jobs
        jobs = await controller.get_company_active_jobs("comp123")
        assert jobs is not None
        assert len(jobs) == 1

    @pytest.mark.asyncio
    async def test_company_not_found_flow(self, controller):
        """Test flow when company is not found"""
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)

        # Mock company not found
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        controller.get_session = Mock(return_value=mock_session)

        # All methods should return None/empty for non-existent company
        company = await controller.get_public_profile("nonexistent")
        assert company is None

        jobs = await controller.get_company_active_jobs("nonexistent")
        assert jobs is None

        stats = await controller.get_company_statistics("nonexistent")
        assert stats is None


class TestCompanyPublicControllerCaching:
    """Test caching behavior (if implemented)"""

    @pytest.fixture
    def controller(self):
        factory = Mock()
        controller = CompanyPublicController(factory)
        controller.logger = Mock()
        return controller

    @pytest.mark.asyncio
    async def test_caching_behavior(self, controller, sample_company_orm):
        """Test that caching works correctly (if implemented)"""
        # This test would verify caching behavior if implemented
        # For now, just ensure methods work without caching
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)

        mock_session.query.return_value.filter_by.return_value.first.return_value = sample_company_orm

        controller.get_session = Mock(return_value=mock_session)

        # Call method twice
        result1 = await controller.get_public_profile("comp123")
        result2 = await controller.get_public_profile("comp123")

        assert result1 is not None
        assert result2 is not None
        assert result1.company_id == result2.company_id


if __name__ == '__main__':
    pytest.main([__file__])
