"""
Unit tests for enhanced JobApplication model with workflow features
"""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError

from src.database.models.jobs_model import (
    JobApplication,
    JobApplicationStatusEnum
)
from src.database.models.application_workflow import WorkflowStepEnum


class TestJobApplicationWorkflow:
    """Test JobApplication workflow enhancements"""
    
    def test_default_workflow_fields(self):
        """Test default values for workflow fields"""
        application = JobApplication(
            user_id="user-123",
            job_id="job-456"
        )
        
        assert application.workflow_step == "draft"
        assert application.cover_letter_session_id is None
        assert application.questionnaire_start_time is None
        assert application.questionnaire_completion_time is None
        assert application.time_spent_on_questionnaires is None
        assert application.workflow_started_at is not None
        assert application.workflow_completed_at is None
    
    def test_workflow_completion_percentage(self):
        """Test workflow completion percentage calculation"""
        application = JobApplication(
            user_id="user-123",
            job_id="job-456",
            workflow_step="questionnaires"
        )
        
        assert application.workflow_completion_percentage == 70
        
        application.workflow_step = "submitted"
        assert application.workflow_completion_percentage == 100
        
        application.workflow_step = "invalid_step"
        assert application.workflow_completion_percentage == 0
    
    def test_is_workflow_complete(self):
        """Test workflow completion detection"""
        application = JobApplication(
            user_id="user-123",
            job_id="job-456",
            workflow_step="draft"
        )
        
        assert application.is_workflow_complete is False
        
        application.workflow_step = "submitted"
        assert application.is_workflow_complete is True
    
    def test_next_workflow_step(self):
        """Test next workflow step calculation"""
        application = JobApplication(
            user_id="user-123",
            job_id="job-456",
            workflow_step="draft"
        )
        
        assert application.next_workflow_step == "cover_letter"
        
        application.workflow_step = "cover_letter"
        assert application.next_workflow_step == "questionnaires"
        
        application.workflow_step = "submitted"
        assert application.next_workflow_step is None
        
        # Test invalid step
        application.workflow_step = "invalid"
        assert application.next_workflow_step == "cover_letter"
    
    def test_workflow_duration_minutes(self):
        """Test workflow duration calculation"""
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(minutes=30)
        
        application = JobApplication(
            user_id="user-123",
            job_id="job-456",
            workflow_started_at=start_time,
            workflow_completed_at=end_time
        )
        
        assert application.workflow_duration_minutes == 30.0
        
        # Test incomplete workflow
        application.workflow_completed_at = None
        assert application.workflow_duration_minutes is None
    
    def test_questionnaire_duration_minutes(self):
        """Test questionnaire duration calculation"""
        application = JobApplication(
            user_id="user-123",
            job_id="job-456",
            time_spent_on_questionnaires=1800  # 30 minutes in seconds
        )
        
        assert application.questionnaire_duration_minutes == 30.0
        
        application.time_spent_on_questionnaires = None
        assert application.questionnaire_duration_minutes is None
    
    def test_has_cover_letter_session(self):
        """Test cover letter session detection"""
        application = JobApplication(
            user_id="user-123",
            job_id="job-456"
        )
        
        assert application.has_cover_letter_session is False
        
        application.cover_letter_session_id = "session-123"
        assert application.has_cover_letter_session is True
    
    def test_questionnaires_completed(self):
        """Test questionnaire completion detection"""
        application = JobApplication(
            user_id="user-123",
            job_id="job-456"
        )
        
        assert application.questionnaires_completed is False
        
        application.questionnaire_completion_time = datetime.utcnow()
        assert application.questionnaires_completed is True
    
    def test_workflow_step_display(self):
        """Test human-readable workflow step names"""
        application = JobApplication(
            user_id="user-123",
            job_id="job-456",
            workflow_step="draft"
        )
        
        assert application.workflow_step_display == "Draft Created"
        
        application.workflow_step = "cover_letter"
        assert application.workflow_step_display == "Cover Letter Generated"
        
        application.workflow_step = "questionnaires"
        assert application.workflow_step_display == "Questionnaires Completed"
        
        application.workflow_step = "review"
        assert application.workflow_step_display == "Ready for Review"
        
        application.workflow_step = "submitted"
        assert application.workflow_step_display == "Application Submitted"
        
        application.workflow_step = "unknown"
        assert application.workflow_step_display == "Unknown Step"
    
    def test_update_workflow_step(self):
        """Test workflow step update method"""
        application = JobApplication(
            user_id="user-123",
            job_id="job-456",
            workflow_step="draft",
            application_stage="DRAFT"
        )
        
        original_updated_at = application.updated_at
        
        # Update to intermediate step
        application.update_workflow_step("cover_letter")
        assert application.workflow_step == "cover_letter"
        assert application.updated_at != original_updated_at
        assert application.workflow_completed_at is None
        assert application.application_stage == "DRAFT"
        
        # Update to final step
        application.update_workflow_step("submitted")
        assert application.workflow_step == "submitted"
        assert application.workflow_completed_at is not None
        assert application.application_stage == JobApplicationStatusEnum.APPLIED.value
        assert application.applied_date is not None
    
    def test_start_questionnaire_timer(self):
        """Test questionnaire timer start"""
        application = JobApplication(
            user_id="user-123",
            job_id="job-456"
        )
        
        assert application.questionnaire_start_time is None
        
        application.start_questionnaire_timer()
        assert application.questionnaire_start_time is not None
    
    def test_complete_questionnaires(self):
        """Test questionnaire completion"""
        application = JobApplication(
            user_id="user-123",
            job_id="job-456",
            workflow_step="questionnaires"
        )
        
        time_spent = 1800  # 30 minutes
        application.complete_questionnaires(time_spent)
        
        assert application.questionnaire_completion_time is not None
        assert application.time_spent_on_questionnaires == time_spent
        assert application.workflow_step == "review"
    
    def test_backward_compatibility(self):
        """Test that existing properties still work"""
        application = JobApplication(
            user_id="user-123",
            job_id="job-456",
            application_stage=JobApplicationStatusEnum.APPLIED.value
        )
        
        # Test existing properties still work
        assert application.is_recent_application is not None
        assert application.is_active is True
        assert application.needs_action is not None
        assert application.workflow_completion_percentage >= 0
    
    def test_workflow_with_existing_fields(self):
        """Test workflow integration with existing fields"""
        application = JobApplication(
            user_id="user-123",
            job_id="job-456",
            cover_letter="My cover letter",
            questionnaire_answers={"q1": ["answer1"]},
            workflow_step="review"
        )
        
        assert application.cover_letter == "My cover letter"
        assert application.questionnaire_answers == {"q1": ["answer1"]}
        assert application.workflow_step == "review"
        assert application.workflow_completion_percentage == 90
    
    def test_model_serialization(self):
        """Test that model can be serialized with new fields"""
        application = JobApplication(
            user_id="user-123",
            job_id="job-456",
            workflow_step="cover_letter",
            cover_letter_session_id="session-123",
            time_spent_on_questionnaires=900
        )
        
        # Test model_dump includes new fields
        data = application.model_dump()
        
        assert "workflow_step" in data
        assert "cover_letter_session_id" in data
        assert "time_spent_on_questionnaires" in data
        assert "workflow_started_at" in data
        assert "workflow_completed_at" in data
        
        assert data["workflow_step"] == "cover_letter"
        assert data["cover_letter_session_id"] == "session-123"
        assert data["time_spent_on_questionnaires"] == 900


class TestJobApplicationWorkflowIntegration:
    """Test integration between workflow and existing features"""
    
    def test_ats_report_with_workflow(self):
        """Test ATS report integration with workflow"""
        from src.database.models.jobs_model import ATSReport
        
        ats_report = ATSReport(
            job_id="job-456",
            cv_id="cv-789",
            score=85.0,
            matched_keywords=["python", "django"],
            missing_keywords=["react"],
            feedback="Good match"
        )
        
        application = JobApplication(
            user_id="user-123",
            job_id="job-456",
            workflow_step="review",
            ats_report=ats_report
        )
        
        assert application.has_ats_report is True
        assert application.ats_score == 85.0
        assert application.is_ats_ready is True
        assert application.workflow_step == "review"
    
    def test_workflow_with_validation_score(self):
        """Test workflow integration with validation scoring"""
        application = JobApplication(
            user_id="user-123",
            job_id="job-456",
            workflow_step="submitted",
            validation_score=95,
            missing_requirements=[]
        )
        
        assert application.validation_score == 95
        assert application.missing_requirements == []
        assert application.is_workflow_complete is True
        assert not application.needs_action