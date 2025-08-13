"""
Unit tests for ApplicationWorkflowController
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from src.controllers.applications.application_workflow_controller import ApplicationWorkflowController
from src.database.models.application_workflow import ApplicationWorkflowResult, QuestionnaireResult
from src.database.models.jobs_model import JobApplication, Job


@pytest.fixture
def mock_factory():
    """Create mock factory"""
    factory = Mock()
    return factory


@pytest.fixture
def controller(mock_factory):
    """Create controller instance"""
    return ApplicationWorkflowController(mock_factory)


@pytest.fixture
def mock_session():
    """Create mock database session"""
    session = Mock()
    session.__enter__ = Mock(return_value=session)
    session.__exit__ = Mock(return_value=None)
    return session


@pytest.fixture
def sample_job():
    """Create sample job for testing"""
    return Job(
        job_id="job-123",
        title="Software Developer",
        description="Great job opportunity",
        company_id="company-456",
        required_questionnaire=["tech-001", "general-001"]
    )


class TestApplicationWorkflowController:
    """Test ApplicationWorkflowController methods"""
    
    @pytest.mark.asyncio
    async def test_start_application_process_success(self, controller, mock_session):
        """Test successful application process start"""
        user_id = "user-123"
        job_id = "job-456"
        
        # Mock dependencies
        with patch.object(controller, 'get_session', return_value=mock_session):
            with patch.object(controller, '_check_existing_application', return_value=None):
                with patch.object(controller, '_check_cover_letter_exists', return_value=False):
                    with patch('src.utils.route_helpers.get_controller') as mock_get_controller:
                        # Mock job controller
                        mock_job_controller = AsyncMock()
                        mock_job_controller.get_job_by_id.return_value = Job(
                            job_id=job_id,
                            title="Test Job",
                            description="Test description",
                            company_id="company-123",
                            required_questionnaire=["q1", "q2"]
                        )
                        mock_get_controller.return_value = mock_job_controller
                        
                        # Mock application ORM
                        from src.database.sql.jobs_sql import JobApplicationORM
                        mock_app = Mock(spec=JobApplicationORM)
                        mock_app.application_id = "app-789"
                        mock_app.workflow_step = "draft"
                        mock_session.add = Mock()
                        mock_session.commit = Mock()
                        
                        # Mock ORM constructor
                        with patch('src.controllers.applications.application_workflow_controller.JobApplicationORM', return_value=mock_app):
                            result = await controller.start_application_process(user_id, job_id)
        
        assert result.success is True
        assert result.application_id == "app-789"
        assert result.next_step == "cover_letter"
        assert result.cover_letter_exists is False
        assert result.questionnaires_required is True
    
    @pytest.mark.asyncio
    async def test_start_application_process_duplicate(self, controller):
        """Test duplicate application prevention"""
        user_id = "user-123"
        job_id = "job-456"
        
        existing_app = JobApplication(
            application_id="existing-app",
            user_id=user_id,
            job_id=job_id,
            workflow_step="submitted"
        )
        
        with patch.object(controller, '_check_existing_application', return_value=existing_app):
            result = await controller.start_application_process(user_id, job_id)
        
        assert result.success is False
        assert "already applied" in result.message.lower()
        assert result.application_id == "existing-app"
    
    @pytest.mark.asyncio
    async def test_start_application_process_job_not_found(self, controller):
        """Test job not found scenario"""
        user_id = "user-123"
        job_id = "nonexistent-job"
        
        with patch.object(controller, '_check_existing_application', return_value=None):
            with patch('src.utils.route_helpers.get_controller') as mock_get_controller:
                mock_job_controller = AsyncMock()
                mock_job_controller.get_job_by_id.return_value = None
                mock_get_controller.return_value = mock_job_controller
                
                result = await controller.start_application_process(user_id, job_id)
        
        assert result.success is False
        assert "job not found" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_start_application_with_existing_cover_letter(self, controller, mock_session):
        """Test application start with existing cover letter"""
        user_id = "user-123"
        job_id = "job-456"
        
        with patch.object(controller, 'get_session', return_value=mock_session):
            with patch.object(controller, '_check_existing_application', return_value=None):
                with patch.object(controller, '_check_cover_letter_exists', return_value=True):
                    with patch('src.utils.route_helpers.get_controller') as mock_get_controller:
                        mock_job_controller = AsyncMock()
                        mock_job_controller.get_job_by_id.return_value = Job(
                            job_id=job_id,
                            title="Test Job",
                            description="Test description",
                            company_id="company-123",
                            required_questionnaire=["q1"]
                        )
                        mock_get_controller.return_value = mock_job_controller
                        
                        from src.database.sql.jobs_sql import JobApplicationORM
                        mock_app = Mock(spec=JobApplicationORM)
                        mock_app.application_id = "app-789"
                        mock_app.workflow_step = "cover_letter"
                        
                        with patch('src.controllers.applications.application_workflow_controller.JobApplicationORM', return_value=mock_app):
                            result = await controller.start_application_process(user_id, job_id)
        
        assert result.success is True
        assert result.next_step == "questionnaires"
        assert result.cover_letter_exists is True
    
    @pytest.mark.asyncio
    async def test_get_job_questionnaires_success(self, controller):
        """Test successful questionnaire retrieval"""
        job_id = "job-123"
        
        with patch('src.utils.route_helpers.get_controller') as mock_get_controller:
            mock_job_controller = AsyncMock()
            mock_job_controller.get_job_by_id.return_value = Job(
                job_id=job_id,
                title="Test Job",
                description="Test description",
                company_id="company-123",
                required_questionnaire=["q1", "q2"]
            )
            mock_get_controller.return_value = mock_job_controller
            
            from src.database.models.application_workflow import Questionnaire, QuestionnaireQuestion
            mock_questionnaires = [
                Questionnaire(
                    questionnaire_id="q1",
                    title="Technical Questions",
                    time_limit=30,
                    questions=[
                        QuestionnaireQuestion(
                            question_text="What is your experience?",
                            question_type="text"
                        )
                    ]
                ),
                Questionnaire(
                    questionnaire_id="q2",
                    title="General Questions",
                    time_limit=15,
                    questions=[
                        QuestionnaireQuestion(
                            question_text="Why this role?",
                            question_type="text"
                        )
                    ]
                )
            ]
            
            with patch.object(controller, '_load_questionnaires', return_value=mock_questionnaires):
                result = await controller.get_job_questionnaires(job_id)
        
        assert result.success is True
        assert len(result.questionnaires) == 2
        assert result.time_limit == 45  # 30 + 15
        assert result.total_questions == 2
    
    @pytest.mark.asyncio
    async def test_get_job_questionnaires_no_questionnaires(self, controller):
        """Test questionnaire retrieval when none required"""
        job_id = "job-123"
        
        with patch('src.utils.route_helpers.get_controller') as mock_get_controller:
            mock_job_controller = AsyncMock()
            mock_job_controller.get_job_by_id.return_value = Job(
                job_id=job_id,
                title="Test Job",
                description="Test description",
                company_id="company-123",
                required_questionnaire=[]
            )
            mock_get_controller.return_value = mock_job_controller
            
            result = await controller.get_job_questionnaires(job_id)
        
        assert result.success is True
        assert len(result.questionnaires) == 0
        assert result.time_limit == 0
        assert result.total_questions == 0
    
    @pytest.mark.asyncio
    async def test_check_existing_application(self, controller, mock_session):
        """Test existing application check"""
        user_id = "user-123"
        job_id = "job-456"
        
        # Mock existing application
        from src.database.sql.jobs_sql import JobApplicationORM
        mock_app = Mock(spec=JobApplicationORM)
        mock_app.to_dict.return_value = {
            "application_id": "app-789",
            "user_id": user_id,
            "job_id": job_id,
            "application_stage": "APPLIED",
            "workflow_step": "submitted"
        }
        
        mock_session.query.return_value.filter.return_value.first.return_value = mock_app
        
        with patch.object(controller, 'get_session', return_value=mock_session):
            result = await controller._check_existing_application(user_id, job_id)
        
        assert result is not None
        assert result.application_id == "app-789"
    
    @pytest.mark.asyncio
    async def test_check_existing_application_none(self, controller, mock_session):
        """Test existing application check when none exists"""
        user_id = "user-123"
        job_id = "job-456"
        
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        with patch.object(controller, 'get_session', return_value=mock_session):
            result = await controller._check_existing_application(user_id, job_id)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_check_cover_letter_exists(self, controller, mock_session):
        """Test cover letter existence check"""
        user_id = "user-123"
        job_id = "job-456"
        
        # Mock existing session
        from src.database.sql.questionnaires import CoverLetterSessionORM
        mock_session_orm = Mock(spec=CoverLetterSessionORM)
        mock_session.query.return_value.filter.return_value.first.return_value = mock_session_orm
        
        with patch.object(controller, 'get_session', return_value=mock_session):
            result = await controller._check_cover_letter_exists(user_id, job_id)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_cover_letter_exists_none(self, controller, mock_session):
        """Test cover letter existence check when none exists"""
        user_id = "user-123"
        job_id = "job-456"
        
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        with patch.object(controller, 'get_session', return_value=mock_session):
            result = await controller._check_cover_letter_exists(user_id, job_id)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_create_cover_letter_session_new(self, controller, mock_session):
        """Test creating new cover letter session"""
        user_id = "user-123"
        job_id = "job-456"
        
        # Mock no existing session
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # Mock new session creation
        from src.database.sql.questionnaires import CoverLetterSessionORM
        mock_session_orm = Mock(spec=CoverLetterSessionORM)
        mock_session_orm.session_id = "session-789"
        
        with patch.object(controller, 'get_session', return_value=mock_session):
            with patch('src.controllers.applications.application_workflow_controller.CoverLetterSessionORM', return_value=mock_session_orm):
                result = await controller.create_cover_letter_session(
                    user_id=user_id,
                    job_id=job_id,
                    draft_text="My draft",
                    selected_tone="professional"
                )
        
        assert result["success"] is True
        assert result["session_id"] == "session-789"
        assert "created new" in result["message"].lower()
    
    @pytest.mark.asyncio
    async def test_create_cover_letter_session_update_existing(self, controller, mock_session):
        """Test updating existing cover letter session"""
        user_id = "user-123"
        job_id = "job-456"
        
        # Mock existing session
        from src.database.sql.questionnaires import CoverLetterSessionORM
        mock_existing_session = Mock(spec=CoverLetterSessionORM)
        mock_existing_session.session_id = "existing-session"
        mock_session.query.return_value.filter.return_value.first.return_value = mock_existing_session
        
        with patch.object(controller, 'get_session', return_value=mock_session):
            result = await controller.create_cover_letter_session(
                user_id=user_id,
                job_id=job_id,
                draft_text="Updated draft",
                selected_tone="enthusiastic"
            )
        
        assert result["success"] is True
        assert result["session_id"] == "existing-session"
        assert "updated existing" in result["message"].lower()
        assert mock_existing_session.draft_text == "Updated draft"
        assert mock_existing_session.selected_tone == "enthusiastic"
    
    @pytest.mark.asyncio
    async def test_link_cover_letter_to_application_success(self, controller, mock_session):
        """Test successful cover letter linking"""
        application_id = "app-123"
        session_id = "session-456"
        user_id = "user-789"
        
        # Mock application
        from src.database.sql.jobs_sql import JobApplicationORM
        mock_app = Mock(spec=JobApplicationORM)
        
        # Mock cover letter session
        from src.database.sql.questionnaires import CoverLetterSessionORM
        mock_cover_session = Mock(spec=CoverLetterSessionORM)
        mock_cover_session.generated_letter = "Generated cover letter"
        
        mock_session.query.side_effect = [
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=mock_app)))),
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=mock_cover_session))))
        ]
        
        with patch.object(controller, 'get_session', return_value=mock_session):
            result = await controller.link_cover_letter_to_application(
                application_id, session_id, user_id
            )
        
        assert result["success"] is True
        assert mock_app.cover_letter_session_id == session_id
        assert mock_app.cover_letter == "Generated cover letter"
        assert mock_app.workflow_step == "questionnaires"
    
    @pytest.mark.asyncio
    async def test_link_cover_letter_application_not_found(self, controller, mock_session):
        """Test cover letter linking when application not found"""
        application_id = "nonexistent-app"
        session_id = "session-456"
        user_id = "user-789"
        
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        with patch.object(controller, 'get_session', return_value=mock_session):
            result = await controller.link_cover_letter_to_application(
                application_id, session_id, user_id
            )
        
        assert result["success"] is False
        assert "application not found" in result["message"].lower()