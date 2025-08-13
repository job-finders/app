"""
Unit tests for application workflow routes
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import json

from src.routes.jobseeker_routes.application_workflow import application_workflow_bp
from src.database.models.application_workflow import ApplicationWorkflowResult, QuestionnaireResult


@pytest.fixture
def app():
    """Create Flask app for testing"""
    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(application_workflow_bp)
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def mock_user():
    """Create mock user"""
    user = Mock()
    user.id = "user-123"
    user.email = "test@example.com"
    return user


@pytest.fixture
def mock_controller():
    """Create mock application workflow controller"""
    controller = AsyncMock()
    controller.logger = Mock()
    return controller


class TestApplicationWorkflowRoutes:
    """Test application workflow route endpoints"""
    
    @patch('src.utils.route_helpers.get_controller')
    @patch('src.routes.jobseeker_routes.application_workflow.jobseeker_login')
    def test_start_application_process_success(self, mock_auth, mock_get_controller, client, mock_user, mock_controller):
        """Test successful application process start"""
        # Setup mocks
        mock_auth.return_value = lambda f: lambda *args, **kwargs: f(mock_user, *args, **kwargs)
        mock_get_controller.return_value = mock_controller
        
        # Mock controller response
        mock_result = ApplicationWorkflowResult(
            success=True,
            application_id="app-123",
            next_step="cover_letter",
            cover_letter_exists=False,
            questionnaires_required=True
        )
        mock_controller.start_application_process.return_value = mock_result
        
        # Make request
        response = client.post('/api/applications/workflow/jobs/job-456/start')
        
        # Assertions
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['application_id'] == "app-123"
        assert data['next_step'] == "cover_letter"
        
        # Verify controller was called correctly
        mock_controller.start_application_process.assert_called_once_with(
            user_id="user-123",
            job_id="job-456"
        )
    
    @patch('src.utils.route_helpers.get_controller')
    @patch('src.routes.jobseeker_routes.application_workflow.jobseeker_login')
    def test_start_application_process_failure(self, mock_auth, mock_get_controller, client, mock_user, mock_controller):
        """Test application process start failure"""
        # Setup mocks
        mock_auth.return_value = lambda f: lambda *args, **kwargs: f(mock_user, *args, **kwargs)
        mock_get_controller.return_value = mock_controller
        
        # Mock controller response
        mock_result = ApplicationWorkflowResult(
            success=False,
            message="You have already applied for this job"
        )
        mock_controller.start_application_process.return_value = mock_result
        
        # Make request
        response = client.post('/api/applications/workflow/jobs/job-456/start')
        
        # Assertions
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert "already applied" in data['message']
    
    @patch('src.utils.route_helpers.get_controller')
    @patch('src.routes.jobseeker_routes.application_workflow.jobseeker_login')
    def test_get_job_questionnaires_success(self, mock_auth, mock_get_controller, client, mock_user, mock_controller):
        """Test successful questionnaire retrieval"""
        # Setup mocks
        mock_auth.return_value = lambda f: lambda *args, **kwargs: f(mock_user, *args, **kwargs)
        mock_get_controller.return_value = mock_controller
        
        # Mock controller response
        mock_result = QuestionnaireResult(
            success=True,
            questionnaires=[],
            time_limit=30,
            total_questions=5
        )
        mock_controller.get_job_questionnaires.return_value = mock_result
        
        # Make request
        response = client.get('/api/applications/workflow/jobs/job-456/questionnaires')
        
        # Assertions
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['time_limit'] == 30
        assert data['total_questions'] == 5
        
        # Verify controller was called correctly
        mock_controller.get_job_questionnaires.assert_called_once_with(job_id="job-456")
    
    @patch('src.utils.route_helpers.get_controller')
    @patch('src.routes.jobseeker_routes.application_workflow.jobseeker_login')
    def test_get_application_status_success(self, mock_auth, mock_get_controller, client, mock_user, mock_controller):
        """Test successful application status retrieval"""
        # Setup mocks
        mock_auth.return_value = lambda f: lambda *args, **kwargs: f(mock_user, *args, **kwargs)
        mock_get_controller.return_value = mock_controller
        
        # Mock controller response
        mock_result = {
            "success": True,
            "application_id": "app-123",
            "workflow_step": "cover_letter",
            "completion_percentage": 40,
            "next_step": "questionnaires"
        }
        mock_controller.get_application_status.return_value = mock_result
        
        # Make request
        response = client.get('/api/applications/workflow/applications/app-123/status')
        
        # Assertions
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['application_id'] == "app-123"
        assert data['workflow_step'] == "cover_letter"
        assert data['completion_percentage'] == 40
        
        # Verify controller was called correctly
        mock_controller.get_application_status.assert_called_once_with(
            application_id="app-123",
            user_id="user-123"
        )
    
    @patch('src.utils.route_helpers.get_controller')
    @patch('src.routes.jobseeker_routes.application_workflow.jobseeker_login')
    def test_get_application_status_not_found(self, mock_auth, mock_get_controller, client, mock_user, mock_controller):
        """Test application status not found"""
        # Setup mocks
        mock_auth.return_value = lambda f: lambda *args, **kwargs: f(mock_user, *args, **kwargs)
        mock_get_controller.return_value = mock_controller
        
        # Mock controller response
        mock_result = {
            "success": False,
            "message": "Application not found"
        }
        mock_controller.get_application_status.return_value = mock_result
        
        # Make request
        response = client.get('/api/applications/workflow/applications/nonexistent/status')
        
        # Assertions
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert "not found" in data['message']
    
    @patch('src.utils.route_helpers.get_controller')
    @patch('src.routes.jobseeker_routes.application_workflow.jobseeker_login')
    def test_create_cover_letter_session_success(self, mock_auth, mock_get_controller, client, mock_user, mock_controller):
        """Test successful cover letter session creation"""
        # Setup mocks
        mock_auth.return_value = lambda f: lambda *args, **kwargs: f(mock_user, *args, **kwargs)
        mock_get_controller.return_value = mock_controller
        
        # Mock controller response
        mock_result = {
            "success": True,
            "session_id": "session-123",
            "message": "Created new cover letter session"
        }
        mock_controller.create_cover_letter_session.return_value = mock_result
        
        # Request data
        request_data = {
            "job_id": "job-456",
            "cv_id": "cv-789",
            "draft_text": "I am interested in this position...",
            "selected_tone": "professional"
        }
        
        # Make request
        response = client.post(
            '/api/applications/workflow/cover-letter/sessions',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        # Assertions
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['session_id'] == "session-123"
        
        # Verify controller was called correctly
        mock_controller.create_cover_letter_session.assert_called_once_with(
            user_id="user-123",
            job_id="job-456",
            cv_id="cv-789",
            draft_text="I am interested in this position...",
            selected_tone="professional"
        )
    
    @patch('src.utils.route_helpers.get_controller')
    @patch('src.routes.jobseeker_routes.application_workflow.jobseeker_login')
    def test_create_cover_letter_session_missing_job_id(self, mock_auth, mock_get_controller, client, mock_user, mock_controller):
        """Test cover letter session creation with missing job_id"""
        # Setup mocks
        mock_auth.return_value = lambda f: lambda *args, **kwargs: f(mock_user, *args, **kwargs)
        mock_get_controller.return_value = mock_controller
        
        # Request data without job_id
        request_data = {
            "draft_text": "I am interested in this position..."
        }
        
        # Make request
        response = client.post(
            '/api/applications/workflow/cover-letter/sessions',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        # Assertions
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert "job_id is required" in data['message']
        
        # Verify controller was not called
        mock_controller.create_cover_letter_session.assert_not_called()
    
    @patch('src.utils.route_helpers.get_controller')
    @patch('src.routes.jobseeker_routes.application_workflow.jobseeker_login')
    def test_link_cover_letter_to_application_success(self, mock_auth, mock_get_controller, client, mock_user, mock_controller):
        """Test successful cover letter linking"""
        # Setup mocks
        mock_auth.return_value = lambda f: lambda *args, **kwargs: f(mock_user, *args, **kwargs)
        mock_get_controller.return_value = mock_controller
        
        # Mock controller response
        mock_result = {
            "success": True,
            "message": "Cover letter linked to application"
        }
        mock_controller.link_cover_letter_to_application.return_value = mock_result
        
        # Request data
        request_data = {
            "session_id": "session-123"
        }
        
        # Make request
        response = client.post(
            '/api/applications/workflow/applications/app-456/cover-letter',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        # Assertions
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert "linked" in data['message']
        
        # Verify controller was called correctly
        mock_controller.link_cover_letter_to_application.assert_called_once_with(
            application_id="app-456",
            session_id="session-123",
            user_id="user-123"
        )
    
    @patch('src.utils.route_helpers.get_controller')
    @patch('src.routes.jobseeker_routes.application_workflow.jobseeker_login')
    def test_link_cover_letter_missing_session_id(self, mock_auth, mock_get_controller, client, mock_user, mock_controller):
        """Test cover letter linking with missing session_id"""
        # Setup mocks
        mock_auth.return_value = lambda f: lambda *args, **kwargs: f(mock_user, *args, **kwargs)
        mock_get_controller.return_value = mock_controller
        
        # Request data without session_id
        request_data = {}
        
        # Make request
        response = client.post(
            '/api/applications/workflow/applications/app-456/cover-letter',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        # Assertions
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert "session_id is required" in data['message']
        
        # Verify controller was not called
        mock_controller.link_cover_letter_to_application.assert_not_called()
    
    @patch('src.utils.route_helpers.get_controller')
    @patch('src.routes.jobseeker_routes.application_workflow.jobseeker_login')
    def test_start_questionnaire_timer_success(self, mock_auth, mock_get_controller, client, mock_user, mock_controller):
        """Test successful questionnaire timer start"""
        # Setup mocks
        mock_auth.return_value = lambda f: lambda *args, **kwargs: f(mock_user, *args, **kwargs)
        mock_get_controller.return_value = mock_controller
        
        # Mock controller response
        mock_result = {
            "success": True,
            "message": "Questionnaire timer started",
            "started_at": "2024-01-01T10:00:00",
            "time_limit_minutes": 30,
            "total_questions": 5
        }
        mock_controller.start_questionnaire_timer.return_value = mock_result
        
        # Make request
        response = client.post('/api/applications/workflow/applications/app-123/questionnaires/timer/start')
        
        # Assertions
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['time_limit_minutes'] == 30
        assert data['total_questions'] == 5
        
        # Verify controller was called correctly
        mock_controller.start_questionnaire_timer.assert_called_once_with(
            application_id="app-123",
            user_id="user-123"
        )
    
    @patch('src.utils.route_helpers.get_controller')
    @patch('src.routes.jobseeker_routes.application_workflow.jobseeker_login')
    def test_route_exception_handling(self, mock_auth, mock_get_controller, client, mock_user, mock_controller):
        """Test route exception handling"""
        # Setup mocks
        mock_auth.return_value = lambda f: lambda *args, **kwargs: f(mock_user, *args, **kwargs)
        mock_get_controller.return_value = mock_controller
        
        # Mock controller to raise exception
        mock_controller.start_application_process.side_effect = Exception("Database error")
        
        # Make request
        response = client.post('/api/applications/workflow/jobs/job-456/start')
        
        # Assertions
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert "Failed to start application process" in data['message']
        assert "Database error" in data['error']
    
    @patch('src.utils.route_helpers.get_controller')
    @patch('src.routes.jobseeker_routes.application_workflow.jobseeker_login')
    def test_empty_json_request_handling(self, mock_auth, mock_get_controller, client, mock_user, mock_controller):
        """Test handling of empty JSON requests"""
        # Setup mocks
        mock_auth.return_value = lambda f: lambda *args, **kwargs: f(mock_user, *args, **kwargs)
        mock_get_controller.return_value = mock_controller
        
        # Make request with empty JSON
        response = client.post(
            '/api/applications/workflow/cover-letter/sessions',
            data=json.dumps({}),
            content_type='application/json'
        )
        
        # Assertions
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert "job_id is required" in data['message']
    
    @patch('src.utils.route_helpers.get_controller')
    @patch('src.routes.jobseeker_routes.application_workflow.jobseeker_login')
    def test_no_json_request_handling(self, mock_auth, mock_get_controller, client, mock_user, mock_controller):
        """Test handling of requests without JSON"""
        # Setup mocks
        mock_auth.return_value = lambda f: lambda *args, **kwargs: f(mock_user, *args, **kwargs)
        mock_get_controller.return_value = mock_controller
        
        # Make request without JSON
        response = client.post('/api/applications/workflow/cover-letter/sessions')
        
        # Assertions
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert "job_id is required" in data['message']
    
@patch('src.utils.route_helpers.get_controller')
    @patch('src.routes.jobseeker_routes.application_workflow.jobseeker_login')
    def test_submit_questionnaire_answers_success(self, mock_auth, mock_get_controller, client, mock_user, mock_controller):
        """Test successful questionnaire answer submission"""
        # Setup mocks
        mock_auth.return_value = lambda f: lambda *args, **kwargs: f(mock_user, *args, **kwargs)
        mock_get_controller.return_value = mock_controller
        
        # Mock controller response
        from src.database.models.application_workflow import SubmissionResult
        mock_result = SubmissionResult(
            success=True,
            message="Questionnaire answers saved successfully",
            application_id="app-123",
            next_step="review"
        )
        mock_controller.submit_questionnaire_answers.return_value = mock_result
        
        # Request data
        request_data = {
            "answers": {
                "q1": ["Answer 1"],
                "q2": ["Option A", "Option B"],
                "q3": ["5"]
            },
            "time_spent_seconds": 1800
        }
        
        # Make request
        response = client.post(
            '/api/applications/workflow/applications/app-123/questionnaires',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        # Assertions
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['next_step'] == "review"
        
        # Verify controller was called correctly
        mock_controller.submit_questionnaire_answers.assert_called_once_with(
            application_id="app-123",
            answers=request_data["answers"],
            user_id="user-123",
            time_spent_seconds=1800
        )
    
    @patch('src.utils.route_helpers.get_controller')
    @patch('src.routes.jobseeker_routes.application_workflow.jobseeker_login')
    def test_submit_questionnaire_answers_missing_answers(self, mock_auth, mock_get_controller, client, mock_user, mock_controller):
        """Test questionnaire submission with missing answers"""
        # Setup mocks
        mock_auth.return_value = lambda f: lambda *args, **kwargs: f(mock_user, *args, **kwargs)
        mock_get_controller.return_value = mock_controller
        
        # Request data without answers
        request_data = {
            "time_spent_seconds": 1800
        }
        
        # Make request
        response = client.post(
            '/api/applications/workflow/applications/app-123/questionnaires',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        # Assertions
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert "answers dictionary is required" in data['message']
        
        # Verify controller was not called
        mock_controller.submit_questionnaire_answers.assert_not_called()
    
    @patch('src.utils.route_helpers.get_controller')
    @patch('src.routes.jobseeker_routes.application_workflow.jobseeker_login')
    def test_submit_questionnaire_answers_validation_failure(self, mock_auth, mock_get_controller, client, mock_user, mock_controller):
        """Test questionnaire submission with validation failure"""
        # Setup mocks
        mock_auth.return_value = lambda f: lambda *args, **kwargs: f(mock_user, *args, **kwargs)
        mock_get_controller.return_value = mock_controller
        
        # Mock controller response with validation failure
        from src.database.models.application_workflow import SubmissionResult
        mock_result = SubmissionResult(
            success=False,
            message="Please complete all required questions",
            missing_fields=["Question 1", "Question 3"]
        )
        mock_controller.submit_questionnaire_answers.return_value = mock_result
        
        # Request data
        request_data = {
            "answers": {
                "q2": ["Partial answer"]
            }
        }
        
        # Make request
        response = client.post(
            '/api/applications/workflow/applications/app-123/questionnaires',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        # Assertions
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert "complete all required questions" in data['message']
        assert data['missing_fields'] == ["Question 1", "Question 3"]
    
    @patch('src.utils.route_helpers.get_controller')
    @patch('src.routes.jobseeker_routes.application_workflow.jobseeker_login')
    def test_submit_application_success(self, mock_auth, mock_get_controller, client, mock_user, mock_controller):
        """Test successful final application submission"""
        # Setup mocks
        mock_auth.return_value = lambda f: lambda *args, **kwargs: f(mock_user, *args, **kwargs)
        mock_get_controller.return_value = mock_controller
        
        # Mock controller response
        from src.database.models.application_workflow import SubmissionResult
        mock_result = SubmissionResult(
            success=True,
            message="Application submitted successfully",
            application_id="app-123",
            validation_score=95
        )
        mock_controller.submit_application.return_value = mock_result
        
        # Make request
        response = client.post('/api/applications/workflow/applications/app-123/submit')
        
        # Assertions
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['application_id'] == "app-123"
        assert data['validation_score'] == 95
        
        # Verify controller was called correctly
        mock_controller.submit_application.assert_called_once_with(
            application_id="app-123",
            user_id="user-123"
        )
    
    @patch('src.utils.route_helpers.get_controller')
    @patch('src.routes.jobseeker_routes.application_workflow.jobseeker_login')
    def test_submit_application_validation_failure(self, mock_auth, mock_get_controller, client, mock_user, mock_controller):
        """Test application submission with validation failure"""
        # Setup mocks
        mock_auth.return_value = lambda f: lambda *args, **kwargs: f(mock_user, *args, **kwargs)
        mock_get_controller.return_value = mock_controller
        
        # Mock controller response with validation failure
        from src.database.models.application_workflow import SubmissionResult
        mock_result = SubmissionResult(
            success=False,
            message="Application validation failed",
            missing_requirements=["Cover letter is required", "CV selection is required"],
            validation_score=45
        )
        mock_controller.submit_application.return_value = mock_result
        
        # Make request
        response = client.post('/api/applications/workflow/applications/app-123/submit')
        
        # Assertions
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert "validation failed" in data['message']
        assert len(data['missing_requirements']) == 2
        assert data['validation_score'] == 45
    
    @patch('src.utils.route_helpers.get_controller')
    @patch('src.routes.jobseeker_routes.application_workflow.jobseeker_login')
    def test_validate_application_success(self, mock_auth, mock_get_controller, client, mock_user, mock_controller):
        """Test successful application validation"""
        # Setup mocks
        mock_auth.return_value = lambda f: lambda *args, **kwargs: f(mock_user, *args, **kwargs)
        mock_get_controller.return_value = mock_controller
        
        # Mock controller response
        mock_status_result = {
            "success": True,
            "application_id": "app-123",
            "validation_score": 85,
            "completion_percentage": 90,
            "workflow_step": "review",
            "next_step": None,
            "is_complete": False,
            "has_cover_letter": True,
            "has_ats_report": True,
            "questionnaires_completed": True
        }
        mock_controller.get_application_status.return_value = mock_status_result
        
        # Make request
        response = client.post('/api/applications/workflow/applications/app-123/validate')
        
        # Assertions
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['is_valid'] is True  # Score >= 70
        assert data['validation_score'] == 85
        assert len(data['missing_requirements']) == 0
        assert data['validation_details']['has_cover_letter'] is True
    
    @patch('src.utils.route_helpers.get_controller')
    @patch('src.routes.jobseeker_routes.application_workflow.jobseeker_login')
    def test_validate_application_with_missing_requirements(self, mock_auth, mock_get_controller, client, mock_user, mock_controller):
        """Test application validation with missing requirements"""
        # Setup mocks
        mock_auth.return_value = lambda f: lambda *args, **kwargs: f(mock_user, *args, **kwargs)
        mock_get_controller.return_value = mock_controller
        
        # Mock controller response with missing requirements
        mock_status_result = {
            "success": True,
            "application_id": "app-123",
            "validation_score": 45,
            "completion_percentage": 40,
            "workflow_step": "draft",
            "next_step": "cover_letter",
            "is_complete": False,
            "has_cover_letter": False,
            "has_ats_report": False,
            "questionnaires_completed": False
        }
        mock_controller.get_application_status.return_value = mock_status_result
        
        # Make request
        response = client.post('/api/applications/workflow/applications/app-123/validate')
        
        # Assertions
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['is_valid'] is False  # Score < 70
        assert data['validation_score'] == 45
        assert len(data['missing_requirements']) > 0
        assert "Cover letter is required" in data['missing_requirements']
        assert data['validation_details']['has_cover_letter'] is False
    
    @patch('src.utils.route_helpers.get_controller')
    @patch('src.routes.jobseeker_routes.application_workflow.jobseeker_login')
    def test_get_application_progress_success(self, mock_auth, mock_get_controller, client, mock_user, mock_controller):
        """Test successful application progress retrieval"""
        # Setup mocks
        mock_auth.return_value = lambda f: lambda *args, **kwargs: f(mock_user, *args, **kwargs)
        mock_get_controller.return_value = mock_controller
        
        # Mock controller response
        mock_status_result = {
            "success": True,
            "application_id": "app-123",
            "workflow_step": "questionnaires",
            "workflow_step_display": "Questionnaires Completed",
            "completion_percentage": 70,
            "next_step": "review",
            "is_complete": False,
            "has_cover_letter": True,
            "questionnaires_completed": True,
            "validation_score": 80,
            "applied_date": "2024-01-01T10:00:00",
            "workflow_duration_minutes": 45.5
        }
        mock_controller.get_application_status.return_value = mock_status_result
        
        # Make request
        response = client.get('/api/applications/workflow/applications/app-123/progress')
        
        # Assertions
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['current_step'] == "questionnaires"
        assert data['completion_percentage'] == 70
        assert len(data['steps']) == 5
        
        # Check step details
        cover_letter_step = next(step for step in data['steps'] if step['step'] == 'cover_letter')
        assert cover_letter_step['completed'] is True
        
        questionnaires_step = next(step for step in data['steps'] if step['step'] == 'questionnaires')
        assert questionnaires_step['current'] is True
    
    @patch('src.utils.route_helpers.get_controller')
    @patch('src.routes.jobseeker_routes.application_workflow.jobseeker_login')
    def test_get_application_progress_not_found(self, mock_auth, mock_get_controller, client, mock_user, mock_controller):
        """Test application progress for non-existent application"""
        # Setup mocks
        mock_auth.return_value = lambda f: lambda *args, **kwargs: f(mock_user, *args, **kwargs)
        mock_get_controller.return_value = mock_controller
        
        # Mock controller response
        mock_status_result = {
            "success": False,
            "message": "Application not found"
        }
        mock_controller.get_application_status.return_value = mock_status_result
        
        # Make request
        response = client.get('/api/applications/workflow/applications/nonexistent/progress')
        
        # Assertions
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert "not found" in data['message']