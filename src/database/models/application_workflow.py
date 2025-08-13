"""
Application Workflow Pydantic Models

This module contains Pydantic models for managing the job application workflow process,
including cover letter generation, questionnaire handling, and application submission.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, validator
from enum import Enum


class WorkflowStepEnum(str, Enum):
    """Enumeration of workflow steps"""
    DRAFT = "draft"
    COVER_LETTER = "cover_letter"
    QUESTIONNAIRES = "questionnaires"
    REVIEW = "review"
    SUBMITTED = "submitted"


class QuestionTypeEnum(str, Enum):
    """Enumeration of question types"""
    MULTIPLE_CHOICE = "multiple_choice"
    TEXT = "text"
    BOOLEAN = "boolean"
    RATING = "rating"


class ApplicationWorkflowResult(BaseModel):
    """Result of starting application workflow"""
    success: bool
    message: Optional[str] = None
    application_id: Optional[str] = None
    next_step: Optional[str] = None  # 'cover_letter', 'questionnaires', 'review'
    cover_letter_exists: bool = False
    questionnaires_required: bool = False
    workflow_step: Optional[str] = None
    
    class Config:
        use_enum_values = True


class QuestionnaireQuestion(BaseModel):
    """Individual questionnaire question"""
    question_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question_text: str = Field(..., min_length=5, max_length=1000)
    question_type: QuestionTypeEnum = Field(default=QuestionTypeEnum.TEXT)
    required: bool = True
    options: Optional[List[str]] = None  # For multiple choice
    max_length: Optional[int] = Field(None, ge=1, le=5000)  # For text questions
    min_rating: Optional[int] = Field(None, ge=1, le=10)  # For rating questions
    max_rating: Optional[int] = Field(None, ge=1, le=10)  # For rating questions
    order_index: int = Field(default=0, ge=0)
    
    @validator('options')
    def validate_options(cls, v, values):
        """Validate options for multiple choice questions"""
        if values.get('question_type') == QuestionTypeEnum.MULTIPLE_CHOICE:
            if not v or len(v) < 2:
                raise ValueError('Multiple choice questions must have at least 2 options')
        return v
    
    @validator('max_rating')
    def validate_rating_range(cls, v, values):
        """Validate rating range"""
        if values.get('question_type') == QuestionTypeEnum.RATING:
            min_rating = values.get('min_rating', 1)
            if v and min_rating and v <= min_rating:
                raise ValueError('max_rating must be greater than min_rating')
        return v
    
    class Config:
        use_enum_values = True


class Questionnaire(BaseModel):
    """Questionnaire definition"""
    questionnaire_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = Field(..., min_length=5, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    time_limit: int = Field(default=30, ge=5, le=120)  # 5-120 minutes
    questions: List[QuestionnaireQuestion] = Field(default_factory=list)
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('questions')
    def validate_questions(cls, v):
        """Validate questionnaire has at least one question"""
        if not v:
            raise ValueError('Questionnaire must have at least one question')
        return v
    
    @property
    def total_questions(self) -> int:
        """Get total number of questions"""
        return len(self.questions)
    
    @property
    def required_questions_count(self) -> int:
        """Get count of required questions"""
        return sum(1 for q in self.questions if q.required)
    
    class Config:
        use_enum_values = True


class QuestionnaireResult(BaseModel):
    """Result of questionnaire retrieval"""
    success: bool
    questionnaires: List[Questionnaire] = Field(default_factory=list)
    time_limit: int = Field(default=30, ge=5, le=120)  # Total time limit in minutes
    message: Optional[str] = None
    total_questions: int = Field(default=0, ge=0)
    
    @property
    def has_questionnaires(self) -> bool:
        """Check if there are questionnaires to complete"""
        return len(self.questionnaires) > 0
    
    class Config:
        use_enum_values = True


class ValidationResult(BaseModel):
    """Result of validation checks"""
    is_valid: bool = True
    is_complete: bool = True
    score: int = Field(default=0, ge=0, le=100)
    missing_fields: List[str] = Field(default_factory=list)
    missing_requirements: List[str] = Field(default_factory=list)
    validation_errors: List[str] = Field(default_factory=list)
    
    @property
    def has_errors(self) -> bool:
        """Check if validation has any errors"""
        return not self.is_valid or not self.is_complete or bool(self.validation_errors)
    
    @property
    def error_count(self) -> int:
        """Get total number of validation errors"""
        return len(self.missing_fields) + len(self.missing_requirements) + len(self.validation_errors)


class SubmissionResult(BaseModel):
    """Result of application submission"""
    success: bool
    message: str
    application_id: Optional[str] = None
    missing_fields: Optional[List[str]] = None
    missing_requirements: Optional[List[str]] = None
    validation_score: Optional[int] = Field(None, ge=0, le=100)
    next_step: Optional[str] = None
    
    @property
    def has_missing_items(self) -> bool:
        """Check if there are missing fields or requirements"""
        return bool(self.missing_fields) or bool(self.missing_requirements)


class CoverLetterSession(BaseModel):
    """Cover letter generation session"""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(..., min_length=1)
    job_id: str = Field(..., min_length=1)
    cv_id: Optional[str] = None
    draft_text: Optional[str] = Field(None, max_length=5000)
    selected_tone: str = Field(default="professional")
    generated_letter: Optional[str] = Field(None, max_length=10000)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(default_factory=lambda: datetime.utcnow() + timedelta(hours=24))
    is_active: bool = True
    
    @validator('selected_tone')
    def validate_tone(cls, v):
        """Validate cover letter tone"""
        valid_tones = ['professional', 'enthusiastic', 'friendly', 'formal', 'concise']
        if v.lower() not in valid_tones:
            raise ValueError(f'Invalid tone. Must be one of: {", ".join(valid_tones)}')
        return v.lower()
    
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


class QuestionnaireAnswer(BaseModel):
    """Individual questionnaire answer"""
    question_id: str = Field(..., min_length=1)
    answer: List[str] = Field(default_factory=list)  # List to support multiple choice
    answered_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('answer')
    def validate_answer(cls, v):
        """Validate answer is not empty for required questions"""
        if not v or (len(v) == 1 and not v[0].strip()):
            raise ValueError('Answer cannot be empty')
        return v


class QuestionnaireSubmission(BaseModel):
    """Complete questionnaire submission"""
    application_id: str = Field(..., min_length=1)
    questionnaire_id: str = Field(..., min_length=1)
    answers: List[QuestionnaireAnswer] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    submitted_at: Optional[datetime] = None
    time_spent_seconds: Optional[int] = Field(None, ge=0)
    is_complete: bool = False
    
    @property
    def completion_time_minutes(self) -> Optional[float]:
        """Get completion time in minutes"""
        if self.time_spent_seconds is not None:
            return self.time_spent_seconds / 60
        return None
    
    @property
    def answer_count(self) -> int:
        """Get number of answered questions"""
        return len(self.answers)


class ApplicationProgress(BaseModel):
    """Application progress tracking"""
    application_id: str = Field(..., min_length=1)
    current_step: WorkflowStepEnum = Field(default=WorkflowStepEnum.DRAFT)
    completed_steps: List[str] = Field(default_factory=list)
    cover_letter_completed: bool = False
    questionnaires_completed: bool = False
    validation_passed: bool = False
    completion_percentage: int = Field(default=0, ge=0, le=100)
    
    @property
    def next_step(self) -> Optional[WorkflowStepEnum]:
        """Get next step in workflow"""
        steps = [
            WorkflowStepEnum.DRAFT,
            WorkflowStepEnum.COVER_LETTER,
            WorkflowStepEnum.QUESTIONNAIRES,
            WorkflowStepEnum.REVIEW,
            WorkflowStepEnum.SUBMITTED
        ]
        
        try:
            current_index = steps.index(self.current_step)
            return steps[current_index + 1] if current_index < len(steps) - 1 else None
        except ValueError:
            return WorkflowStepEnum.COVER_LETTER
    
    @property
    def is_complete(self) -> bool:
        """Check if workflow is complete"""
        return self.current_step == WorkflowStepEnum.SUBMITTED
    
    def update_completion_percentage(self):
        """Update completion percentage based on current step"""
        step_percentages = {
            WorkflowStepEnum.DRAFT: 10,
            WorkflowStepEnum.COVER_LETTER: 40,
            WorkflowStepEnum.QUESTIONNAIRES: 70,
            WorkflowStepEnum.REVIEW: 90,
            WorkflowStepEnum.SUBMITTED: 100
        }
        self.completion_percentage = step_percentages.get(self.current_step, 0)
    
    class Config:
        use_enum_values = True