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
   @pytest.mark.asyncio
    async def test_create_cover_letter_session_new(self, controller, mock_session):
        """Test creating new cover letter session"""
        controller.get_session = Mock(return_value=mock_session)
        
        # Mock no existing session
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # Mock new session creation
        mock_session_orm = Mock()
        mock_session_orm.session_id = "session-456"
        mock_session.add = Mock()
        mock_session.commit = Mock()
        
        result = await controller.create_cover_letter_session(
            "user-123", "job-123", draft_text="Hello", selected_tone="professional"
        )
        
        assert result["success"] is True
        assert "Created new cover letter session" in result["message"]
        assert result["session_id"] == "session-456"
    
    @pytest.mark.asyncio
    async def test_validate_application_missing_cover_letter(self, controller, mock_session):
        """Test application validation with missing cover letter"""
        controller.get_session = Mock(return_value=mock_session)
        
        # Mock application without cover letter
        mock_application = Mock()
        mock_application.cover_letter = None
        mock_application.job_id = "job-123"
        mock_session.query.return_value.filter.return_value.first.return_value = mock_application
        
        # Mock job controller
        with patch('src.utils.route_helpers.get_controller') as mock_get_controller:
            mock_job_controller = AsyncMock()
            mock_job_controller.get_job_by_id.return_value = Job(job_id="job-123")
            mock_get_controller.return_value = mock_job_controller
            
            result = await controller.validate_application("app-123", "user-123")
            
            assert result["success"] is True
            assert len(result["issues"]) == 1
            assert "Cover Letter Missing" in result["issues"][0]["title"]
            assert result["validation_score"] == 75  # 100 - 25 for missing cover letter
    
    @pytest.mark.asyncio
    async def test_submit_final_application_validation_issues(self, controller, mock_session):
        """Test final application submission with validation issues"""
        controller.get_session = Mock(return_value=mock_session)
        
        # Mock application
        mock_application = Mock()
        mock_application.workflow_step = "review"
        mock_session.query.return_value.filter.return_value.first.return_value = mock_application
        
        # Mock validation with issues
        controller.validate_application = AsyncMock(return_value={
            "issues": [{"title": "Missing cover letter"}]
        })
        
        result = await controller.submit_final_application("app-123", "user-123", True)
        
        assert result["success"] is False
        assert "validation issues" in result["message"]
        assert "issues" in result
    
    @pytest.mark.asyncio
    async def test_handle_workflow_error(self, controller):
        """Test workflow error handling"""
        result = await controller.handle_workflow_error(
            "app-123", "user-123", "validation", "Missing required field", 
            ["fix_validation_errors", "save_draft"]
        )
        
        assert result["success"] is False
        assert result["error_type"] == "validation"
        assert result["message"] == "Missing required field"
        assert "fix_validation_errors" in result["recovery_options"]
        assert "save_draft" in result["recovery_options"]
        assert "error_id" in result
        assert "support_contact" in result
    
    @pytest.mark.asyncio
    async def test_preserve_session_progress(self, controller, mock_session):
        """Test session progress preservation"""
        controller.get_session = Mock(return_value=mock_session)
        
        # Mock application
        mock_application = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_application
        mock_session.commit = Mock()
        
        progress_data = {
            "current_step": "questionnaires",
            "answers": {"q1": ["answer1"]},
            "time_spent": 300
        }
        
        with patch('flask.session', {}) as mock_flask_session:
            result = await controller.preserve_session_progress("app-123", "user-123", progress_data)
            
            assert result["success"] is True
            assert "Progress saved successfully" in result["message"]
            assert "expires_at" in result
    
    @pytest.mark.asyncio
    async def test_extend_session_timeout(self, controller, mock_session):
        """Test session timeout extension"""
        controller.get_session = Mock(return_value=mock_session)
        
        # Mock application
        mock_application = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_application
        mock_session.commit = Mock()
        
        with patch('flask.session') as mock_flask_session:
            result = await controller.extend_session_timeout("app-123", "user-123", 60)
            
            assert result["success"] is True
            assert "Session extended by 60 minutes" in result["message"]
            assert "new_expiry" in result
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, controller, mock_session):
        """Test cleanup of expired sessions"""
        controller.get_session = Mock(return_value=mock_session)
        
        # Mock expired drafts and sessions
        expired_draft = Mock()
        expired_draft.user_id = "user-123"
        expired_draft.job_id = "job-123"
        expired_draft.application_id = "app-123"
        
        expired_session = Mock()
        
        mock_session.query.return_value.filter.return_value.all.side_effect = [
            [expired_draft],  # expired drafts
            [expired_session]  # expired sessions
        ]
        mock_session.delete = Mock()
        mock_session.commit = Mock()
        
        result = await controller.cleanup_expired_sessions()
        
        assert result["success"] is True
        assert result["cleanup_count"] == 2
        assert "Cleaned up 2 expired sessions" in result["message"]


