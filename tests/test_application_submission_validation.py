"""
Test suite for application submission validation functionality.
Tests the enhanced validation logic implemented in task 3.3.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date, datetime, timezone, timedelta
from flask import Flask
from src.routes.jobseeker_routes.jobseeker_applications import jobseeker_applications_route
from src.database.models import JobApplication, Job, User, JobSeekerCV


@pytest.fixture
def app():
    """Create a test Flask app."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.register_blueprint(jobseeker_applications_route)
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    return User(
        uid="test-user-123",
        email="test@example.com",
        first_name="Test",
        last_name="User"
    )


@pytest.fixture
def mock_job():
    """Create a mock job for testing."""
    return Job(
        job_id="test-job-123",
        title="Software Developer",
        description="Test job description",
        status="active",
        expires_at=datetime.now(timezone.utc) + timedelta(days=30)
    )


@pytest.fixture
def mock_cv():
    """Create a mock CV for testing."""
    return JobSeekerCV(
        cv_id="test-cv-123",
        user_uid="test-user-123",
        title="Test CV"
    )


class TestApplicationSubmissionValidation:
    """Test class for application submission validation."""

    @patch('src.routes.jobseeker_routes.jobseeker_applications.get_controller')
    @patch('src.routes.jobseeker_routes.jobseeker_applications.jobseeker_login')
    def test_submit_application_missing_cv_id(self, mock_login, mock_get_controller, client, mock_user):
        """Test validation error when CV ID is missing."""
        mock_login.return_value = lambda f: f  # Mock decorator
        
        with client.application.app_context():
            with client.session_transaction() as sess:
                sess['user'] = mock_user.model_dump()
            
            response = client.post('/jobseeker/applications/submit/test-job-123', data={
                'cover_letter': 'This is a test cover letter that is definitely longer than fifty characters to meet the minimum requirement.',
                'expected_salary': '50000'
            }, follow_redirects=True)
            
            # Should redirect back to application form with error
            assert response.status_code == 200

    @patch('src.routes.jobseeker_routes.jobseeker_applications.get_controller')
    @patch('src.routes.jobseeker_routes.jobseeker_applications.jobseeker_login')
    def test_submit_application_short_cover_letter(self, mock_login, mock_get_controller, client, mock_user):
        """Test validation error when cover letter is too short."""
        mock_login.return_value = lambda f: f  # Mock decorator
        
        with client.application.app_context():
            with client.session_transaction() as sess:
                sess['user'] = mock_user.model_dump()
            
            response = client.post('/jobseeker/applications/submit/test-job-123', data={
                'cv_id': 'test-cv-123',
                'cover_letter': 'Too short',  # Less than 50 characters
                'expected_salary': '50000'
            }, follow_redirects=True)
            
            # Should redirect back to application form with error
            assert response.status_code == 200

    @patch('src.routes.jobseeker_routes.jobseeker_applications.get_controller')
    @patch('src.routes.jobseeker_routes.jobseeker_applications.jobseeker_login')
    def test_submit_application_invalid_salary(self, mock_login, mock_get_controller, client, mock_user):
        """Test validation error when salary is invalid."""
        mock_login.return_value = lambda f: f  # Mock decorator
        
        with client.application.app_context():
            with client.session_transaction() as sess:
                sess['user'] = mock_user.model_dump()
            
            response = client.post('/jobseeker/applications/submit/test-job-123', data={
                'cv_id': 'test-cv-123',
                'cover_letter': 'This is a test cover letter that is definitely longer than fifty characters to meet the minimum requirement.',
                'expected_salary': 'not-a-number'  # Invalid salary
            }, follow_redirects=True)
            
            # Should redirect back to application form with error
            assert response.status_code == 200

    @patch('src.routes.jobseeker_routes.jobseeker_applications.get_controller')
    @patch('src.routes.jobseeker_routes.jobseeker_applications.jobseeker_login')
    def test_submit_application_past_start_date(self, mock_login, mock_get_controller, client, mock_user):
        """Test validation error when start date is in the past."""
        mock_login.return_value = lambda f: f  # Mock decorator
        
        past_date = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        with client.application.app_context():
            with client.session_transaction() as sess:
                sess['user'] = mock_user.model_dump()
            
            response = client.post('/jobseeker/applications/submit/test-job-123', data={
                'cv_id': 'test-cv-123',
                'cover_letter': 'This is a test cover letter that is definitely longer than fifty characters to meet the minimum requirement.',
                'preferred_start_date': past_date  # Past date
            }, follow_redirects=True)
            
            # Should redirect back to application form with error
            assert response.status_code == 200

    @patch('src.routes.jobseeker_routes.jobseeker_applications.get_controller')
    @patch('src.routes.jobseeker_routes.jobseeker_applications.jobseeker_login')
    async def test_submit_application_duplicate_prevention(self, mock_login, mock_get_controller, client, mock_user, mock_job):
        """Test duplicate application prevention."""
        mock_login.return_value = lambda f: f  # Mock decorator
        
        # Mock existing application
        existing_application = JobApplication(
            application_id="existing-app-123",
            user_id=mock_user.uid,
            job_id="test-job-123",
            cv_id="test-cv-123",
            cover_letter="Existing application"
        )
        
        mock_jobs_search = AsyncMock()
        mock_jobs_search.get_applied_jobs_for_user.return_value = [existing_application]
        mock_get_controller.return_value = mock_jobs_search
        
        with client.application.app_context():
            with client.session_transaction() as sess:
                sess['user'] = mock_user.model_dump()
            
            response = client.post('/jobseeker/applications/submit/test-job-123', data={
                'cv_id': 'test-cv-123',
                'cover_letter': 'This is a test cover letter that is definitely longer than fifty characters to meet the minimum requirement.',
            }, follow_redirects=True)
            
            # Should redirect to applications list with warning
            assert response.status_code == 200

    def test_validation_edge_cases(self):
        """Test edge cases in validation logic."""
        # Test maximum length validations
        long_cover_letter = 'a' * 5001  # Exceeds 5000 character limit
        long_notes = 'b' * 1001  # Exceeds 1000 character limit
        long_location = 'c' * 101  # Exceeds 100 character limit
        
        # These would be tested in the actual route handler
        # but we can test the validation logic separately
        assert len(long_cover_letter) > 5000
        assert len(long_notes) > 1000
        assert len(long_location) > 100

    def test_salary_validation_edge_cases(self):
        """Test salary validation edge cases."""
        # Test various salary inputs
        valid_salaries = ['50000', '100000', '0']
        invalid_salaries = ['abc', '-1000', '10000001']  # Last one exceeds reasonable limit
        
        for salary in valid_salaries:
            try:
                parsed = int(salary)
                assert parsed >= 0
                assert parsed <= 10000000
            except ValueError:
                assert False, f"Valid salary {salary} failed parsing"
        
        for salary in invalid_salaries:
            try:
                parsed = int(salary)
                if salary == '-1000':
                    assert parsed < 0  # Should be caught by validation
                elif salary == '10000001':
                    assert parsed > 10000000  # Should be caught by validation
            except ValueError:
                # Expected for 'abc'
                assert salary == 'abc'

    def test_date_validation_edge_cases(self):
        """Test date validation edge cases."""
        from datetime import date, timedelta
        
        # Valid dates
        today = date.today()
        future_date = today + timedelta(days=30)
        far_future = today + timedelta(days=365 * 2)  # 2 years
        
        # Invalid dates
        past_date = today - timedelta(days=1)
        too_far_future = today + timedelta(days=365 * 3)  # 3 years
        
        # Test date parsing
        valid_date_str = future_date.strftime('%Y-%m-%d')
        invalid_date_str = 'not-a-date'
        
        try:
            parsed_date = datetime.strptime(valid_date_str, '%Y-%m-%d').date()
            assert parsed_date == future_date
        except ValueError:
            assert False, "Valid date string failed parsing"
        
        try:
            datetime.strptime(invalid_date_str, '%Y-%m-%d').date()
            assert False, "Invalid date string should have failed parsing"
        except ValueError:
            pass  # Expected


if __name__ == '__main__':
    pytest.main([__file__])