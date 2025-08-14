"""
Integration tests for Candidate Fit Analysis functionality
Tests the complete flow from frontend request to backend response
"""

import pytest
import json
from unittest.mock import Mock, patch
from flask import Flask
from src.main import create_app
from src.config import config_instance


class TestCandidateFitAnalysisIntegration:
    """Test suite for candidate fit analysis integration"""

    @pytest.fixture
    def app(self):
        """Create test Flask application"""
        config = config_instance()
        app = create_app(config=config)
        app.config['TESTING'] = True
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()

    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user"""
        user = Mock()
        user.id = "test-user-123"
        user.email = "test@example.com"
        return user

    @pytest.fixture
    def mock_cv_data(self):
        """Mock CV data"""
        return {
            "cv_id": "test-cv-456",
            "ats_description": "Software Engineer with 5 years experience in Python, Flask, and web development.",
            "skills": ["Python", "Flask", "JavaScript", "SQL"],
            "user_uid": "test-user-123"
        }

    @pytest.fixture
    def mock_job_data(self):
        """Mock job data"""
        return {
            "job_id": "test-job-789",
            "title": "Senior Software Engineer",
            "ats_description": "Looking for experienced Python developer with Flask knowledge and web development skills.",
            "company_id": "test-company-101"
        }

    @pytest.fixture
    def mock_benchmark_report(self):
        """Mock candidate benchmark report"""
        return {
            "summary": "Strong candidate with excellent technical skills matching job requirements.",
            "percentile_rank": 85.0,
            "key_strengths": [
                "Strong Python programming skills",
                "Relevant Flask framework experience",
                "Good web development background"
            ],
            "development_areas": [
                "Could benefit from more senior-level project experience",
                "Consider expanding cloud platform knowledge"
            ],
            "candidate_insights": [
                "This role offers good career progression opportunities",
                "Skills align well with job requirements"
            ],
            "cv_optimization_tips": [
                "Highlight specific Python projects and achievements",
                "Add metrics to demonstrate impact of previous work"
            ]
        }

    def test_candidate_fit_analysis_endpoint_exists(self, client):
        """Test that the candidate fit analysis endpoint exists"""
        # This will return 401 since we're not authenticated, but confirms endpoint exists
        response = client.post('/agents/employee/v1/jobs/test-job/candidate-fit-analysis')
        assert response.status_code in [401, 403]  # Authentication required

    @patch('src.controllers.agents.candidate_benchmark_controller.CandidateBenchMarkController.benchmark_for_employee')
    @patch('src.authentication.jobseeker_login')
    def test_successful_candidate_analysis(self, mock_auth, mock_benchmark, client, mock_user, mock_benchmark_report):
        """Test successful candidate fit analysis flow"""
        # Mock authentication
        mock_auth.return_value = lambda f: lambda *args, **kwargs: f(mock_user, *args, **kwargs)

        # Mock benchmark controller response
        mock_benchmark_report_obj = Mock()
        mock_benchmark_report_obj.model_dump.return_value = mock_benchmark_report
        mock_benchmark.return_value = mock_benchmark_report_obj

        # Make request
        response = client.post(
            '/agents/employee/v1/jobs/test-job-789/candidate-fit-analysis',
            json={'cv_id': 'test-cv-456'},
            headers={'Content-Type': 'application/json'}
        )

        # Verify response
        assert response.status_code == 200
        data = json.loads(response.data)

        # Verify response structure matches CandidateBenchmarkReport
        assert 'summary' in data
        assert 'percentile_rank' in data
        assert 'key_strengths' in data
        assert 'development_areas' in data
        assert 'candidate_insights' in data
        assert 'cv_optimization_tips' in data

        # Verify content
        assert data['summary'] == mock_benchmark_report['summary']
        assert data['percentile_rank'] == mock_benchmark_report['percentile_rank']
        assert len(data['key_strengths']) == 3
        assert len(data['development_areas']) == 2

    @patch('src.authentication.jobseeker_login')
    def test_missing_cv_id_validation(self, mock_auth, client, mock_user):
        """Test validation when CV ID is missing"""
        # Mock authentication
        mock_auth.return_value = lambda f: lambda *args, **kwargs: f(mock_user, *args, **kwargs)

        # Make request without cv_id
        response = client.post(
            '/agents/employee/v1/jobs/test-job-789/candidate-fit-analysis',
            json={},
            headers={'Content-Type': 'application/json'}
        )

        # Verify validation error
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'CV ID is required' in data['error']

    @patch('src.controllers.agents.candidate_benchmark_controller.CandidateBenchMarkController.benchmark_for_employee')
    @patch('src.authentication.jobseeker_login')
    def test_benchmark_controller_failure(self, mock_auth, mock_benchmark, client, mock_user):
        """Test handling when benchmark controller returns None"""
        # Mock authentication
        mock_auth.return_value = lambda f: lambda *args, **kwargs: f(mock_user, *args, **kwargs)

        # Mock benchmark controller returning None (failure)
        mock_benchmark.return_value = None

        # Make request
        response = client.post(
            '/agents/employee/v1/jobs/test-job-789/candidate-fit-analysis',
            json={'cv_id': 'test-cv-456'},
            headers={'Content-Type': 'application/json'}
        )

        # Verify error response
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Candidate fit analysis failed' in data['error']

    @patch('src.controllers.agents.candidate_benchmark_controller.CandidateBenchMarkController.benchmark_for_employee')
    @patch('src.authentication.jobseeker_login')
    def test_benchmark_controller_exception(self, mock_auth, mock_benchmark, client, mock_user):
        """Test handling when benchmark controller raises exception"""
        # Mock authentication
        mock_auth.return_value = lambda f: lambda *args, **kwargs: f(mock_user, *args, **kwargs)

        # Mock benchmark controller raising exception
        mock_benchmark.side_effect = ValueError("Test validation error")

        # Make request
        response = client.post(
            '/agents/employee/v1/jobs/test-job-789/candidate-fit-analysis',
            json={'cv_id': 'test-cv-456'},
            headers={'Content-Type': 'application/json'}
        )

        # Verify error response
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Test validation error' in data['error']

    def test_unauthenticated_request(self, client):
        """Test that unauthenticated requests are rejected"""
        response = client.post(
            '/agents/employee/v1/jobs/test-job-789/candidate-fit-analysis',
            json={'cv_id': 'test-cv-456'},
            headers={'Content-Type': 'application/json'}
        )

        # Should return 401 or 403 for unauthenticated request
        assert response.status_code in [401, 403]

    def test_invalid_json_request(self, client):
        """Test handling of invalid JSON in request"""
        response = client.post(
            '/agents/employee/v1/jobs/test-job-789/candidate-fit-analysis',
            data='invalid json',
            headers={'Content-Type': 'application/json'}
        )

        # Should handle invalid JSON gracefully
        assert response.status_code in [400, 401, 403]  # 401/403 if auth fails first

    @patch('src.controllers.agents.candidate_benchmark_controller.CandidateBenchMarkController.benchmark_for_employee')
    @patch('src.authentication.jobseeker_login')
    def test_response_format_compatibility(self, mock_auth, mock_benchmark, client, mock_user, mock_benchmark_report):
        """Test that response format is compatible with frontend expectations"""
        # Mock authentication
        mock_auth.return_value = lambda f: lambda *args, **kwargs: f(mock_user, *args, **kwargs)

        # Mock benchmark controller response
        mock_benchmark_report_obj = Mock()
        mock_benchmark_report_obj.model_dump.return_value = mock_benchmark_report
        mock_benchmark.return_value = mock_benchmark_report_obj

        # Make request
        response = client.post(
            '/agents/employee/v1/jobs/test-job-789/candidate-fit-analysis',
            json={'cv_id': 'test-cv-456'},
            headers={'Content-Type': 'application/json'}
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        # Verify all fields expected by frontend are present
        required_fields = [
            'summary', 'percentile_rank', 'key_strengths',
            'development_areas', 'candidate_insights', 'cv_optimization_tips'
        ]

        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Verify data types match frontend expectations
        assert isinstance(data['summary'], str)
        assert isinstance(data['percentile_rank'], (int, float))
        assert isinstance(data['key_strengths'], list)
        assert isinstance(data['development_areas'], list)
        assert isinstance(data['candidate_insights'], list)
        assert isinstance(data['cv_optimization_tips'], list)

        # Verify percentile_rank is in valid range
        assert 0 <= data['percentile_rank'] <= 100


class TestFrontendBackendCompatibility:
    """Test compatibility between frontend JavaScript and backend API"""

    def test_request_payload_format(self):
        """Test that frontend request format matches backend expectations"""
        # Frontend sends this format:
        frontend_payload = {
            "cv_id": "test-cv-456"
        }

        # Backend expects cv_id in request body and job_id in URL
        # This test verifies the format is correct
        assert 'cv_id' in frontend_payload
        assert isinstance(frontend_payload['cv_id'], str)
        assert frontend_payload['cv_id'] != ""

    def test_response_parsing_compatibility(self, mock_benchmark_report):
        """Test that backend response can be parsed by frontend JavaScript"""
        # Backend returns CandidateBenchmarkReport.model_dump()
        backend_response = mock_benchmark_report

        # Frontend expects these fields for display
        frontend_expected_fields = [
            'summary',  # For match summary text
            'percentile_rank',  # For match score display
            'key_strengths',  # For strengths list
            'development_areas',  # For areas for improvement
            'candidate_insights',  # For additional insights
            'cv_optimization_tips'  # For CV improvement suggestions
        ]

        for field in frontend_expected_fields:
            assert field in backend_response

        # Verify data types are JavaScript-compatible
        assert isinstance(backend_response['summary'], str)
        assert isinstance(backend_response['percentile_rank'], (int, float))

        for list_field in ['key_strengths', 'development_areas', 'candidate_insights', 'cv_optimization_tips']:
            assert isinstance(backend_response[list_field], list)
            if backend_response[list_field]:  # If not empty
                assert all(isinstance(item, str) for item in backend_response[list_field])


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