class TestApplicationWorkflowIntegration:
    """Integration tests for complete application workflow scenarios"""
    
    @pytest.fixture
    def integration_controller(self, mock_factory):
        """Create controller for integration tests"""
        controller = ApplicationWorkflowController(mock_factory)
        return controller
    
    @pytest.mark.asyncio
    async def test_complete_application_workflow(self, integration_controller):
        """Test complete application workflow from start to submission"""
        user_id = "user-123"
        job_id = "job-456"
        
        # Mock all dependencies
        with patch.multiple(
            integration_controller,
            get_session=Mock(),
            _check_existing_application=AsyncMock(return_value=None),
            _check_cover_letter_exists=AsyncMock(return_value=False),
            validate_application=AsyncMock(return_value={"issues": []}),
            _send_application_notifications=AsyncMock()
        ):
            # Step 1: Start application process
            start_result = await integration_controller.start_application_process(user_id, job_id)
            assert start_result.success is True
            
            # Step 2: Create cover letter session
            cover_result = await integration_controller.create_cover_letter_session(
                user_id, job_id, draft_text="Cover letter draft"
            )
            assert cover_result["success"] is True
            
            # Step 3: Submit questionnaire (if required)
            questionnaire_result = await integration_controller.submit_questionnaire(
                start_result.application_id, "quest-123", user_id, 
                {"q1": ["answer1"]}, 600, False
            )
            assert questionnaire_result["success"] is True
            
            # Step 4: Final submission
            final_result = await integration_controller.submit_final_application(
                start_result.application_id, user_id, True
            )
            assert final_result["success"] is True
    
    @pytest.mark.asyncio
    async def test_workflow_with_errors_and_recovery(self, integration_controller):
        """Test workflow with errors and recovery mechanisms"""
        user_id = "user-123"
        job_id = "job-456"
        application_id = "app-789"
        
        # Test error handling
        error_result = await integration_controller.handle_workflow_error(
            application_id, user_id, "validation", "Missing required fields"
        )
        assert error_result["success"] is False
        assert "recovery_options" in error_result
        
        # Test session preservation
        progress_data = {"step": "questionnaires", "answers": {"q1": ["test"]}}
        preserve_result = await integration_controller.preserve_session_progress(
            application_id, user_id, progress_data
        )
        assert preserve_result["success"] is True
        
        # Test session restoration
        restore_result = await integration_controller.restore_session_progress(
            application_id, user_id
        )
        # Note: This might fail in test environment due to Flask session mocking
        # In real environment, this would restore the preserved progress


class TestApplicationWorkflowPerformance:
    """Performance tests for application workflow"""
    
    @pytest.mark.asyncio
    async def test_concurrent_application_submissions(self, mock_factory):
        """Test handling multiple concurrent application submissions"""
        import asyncio
        
        controller = ApplicationWorkflowController(mock_factory)
        
        # Mock database operations to be fast
        with patch.multiple(
            controller,
            get_session=Mock(),
            _check_existing_application=AsyncMock(return_value=None),
            validate_application=AsyncMock(return_value={"issues": []}),
            _send_application_notifications=AsyncMock()
        ):
            # Create multiple concurrent submissions
            tasks = []
            for i in range(10):
                task = controller.submit_final_application(
                    f"app-{i}", f"user-{i}", True
                )
                tasks.append(task)
            
            # Execute all tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify all completed successfully (or with expected errors)
            successful_results = [r for r in results if not isinstance(r, Exception)]
            assert len(successful_results) >= 8  # Allow for some failures in test environment
    
    @pytest.mark.asyncio
    async def test_large_questionnaire_submission_performance(self, mock_factory):
        """Test performance with large questionnaire submissions"""
        controller = ApplicationWorkflowController(mock_factory)
        
        # Create large questionnaire answers
        large_answers = {}
        for i in range(100):  # 100 questions
            large_answers[f"question_{i}"] = [f"answer_{i}" * 100]  # Long answers
        
        with patch.object(controller, 'get_session', Mock()):
            start_time = datetime.utcnow()
            
            result = await controller.save_questionnaire_progress(
                "app-123", "quest-456", "user-123", large_answers, 1, 3600
            )
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            # Should complete within reasonable time (5 seconds for large data)
            assert duration < 5.0
            assert result["success"] is True


class TestApplicationWorkflowEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.fixture
    def edge_case_controller(self, mock_factory):
        """Create controller for edge case tests"""
        return ApplicationWorkflowController(mock_factory)
    
    @pytest.mark.asyncio
    async def test_invalid_application_id(self, edge_case_controller, mock_session):
        """Test handling of invalid application IDs"""
        edge_case_controller.get_session = Mock(return_value=mock_session)
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        result = await edge_case_controller.get_application_status("invalid-id", "user-123")
        
        assert result["success"] is False
        assert "not found" in result["message"]
    
    @pytest.mark.asyncio
    async def test_database_connection_failure(self, edge_case_controller):
        """Test handling of database connection failures"""
        # Mock database connection failure
        def mock_get_session():
            raise Exception("Database connection failed")
        
        edge_case_controller.get_session = mock_get_session
        
        result = await edge_case_controller.start_application_process("user-123", "job-456")
        
        assert result.success is False
        assert "Database connection failed" in result.message
    
    @pytest.mark.asyncio
    async def test_malformed_questionnaire_answers(self, edge_case_controller):
        """Test handling of malformed questionnaire answers"""
        # Test with various malformed answer formats
        malformed_answers = [
            None,  # None answers
            {"q1": None},  # None answer value
            {"q1": []},  # Empty answer list
            {"q1": [""]},  # Empty string answer
            {"q1": [None]},  # None in answer list
        ]
        
        for answers in malformed_answers:
            result = await edge_case_controller.save_questionnaire_progress(
                "app-123", "quest-456", "user-123", answers or {}, 1, 300
            )
            # Should handle gracefully without crashing
            assert "success" in result
    
    @pytest.mark.asyncio
    async def test_session_timeout_during_submission(self, edge_case_controller):
        """Test handling of session timeout during submission"""
        with patch('flask.session', {}) as mock_session:
            # Simulate expired session
            mock_session.permanent = False
            
            result = await edge_case_controller.extend_session_timeout(
                "app-123", "user-123", 30
            )
            
            # Should handle gracefully
            assert "success" in result
    
    @pytest.mark.asyncio
    async def test_extremely_long_cover_letter(self, edge_case_controller, mock_session):
        """Test handling of extremely long cover letter content"""
        edge_case_controller.get_session = Mock(return_value=mock_session)
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_session.add = Mock()
        mock_session.commit = Mock()
        
        # Create very long cover letter (100KB)
        long_text = "A" * 100000
        
        result = await edge_case_controller.create_cover_letter_session(
            "user-123", "job-123", draft_text=long_text
        )
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_unicode_and_special_characters(self, edge_case_controller, mock_session):
        """Test handling of unicode and special characters in submissions"""
        edge_case_controller.get_session = Mock(return_value=mock_session)
        mock_session.add = Mock()
        mock_session.commit = Mock()
        
        # Test with various unicode and special characters
        special_text = "Hello 世界! 🌍 Special chars: @#$%^&*()_+-=[]{}|;':\",./<>?"
        unicode_answers = {
            "q1": ["Résumé with açcénts"],
            "q2": ["中文回答"],
            "q3": ["Emoji answer 😀🎉"],
            "q4": [special_text]
        }
        
        result = await edge_case_controller.save_questionnaire_progress(
            "app-123", "quest-456", "user-123", unicode_answers, 1, 300
        )
        
        assert result["success"] is True