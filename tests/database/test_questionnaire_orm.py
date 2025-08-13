"""
Unit tests for questionnaire SQLAlchemy ORM models
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from src.database.sql.questionnaires import (
    QuestionnaireORM,
    QuestionnaireQuestionORM,
    CoverLetterSessionORM,
    QuestionnaireSubmissionORM,
    QuestionnaireAnswerORM
)

# Test database setup
Base = declarative_base()
engine = create_engine('sqlite:///:memory:', echo=False)
TestSession = sessionmaker(bind=engine)


@pytest.fixture
def db_session():
    """Create test database session"""
    Base.metadata.create_all(engine)
    session = TestSession()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


class TestQuestionnaireORM:
    """Test QuestionnaireORM model"""
    
    def test_create_questionnaire(self, db_session):
        """Test creating a questionnaire"""
        questionnaire = QuestionnaireORM(
            title="Test Questionnaire",
            description="A test questionnaire",
            time_limit=30
        )
        
        db_session.add(questionnaire)
        db_session.commit()
        
        assert questionnaire.questionnaire_id is not None
        assert questionnaire.title == "Test Questionnaire"
        assert questionnaire.time_limit == 30
        assert questionnaire.is_active is True
    
    def test_questionnaire_to_dict(self, db_session):
        """Test questionnaire to_dict method"""
        questionnaire = QuestionnaireORM(
            title="Test Questionnaire",
            description="Test description"
        )
        
        db_session.add(questionnaire)
        db_session.commit()
        
        data = questionnaire.to_dict()
        
        assert 'questionnaire_id' in data
        assert data['title'] == "Test Questionnaire"
        assert data['description'] == "Test description"
        assert 'created_at' in data
    
    def test_questionnaire_properties(self, db_session):
        """Test questionnaire computed properties"""
        questionnaire = QuestionnaireORM(title="Test")
        db_session.add(questionnaire)
        db_session.commit()
        
        # Add questions
        question1 = QuestionnaireQuestionORM(
            questionnaire_id=questionnaire.questionnaire_id,
            question_text="Question 1",
            question_type="text",
            required=True
        )
        question2 = QuestionnaireQuestionORM(
            questionnaire_id=questionnaire.questionnaire_id,
            question_text="Question 2",
            question_type="text",
            required=False
        )
        
        db_session.add_all([question1, question2])
        db_session.commit()
        db_session.refresh(questionnaire)
        
        assert questionnaire.total_questions == 2
        assert questionnaire.required_questions_count == 1


class TestQuestionnaireQuestionORM:
    """Test QuestionnaireQuestionORM model"""
    
    def test_create_text_question(self, db_session):
        """Test creating a text question"""
        questionnaire = QuestionnaireORM(title="Test")
        db_session.add(questionnaire)
        db_session.commit()
        
        question = QuestionnaireQuestionORM(
            questionnaire_id=questionnaire.questionnaire_id,
            question_text="What is your experience?",
            question_type="text",
            required=True,
            max_length=500
        )
        
        db_session.add(question)
        db_session.commit()
        
        assert question.question_id is not None
        assert question.question_text == "What is your experience?"
        assert question.question_type == "text"
        assert question.max_length == 500
    
    def test_create_multiple_choice_question(self, db_session):
        """Test creating a multiple choice question"""
        questionnaire = QuestionnaireORM(title="Test")
        db_session.add(questionnaire)
        db_session.commit()
        
        options = ["Option 1", "Option 2", "Option 3"]
        question = QuestionnaireQuestionORM(
            questionnaire_id=questionnaire.questionnaire_id,
            question_text="Choose one:",
            question_type="multiple_choice",
            options=options
        )
        
        db_session.add(question)
        db_session.commit()
        
        assert question.options == options
        assert question.question_type == "multiple_choice"
    
    def test_question_to_dict(self, db_session):
        """Test question to_dict method"""
        questionnaire = QuestionnaireORM(title="Test")
        db_session.add(questionnaire)
        db_session.commit()
        
        question = QuestionnaireQuestionORM(
            questionnaire_id=questionnaire.questionnaire_id,
            question_text="Test question",
            question_type="text"
        )
        
        db_session.add(question)
        db_session.commit()
        
        data = question.to_dict()
        
        assert 'question_id' in data
        assert data['question_text'] == "Test question"
        assert data['question_type'] == "text"
        assert data['questionnaire_id'] == questionnaire.questionnaire_id


class TestCoverLetterSessionORM:
    """Test CoverLetterSessionORM model"""
    
    def test_create_cover_letter_session(self, db_session):
        """Test creating a cover letter session"""
        session_obj = CoverLetterSessionORM(
            user_id="user-123",
            job_id="job-456",
            draft_text="I am interested...",
            selected_tone="professional"
        )
        
        db_session.add(session_obj)
        db_session.commit()
        
        assert session_obj.session_id is not None
        assert session_obj.user_id == "user-123"
        assert session_obj.job_id == "job-456"
        assert session_obj.selected_tone == "professional"
        assert session_obj.is_active is True
    
    def test_session_expiry_default(self, db_session):
        """Test session expiry default value"""
        session_obj = CoverLetterSessionORM(
            user_id="user-123",
            job_id="job-456"
        )
        
        db_session.add(session_obj)
        db_session.commit()
        
        # Should expire in approximately 24 hours
        expected_expiry = datetime.utcnow() + timedelta(hours=24)
        time_diff = abs((session_obj.expires_at - expected_expiry).total_seconds())
        assert time_diff < 60  # Within 1 minute
    
    def test_session_properties(self, db_session):
        """Test session computed properties"""
        # Create expired session
        past_time = datetime.utcnow() - timedelta(hours=1)
        expired_session = CoverLetterSessionORM(
            user_id="user-123",
            job_id="job-456",
            expires_at=past_time
        )
        
        # Create active session
        future_time = datetime.utcnow() + timedelta(hours=1)
        active_session = CoverLetterSessionORM(
            user_id="user-456",
            job_id="job-789",
            expires_at=future_time,
            generated_letter="Generated letter content"
        )
        
        db_session.add_all([expired_session, active_session])
        db_session.commit()
        
        assert expired_session.is_expired is True
        assert expired_session.time_remaining_hours == 0.0
        
        assert active_session.is_expired is False
        assert active_session.time_remaining_hours > 0
        assert active_session.has_generated_letter is True


class TestQuestionnaireSubmissionORM:
    """Test QuestionnaireSubmissionORM model"""
    
    def test_create_submission(self, db_session):
        """Test creating a questionnaire submission"""
        questionnaire = QuestionnaireORM(title="Test")
        db_session.add(questionnaire)
        db_session.commit()
        
        submission = QuestionnaireSubmissionORM(
            application_id="app-123",
            questionnaire_id=questionnaire.questionnaire_id,
            user_id="user-456",
            time_spent_seconds=1800  # 30 minutes
        )
        
        db_session.add(submission)
        db_session.commit()
        
        assert submission.submission_id is not None
        assert submission.application_id == "app-123"
        assert submission.time_spent_seconds == 1800
        assert submission.completion_time_minutes == 30.0
    
    def test_submission_properties(self, db_session):
        """Test submission computed properties"""
        questionnaire = QuestionnaireORM(title="Test")
        db_session.add(questionnaire)
        db_session.commit()
        
        submission = QuestionnaireSubmissionORM(
            application_id="app-123",
            questionnaire_id=questionnaire.questionnaire_id,
            user_id="user-456"
        )
        
        db_session.add(submission)
        db_session.commit()
        
        assert submission.answer_count == 0
        assert submission.completion_time_minutes == 0.0


class TestQuestionnaireAnswerORM:
    """Test QuestionnaireAnswerORM model"""
    
    def test_create_answer(self, db_session):
        """Test creating a questionnaire answer"""
        questionnaire = QuestionnaireORM(title="Test")
        question = QuestionnaireQuestionORM(
            questionnaire=questionnaire,
            question_text="Test question",
            question_type="text"
        )
        submission = QuestionnaireSubmissionORM(
            application_id="app-123",
            questionnaire=questionnaire,
            user_id="user-456"
        )
        
        db_session.add_all([questionnaire, question, submission])
        db_session.commit()
        
        answer = QuestionnaireAnswerORM(
            submission_id=submission.submission_id,
            question_id=question.question_id,
            answer_data=["My answer text"]
        )
        
        db_session.add(answer)
        db_session.commit()
        
        assert answer.answer_id is not None
        assert answer.answer_data == ["My answer text"]
        assert answer.answer_text == "My answer text"
    
    def test_answer_text_property(self, db_session):
        """Test answer text property with different data types"""
        questionnaire = QuestionnaireORM(title="Test")
        question = QuestionnaireQuestionORM(
            questionnaire=questionnaire,
            question_text="Test question",
            question_type="multiple_choice"
        )
        submission = QuestionnaireSubmissionORM(
            application_id="app-123",
            questionnaire=questionnaire,
            user_id="user-456"
        )
        
        db_session.add_all([questionnaire, question, submission])
        db_session.commit()
        
        # Test multiple choice answer
        answer = QuestionnaireAnswerORM(
            submission_id=submission.submission_id,
            question_id=question.question_id,
            answer_data=["Option 1", "Option 2"]
        )
        
        db_session.add(answer)
        db_session.commit()
        
        assert answer.answer_text == "Option 1, Option 2"