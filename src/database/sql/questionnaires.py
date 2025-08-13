"""
SQLAlchemy ORM models for questionnaire system

This module contains the database models for managing questionnaires,
questions, and cover letter sessions in the job application workflow.
"""

import uuid
from datetime import datetime, timedelta
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

# Import the base from the main database module
try:
    from src.database.sql import Base
except ImportError:
    # Fallback for testing
    Base = declarative_base()


class QuestionnaireORM(Base):
    """Questionnaire definition table"""
    __tablename__ = 'questionnaires'
    
    questionnaire_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    time_limit = Column(Integer, default=30, nullable=False)  # minutes
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    questions = relationship("QuestionnaireQuestionORM", back_populates="questionnaire", cascade="all, delete-orphan")
    submissions = relationship("QuestionnaireSubmissionORM", back_populates="questionnaire")
    
    def to_dict(self) -> dict:
        """Convert ORM instance to dictionary"""
        return {
            'questionnaire_id': self.questionnaire_id,
            'title': self.title,
            'description': self.description,
            'time_limit': self.time_limit,
            'is_active': self.is_active,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @property
    def total_questions(self) -> int:
        """Get total number of questions"""
        return len(self.questions) if self.questions else 0
    
    @property
    def required_questions_count(self) -> int:
        """Get count of required questions"""
        if not self.questions:
            return 0
        return sum(1 for q in self.questions if q.required)


class QuestionnaireQuestionORM(Base):
    """Individual questionnaire questions"""
    __tablename__ = 'questionnaire_questions'
    
    question_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    questionnaire_id = Column(String(36), ForeignKey('questionnaires.questionnaire_id'), nullable=False)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(20), nullable=False)  # multiple_choice, text, boolean, rating
    required = Column(Boolean, default=True, nullable=False)
    options = Column(JSON, nullable=True)  # JSON array for multiple choice options
    max_length = Column(Integer, nullable=True)  # For text questions
    min_rating = Column(Integer, nullable=True)  # For rating questions
    max_rating = Column(Integer, nullable=True)  # For rating questions
    order_index = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    questionnaire = relationship("QuestionnaireORM", back_populates="questions")
    answers = relationship("QuestionnaireAnswerORM", back_populates="question")
    
    def to_dict(self) -> dict:
        """Convert ORM instance to dictionary"""
        return {
            'question_id': self.question_id,
            'questionnaire_id': self.questionnaire_id,
            'question_text': self.question_text,
            'question_type': self.question_type,
            'required': self.required,
            'options': self.options,
            'max_length': self.max_length,
            'min_rating': self.min_rating,
            'max_rating': self.max_rating,
            'order_index': self.order_index,
            'created_at': self.created_at
        }


class CoverLetterSessionORM(Base):
    """Cover letter generation sessions"""
    __tablename__ = 'cover_letter_sessions'
    
    session_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    job_id = Column(String(36), nullable=False, index=True)
    cv_id = Column(String(36), nullable=True)
    draft_text = Column(Text, nullable=True)
    selected_tone = Column(String(20), default='professional', nullable=False)
    generated_letter = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.expires_at:
            self.expires_at = datetime.utcnow() + timedelta(hours=24)
    
    def to_dict(self) -> dict:
        """Convert ORM instance to dictionary"""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'job_id': self.job_id,
            'cv_id': self.cv_id,
            'draft_text': self.draft_text,
            'selected_tone': self.selected_tone,
            'generated_letter': self.generated_letter,
            'created_at': self.created_at,
            'expires_at': self.expires_at,
            'is_active': self.is_active
        }
    
    @property
    def is_expired(self) -> bool:
        """Check if session is expired"""
        return datetime.utcnow() > self.expires_at
    
    @property
    def has_generated_letter(self) -> bool:
        """Check if cover letter has been generated"""
        return bool(self.generated_letter)
    
    @property
    def time_remaining_hours(self) -> float:
        """Get remaining time in hours"""
        if self.is_expired:
            return 0.0
        delta = self.expires_at - datetime.utcnow()
        return delta.total_seconds() / 3600


