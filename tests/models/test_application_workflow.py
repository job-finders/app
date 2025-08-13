"""
Unit tests for application workflow Pydantic models
"""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError

from src.database.models.application_workflow import (
    ApplicationWorkflowResult,
    QuestionnaireQuestion,
    Questionnaire,
    QuestionnaireResult,
    ValidationResult,
    SubmissionResult,
    CoverLetterSession,
    QuestionnaireAnswer,
    QuestionnaireSubmission,
    ApplicationProgress,
    WorkflowStepEnum,
    QuestionTypeEnum
)


class TestApplicationWorkflowResult:
    """Test ApplicationWorkflowResult model"""
    
    def test_valid_workflow_result(self):
        """Test creating valid workflow result"""
        result = ApplicationWorkflowResult(
            success=True,
            application_id="test-app-123",
            next_step="cover_letter",
            cover_letter_exists=False,
            questionnaires_required=True
        )
        
        assert result.success is True
        assert result.application_id == "test-app-123"
        assert result.next_step == "cover_letter"
        assert result.cover_letter_exists is False
        assert result.questionnaires_required is True
    
    def test_minimal_workflow_result(self):
        """Test creating minimal workflow result"""
        result = ApplicationWorkflowResult(success=False)
        
        assert result.success is False
        assert result.application_id is None
        assert result.next_step is None


class TestQuestionnaireQuestion:
    """Test QuestionnaireQuestion model"""
    
    def test_valid_text_question(self):
        """Test creating valid text question"""
        question = QuestionnaireQuestion(
            question_text="What is your experience with Python?",
            question_type=QuestionTypeEnum.TEXT,
            required=True,
            max_length=500
        )
        
        assert question.question_text == "What is your experience with Python?"
        assert question.question_type == QuestionTypeEnum.TEXT
        assert question.required is True
        assert question.max_length == 500
    
    def test_valid_multiple_choice_question(self):
        """Test creating valid multiple choice question"""
        question = QuestionnaireQuestion(
            question_text="What is your preferred work environment?",
            question_type=QuestionTypeEnum.MULTIPLE_CHOICE,
            options=["Remote", "Office", "Hybrid"]
        )
        
        assert question.question_type == QuestionTypeEnum.MULTIPLE_CHOICE
        assert len(question.options) == 3
        assert "Remote" in question.options
    
    def test_multiple_choice_validation_error(self):
        """Test multiple choice question with insufficient options"""
        with pytest.raises(ValidationError):
            QuestionnaireQuestion(
                question_text="Choose one:",
                question_type=QuestionTypeEnum.MULTIPLE_CHOICE,
                options=["Only one option"]
            )
    
    def test_rating_question_validation(self):
        """Test rating question validation"""
        question = QuestionnaireQuestion(
            question_text="Rate your Python skills",
            question_type=QuestionTypeEnum.RATING,
            min_rating=1,
            max_rating=5
        )
        
        assert question.min_rating == 1
        assert question.max_rating == 5
    
    def test_invalid_rating_range(self):
        """Test invalid rating range"""
        with pytest.raises(ValidationError):
            QuestionnaireQuestion(
                question_text="Rate your skills",
                question_type=QuestionTypeEnum.RATING,
                min_rating=5,
                max_rating=3  # max should be greater than min
            )


class TestQuestionnaire:
    """Test Questionnaire model"""
    
    def test_valid_questionnaire(self):
        """Test creating valid questionnaire"""
        questions = [
            QuestionnaireQuestion(
                question_text="What is your experience?",
                question_type=QuestionTypeEnum.TEXT
            )
        ]
        
        questionnaire = Questionnaire(
            title="Technical Assessment",
            description="Basic technical questions",
            time_limit=45,
            questions=questions
        )
        
        assert questionnaire.title == "Technical Assessment"
        assert questionnaire.time_limit == 45
        assert questionnaire.total_questions == 1
        assert questionnaire.required_questions_count == 1
    
    def test_empty_questionnaire_validation(self):
        """Test questionnaire with no questions fails validation"""
        with pytest.raises(ValidationError):
            Questionnaire(
                title="Empty Questionnaire",
                questions=[]
            )