class QuestionnaireSubmissionORM(Base):
    """Complete questionnaire submissions"""
    __tablename__ = 'questionnaire_submissions'
    
    submission_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String(36), nullable=False, index=True)
    questionnaire_id = Column(String(36), ForeignKey('questionnaires.questionnaire_id'), nullable=False)
    user_id = Column(String(36), nullable=False, index=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    time_spent_seconds = Column(Integer, nullable=True)
    is_complete = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    questionnaire = relationship("QuestionnaireORM", back_populates="submissions")
    answers = relationship("QuestionnaireAnswerORM", back_populates="submission", cascade="all, delete-orphan")
    
    def to_dict(self) -> dict:
        """Convert ORM instance to dictionary"""
        return {
            'submission_id': self.submission_id,
            'application_id': self.application_id,
            'questionnaire_id': self.questionnaire_id,
            'user_id': self.user_id,
            'started_at': self.started_at,
            'submitted_at': self.submitted_at,
            'time_spent_seconds': self.time_spent_seconds,
            'is_complete': self.is_complete,
            'created_at': self.created_at
        }
    
    @property
    def completion_time_minutes(self) -> float:
        """Get completion time in minutes"""
        if self.time_spent_seconds is not None:
            return self.time_spent_seconds / 60
        return 0.0
    
    @property
    def answer_count(self) -> int:
        """Get number of answered questions"""
        return len(self.answers) if self.answers else 0


class QuestionnaireAnswerORM(Base):
    """Individual questionnaire answers"""
    __tablename__ = 'questionnaire_answers'
    
    answer_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    submission_id = Column(String(36), ForeignKey('questionnaire_submissions.submission_id'), nullable=False)
    question_id = Column(String(36), ForeignKey('questionnaire_questions.question_id'), nullable=False)
    answer_data = Column(JSON, nullable=False)  # Store answer as JSON array
    answered_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    submission = relationship("QuestionnaireSubmissionORM", back_populates="answers")
    question = relationship("QuestionnaireQuestionORM", back_populates="answers")
    
    def to_dict(self) -> dict:
        """Convert ORM instance to dictionary"""
        return {
            'answer_id': self.answer_id,
            'submission_id': self.submission_id,
            'question_id': self.question_id,
            'answer_data': self.answer_data,
            'answered_at': self.answered_at
        }
    
    @property
    def answer_text(self) -> str:
        """Get answer as text string"""
        if isinstance(self.answer_data, list):
            return ', '.join(str(item) for item in self.answer_data)
        return str(self.answer_data) if self.answer_data else ''


# Index definitions for performance optimization
from sqlalchemy import Index

# Indexes for questionnaires
Index('idx_questionnaires_active', QuestionnaireORM.is_active)
Index('idx_questionnaires_created', QuestionnaireORM.created_at)

# Indexes for questions
Index('idx_questions_questionnaire', QuestionnaireQuestionORM.questionnaire_id)
Index('idx_questions_order', QuestionnaireQuestionORM.questionnaire_id, QuestionnaireQuestionORM.order_index)

# Indexes for cover letter sessions
Index('idx_cover_sessions_user_job', CoverLetterSessionORM.user_id, CoverLetterSessionORM.job_id)
Index('idx_cover_sessions_active', CoverLetterSessionORM.is_active)
Index('idx_cover_sessions_expires', CoverLetterSessionORM.expires_at)

# Indexes for submissions
Index('idx_submissions_application', QuestionnaireSubmissionORM.application_id)
Index('idx_submissions_user', QuestionnaireSubmissionORM.user_id)
Index('idx_submissions_questionnaire', QuestionnaireSubmissionORM.questionnaire_id)
Index('idx_submissions_complete', QuestionnaireSubmissionORM.is_complete)

# Indexes for answers
Index('idx_answers_submission', QuestionnaireAnswerORM.submission_id)
Index('idx_answers_question', QuestionnaireAnswerORM.question_id)