class TestCoverLetterSession:
    """Test CoverLetterSession model"""
    
    def test_valid_cover_letter_session(self):
        """Test creating valid cover letter session"""
        session = CoverLetterSession(
            user_id="user-123",
            job_id="job-456",
            draft_text="I am interested in this position...",
            selected_tone="professional"
        )
        
        assert session.user_id == "user-123"
        assert session.job_id == "job-456"
        assert session.selected_tone == "professional"
        assert session.is_active is True
        assert not session.is_expired
    
    def test_invalid_tone_validation(self):
        """Test invalid tone validation"""
        with pytest.raises(ValidationError):
            CoverLetterSession(
                user_id="user-123",
                job_id="job-456",
                selected_tone="invalid_tone"
            )
    
    def test_session_expiry(self):
        """Test session expiry logic"""
        past_time = datetime.utcnow() - timedelta(hours=25)
        session = CoverLetterSession(
            user_id="user-123",
            job_id="job-456",
            expires_at=past_time
        )
        
        assert session.is_expired is True
        assert session.time_remaining_hours == 0.0


class TestApplicationProgress:
    """Test ApplicationProgress model"""
    
    def test_valid_application_progress(self):
        """Test creating valid application progress"""
        progress = ApplicationProgress(
            application_id="app-123",
            current_step=WorkflowStepEnum.COVER_LETTER,
            completed_steps=["draft"],
            cover_letter_completed=False
        )
        
        assert progress.application_id == "app-123"
        assert progress.current_step == WorkflowStepEnum.COVER_LETTER
        assert progress.next_step == WorkflowStepEnum.QUESTIONNAIRES
        assert not progress.is_complete
    
    def test_completion_percentage_update(self):
        """Test completion percentage calculation"""
        progress = ApplicationProgress(
            application_id="app-123",
            current_step=WorkflowStepEnum.QUESTIONNAIRES
        )
        
        progress.update_completion_percentage()
        assert progress.completion_percentage == 70
    
    def test_workflow_completion(self):
        """Test workflow completion detection"""
        progress = ApplicationProgress(
            application_id="app-123",
            current_step=WorkflowStepEnum.SUBMITTED
        )
        
        assert progress.is_complete is True
        assert progress.next_step is None


class TestValidationResult:
    """Test ValidationResult model"""
    
    def test_valid_validation_result(self):
        """Test creating valid validation result"""
        result = ValidationResult(
            is_valid=True,
            is_complete=True,
            score=85,
            missing_fields=[],
            missing_requirements=[]
        )
        
        assert result.is_valid is True
        assert result.score == 85
        assert not result.has_errors
        assert result.error_count == 0
    
    def test_validation_with_errors(self):
        """Test validation result with errors"""
        result = ValidationResult(
            is_valid=False,
            missing_fields=["cover_letter", "cv"],
            validation_errors=["Invalid email format"]
        )
        
        assert result.has_errors is True
        assert result.error_count == 3  # 2 missing fields + 1 validation error


class TestSubmissionResult:
    """Test SubmissionResult model"""
    
    def test_successful_submission(self):
        """Test successful submission result"""
        result = SubmissionResult(
            success=True,
            message="Application submitted successfully",
            application_id="app-123",
            validation_score=90
        )
        
        assert result.success is True
        assert result.application_id == "app-123"
        assert result.validation_score == 90
        assert not result.has_missing_items
    
    def test_submission_with_missing_items(self):
        """Test submission result with missing items"""
        result = SubmissionResult(
            success=False,
            message="Missing required fields",
            missing_fields=["cover_letter"],
            missing_requirements=["cv"]
        )
        
        assert result.success is False
        assert result.has_missing_items is True