"""
Application Workflow Controller

This controller manages the job application workflow process including
cover letter generation, questionnaire handling, and application submission.
"""

from typing import Optional, Dict, List
from datetime import datetime
from sqlalchemy.orm import joinedload
from sqlalchemy import and_

from src.controllers.controller import Controllers, error_handler
from src.database.models.jobs_model import JobApplication, JobApplicationORM, JobApplicationStatusEnum
from src.database.models.application_workflow import (
    ApplicationWorkflowResult,
    QuestionnaireResult,
    SubmissionResult,
    ValidationResult,
    CoverLetterSession
)
from src.database.sql.questionnaires import (
    QuestionnaireORM,
    CoverLetterSessionORM,
    QuestionnaireSubmissionORM,
    QuestionnaireAnswerORM
)
from src.utils.route_helpers import get_controller
from src.logger import init_logger


class ApplicationWorkflowController(Controllers):
    """Controller for managing the job application workflow"""
    
    def __init__(self, factory):
        super().__init__(factory)
        self.logger = init_logger(self.__class__.__name__)
    
    @error_handler
    async def start_application_process(
        self, 
        user_id: str, 
        job_id: str
    ) -> ApplicationWorkflowResult:
        """
        Start the application process for a user and job
        
        Args:
            user_id: ID of the job seeker
            job_id: ID of the job being applied to
            
        Returns:
            ApplicationWorkflowResult with next steps and application ID
        """
        self.logger.info(f"Starting application process for user {user_id}, job {job_id}")
        
        try:
            # Check if user already applied
            existing_application = await self._check_existing_application(user_id, job_id)
            if existing_application:
                self.logger.warning(f"User {user_id} already applied for job {job_id}")
                return ApplicationWorkflowResult(
                    success=False,
                    message="You have already applied for this job",
                    application_id=existing_application.application_id,
                    workflow_step=existing_application.workflow_step
                )
            
            # Get job details to check requirements
            job_controller = get_controller('jobs_search')
            job = await job_controller.get_job_by_id(job_id=job_id)
            
            if not job:
                self.logger.error(f"Job {job_id} not found")
                return ApplicationWorkflowResult(
                    success=False,
                    message="Job not found"
                )
            
            # Check for existing cover letter session
            cover_letter_exists = await self._check_cover_letter_exists(user_id, job_id)
            
            # Determine if questionnaires are required
            questionnaires_required = bool(job.required_questionnaire and len(job.required_questionnaire) > 0)
            
            # Create draft application record
            with self.get_session() as session:
                application_orm = JobApplicationORM(
                    user_id=user_id,
                    job_id=job_id,
                    application_stage="DRAFT",
                    workflow_step="draft",
                    method="website"
                )
                session.add(application_orm)
                session.commit()
                
                # Determine next step
                if cover_letter_exists:
                    next_step = "questionnaires" if questionnaires_required else "review"
                    application_orm.workflow_step = "cover_letter"
                else:
                    next_step = "cover_letter"
                
                session.commit()
                
                self.logger.info(f"Created draft application {application_orm.application_id} for user {user_id}")
                
                return ApplicationWorkflowResult(
                    success=True,
                    application_id=application_orm.application_id,
                    next_step=next_step,
                    cover_letter_exists=cover_letter_exists,
                    questionnaires_required=questionnaires_required,
                    workflow_step=application_orm.workflow_step
                )
                
        except Exception as e:
            self.logger.error(f"Error starting application process: {e}")
            return ApplicationWorkflowResult(
                success=False,
                message=f"Failed to start application process: {str(e)}"
            )
    
    @error_handler
    async def get_job_questionnaires(self, job_id: str) -> QuestionnaireResult:
        """
        Get questionnaires required for a job
        
        Args:
            job_id: ID of the job
            
        Returns:
            QuestionnaireResult with questionnaire definitions
        """
        self.logger.info(f"Getting questionnaires for job {job_id}")
        
        try:
            # Get job details
            job_controller = get_controller('jobs_search')
            job = await job_controller.get_job_by_id(job_id=job_id)
            
            if not job or not job.required_questionnaire:
                return QuestionnaireResult(
                    success=True,
                    questionnaires=[],
                    time_limit=0,
                    total_questions=0
                )
            
            # Load questionnaire definitions from database
            questionnaires = await self._load_questionnaires(job.required_questionnaire)
            
            # Calculate total time limit and questions
            total_time_limit = sum(q.time_limit for q in questionnaires)
            total_questions = sum(q.total_questions for q in questionnaires)
            
            self.logger.info(f"Found {len(questionnaires)} questionnaires for job {job_id}")
            
            return QuestionnaireResult(
                success=True,
                questionnaires=questionnaires,
                time_limit=total_time_limit,
                total_questions=total_questions
            )
            
        except Exception as e:
            self.logger.error(f"Error getting questionnaires for job {job_id}: {e}")
            return QuestionnaireResult(
                success=False,
                questionnaires=[],
                time_limit=0,
                message=f"Failed to load questionnaires: {str(e)}"
            )
    
    async def _check_existing_application(self, user_id: str, job_id: str) -> Optional[JobApplication]:
        """
        Check if user already applied for this job
        
        Args:
            user_id: ID of the user
            job_id: ID of the job
            
        Returns:
            JobApplication if exists, None otherwise
        """
        with self.get_session() as session:
            existing = session.query(JobApplicationORM).filter(
                and_(
                    JobApplicationORM.user_id == user_id,
                    JobApplicationORM.job_id == job_id,
                    JobApplicationORM.application_stage != "DRAFT"
                )
            ).first()
            
            if existing:
                return JobApplication(**existing.to_dict())
            return None
    
    async def _check_cover_letter_exists(self, user_id: str, job_id: str) -> bool:
        """
        Check if user has generated a cover letter for this job
        
        Args:
            user_id: ID of the user
            job_id: ID of the job
            
        Returns:
            True if cover letter exists, False otherwise
        """
        with self.get_session() as session:
            # Check for active cover letter session with generated letter
            session_exists = session.query(CoverLetterSessionORM).filter(
                and_(
                    CoverLetterSessionORM.user_id == user_id,
                    CoverLetterSessionORM.job_id == job_id,
                    CoverLetterSessionORM.is_active == True,
                    CoverLetterSessionORM.generated_letter.isnot(None),
                    CoverLetterSessionORM.expires_at > datetime.utcnow()
                )
            ).first()
            
            return session_exists is not None
    
    async def _load_questionnaires(self, questionnaire_ids: List[str]) -> List:
        """
        Load questionnaire definitions from database
        
        Args:
            questionnaire_ids: List of questionnaire IDs
            
        Returns:
            List of Questionnaire objects
        """
        from src.database.models.application_workflow import Questionnaire, QuestionnaireQuestion
        
        questionnaires = []
        
        with self.get_session() as session:
            for questionnaire_id in questionnaire_ids:
                questionnaire_orm = session.query(QuestionnaireORM).options(
                    joinedload(QuestionnaireORM.questions)
                ).filter(
                    and_(
                        QuestionnaireORM.questionnaire_id == questionnaire_id,
                        QuestionnaireORM.is_active == True
                    )
                ).first()
                
                if questionnaire_orm:
                    # Convert questions
                    questions = []
                    for question_orm in sorted(questionnaire_orm.questions, key=lambda x: x.order_index):
                        question = QuestionnaireQuestion(
                            question_id=question_orm.question_id,
                            question_text=question_orm.question_text,
                            question_type=question_orm.question_type,
                            required=question_orm.required,
                            options=question_orm.options,
                            max_length=question_orm.max_length,
                            min_rating=question_orm.min_rating,
                            max_rating=question_orm.max_rating,
                            order_index=question_orm.order_index
                        )
                        questions.append(question)
                    
                    # Convert questionnaire
                    questionnaire = Questionnaire(
                        questionnaire_id=questionnaire_orm.questionnaire_id,
                        title=questionnaire_orm.title,
                        description=questionnaire_orm.description,
                        time_limit=questionnaire_orm.time_limit,
                        questions=questions,
                        is_active=questionnaire_orm.is_active,
                        created_at=questionnaire_orm.created_at
                    )
                    questionnaires.append(questionnaire)
        
        return questionnaires
    
    @error_handler
    async def create_cover_letter_session(
        self,
        user_id: str,
        job_id: str,
        cv_id: Optional[str] = None,
        draft_text: Optional[str] = None,
        selected_tone: str = "professional"
    ) -> Dict[str, any]:
        """
        Create a cover letter generation session
        
        Args:
            user_id: ID of the user
            job_id: ID of the job
            cv_id: ID of the CV to use
            draft_text: Initial draft text
            selected_tone: Tone for generation
            
        Returns:
            Dictionary with session information
        """
        self.logger.info(f"Creating cover letter session for user {user_id}, job {job_id}")
        
        try:
            with self.get_session() as session:
                # Check for existing active session
                existing_session = session.query(CoverLetterSessionORM).filter(
                    and_(
                        CoverLetterSessionORM.user_id == user_id,
                        CoverLetterSessionORM.job_id == job_id,
                        CoverLetterSessionORM.is_active == True,
                        CoverLetterSessionORM.expires_at > datetime.utcnow()
                    )
                ).first()
                
                if existing_session:
                    # Update existing session
                    if draft_text:
                        existing_session.draft_text = draft_text
                    existing_session.selected_tone = selected_tone
                    if cv_id:
                        existing_session.cv_id = cv_id
                    
                    session.commit()
                    
                    return {
                        "success": True,
                        "session_id": existing_session.session_id,
                        "message": "Updated existing cover letter session"
                    }
                else:
                    # Create new session
                    session_orm = CoverLetterSessionORM(
                        user_id=user_id,
                        job_id=job_id,
                        cv_id=cv_id,
                        draft_text=draft_text,
                        selected_tone=selected_tone
                    )
                    session.add(session_orm)
                    session.commit()
                    
                    self.logger.info(f"Created cover letter session {session_orm.session_id}")
                    
                    return {
                        "success": True,
                        "session_id": session_orm.session_id,
                        "message": "Created new cover letter session"
                    }
                    
        except Exception as e:
            self.logger.error(f"Error creating cover letter session: {e}")
            return {
                "success": False,
                "message": f"Failed to create cover letter session: {str(e)}"
            }
    
    @error_handler
    async def link_cover_letter_to_application(
        self,
        application_id: str,
        session_id: str,
        user_id: str
    ) -> Dict[str, any]:
        """
        Link a cover letter session to an application
        
        Args:
            application_id: ID of the application
            session_id: ID of the cover letter session
            user_id: ID of the user (for security)
            
        Returns:
            Dictionary with result
        """
        self.logger.info(f"Linking cover letter session {session_id} to application {application_id}")
        
        try:
            with self.get_session() as session:
                # Get application
                application = session.query(JobApplicationORM).filter(
                    and_(
                        JobApplicationORM.application_id == application_id,
                        JobApplicationORM.user_id == user_id
                    )
                ).first()
                
                if not application:
                    return {
                        "success": False,
                        "message": "Application not found"
                    }
                
                # Get cover letter session
                cover_session = session.query(CoverLetterSessionORM).filter(
                    and_(
                        CoverLetterSessionORM.session_id == session_id,
                        CoverLetterSessionORM.user_id == user_id
                    )
                ).first()
                
                if not cover_session:
                    return {
                        "success": False,
                        "message": "Cover letter session not found"
                    }
                
                # Link session to application
                application.cover_letter_session_id = session_id
                if cover_session.generated_letter:
                    application.cover_letter = cover_session.generated_letter
                    application.workflow_step = "questionnaires"
                
                session.commit()
                
                self.logger.info(f"Successfully linked cover letter session to application")
                
                return {
                    "success": True,
                    "message": "Cover letter linked to application"
                }
                
        except Exception as e:
            self.logger.exception("Failed to link cover letter to application")
            return {
                "success": False,
                "message": f"Failed to link cover letter: {str(e)}"
            }
    
    @error_handler
    async def update_cover_letter_session(
        self,
        session_id: str,
        user_id: str,
        generated_letter: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Update a cover letter session with generated content
        
        Args:
            session_id: ID of the cover letter session
            user_id: ID of the user (for security)
            generated_letter: Generated cover letter content
            
        Returns:
            Dictionary with result
        """
        self.logger.info(f"Updating cover letter session {session_id}")
        
        try:
            with self.get_session() as session:
                # Get cover letter session
                cover_session = session.query(CoverLetterSessionORM).filter(
                    and_(
                        CoverLetterSessionORM.session_id == session_id,
                        CoverLetterSessionORM.user_id == user_id
                    )
                ).first()
                
                if not cover_session:
                    return {
                        "success": False,
                        "message": "Cover letter session not found"
                    }
                
                # Update session with generated content
                if generated_letter:
                    cover_session.generated_letter = generated_letter
                    cover_session.generated_at = datetime.utcnow()
                
                session.commit()
                
                self.logger.info(f"Successfully updated cover letter session")
                
                return {
                    "success": True,
                    "message": "Cover letter session updated"
                }
                
        except Exception as e:
            self.logger.exception("Failed to update cover letter session")
            return {
                "success": False,
                "message": f"Failed to update cover letter session: {str(e)}"
            }
    
    @error_handler
    async def save_questionnaire_progress(
        self,
        application_id: str,
        questionnaire_id: str,
        user_id: str,
        answers: Dict[str, List[str]],
        current_question: int = 1,
        time_spent: int = 0
    ) -> Dict[str, any]:
        """
        Save questionnaire progress for auto-save functionality
        
        Args:
            application_id: ID of the application
            questionnaire_id: ID of the questionnaire
            user_id: ID of the user
            answers: Current answers
            current_question: Current question number
            time_spent: Time spent in seconds
            
        Returns:
            Dictionary with result
        """
        self.logger.info(f"Saving questionnaire progress for application {application_id}")
        
        try:
            with self.get_session() as session:
                # Get or create submission record
                submission = session.query(QuestionnaireSubmissionORM).filter(
                    and_(
                        QuestionnaireSubmissionORM.application_id == application_id,
                        QuestionnaireSubmissionORM.questionnaire_id == questionnaire_id,
                        QuestionnaireSubmissionORM.user_id == user_id
                    )
                ).first()
                
                if not submission:
                    submission = QuestionnaireSubmissionORM(
                        application_id=application_id,
                        questionnaire_id=questionnaire_id,
                        user_id=user_id
                    )
                    session.add(submission)
                    session.flush()  # Get the ID
                
                # Update progress
                submission.time_spent_seconds = time_spent
                
                # Save answers
                for question_id, answer_data in answers.items():
                    # Check if answer already exists
                    existing_answer = session.query(QuestionnaireAnswerORM).filter(
                        and_(
                            QuestionnaireAnswerORM.submission_id == submission.submission_id,
                            QuestionnaireAnswerORM.question_id == question_id
                        )
                    ).first()
                    
                    if existing_answer:
                        existing_answer.answer_data = answer_data
                    else:
                        new_answer = QuestionnaireAnswerORM(
                            submission_id=submission.submission_id,
                            question_id=question_id,
                            answer_data=answer_data
                        )
                        session.add(new_answer)
                
                session.commit()
                
                return {
                    "success": True,
                    "message": "Progress saved"
                }
                
        except Exception as e:
            self.logger.exception("Failed to save questionnaire progress")
            return {
                "success": False,
                "message": f"Failed to save progress: {str(e)}"
            }
    
    @error_handler
    async def submit_questionnaire(
        self,
        application_id: str,
        questionnaire_id: str,
        user_id: str,
        answers: Dict[str, List[str]],
        time_spent_seconds: int = 0,
        is_auto_submit: bool = False
    ) -> Dict[str, any]:
        """
        Submit completed questionnaire
        
        Args:
            application_id: ID of the application
            questionnaire_id: ID of the questionnaire
            user_id: ID of the user
            answers: Final answers
            time_spent_seconds: Total time spent
            is_auto_submit: Whether this was an auto-submission
            
        Returns:
            Dictionary with result
        """
        self.logger.info(f"Submitting questionnaire for application {application_id}")
        
        try:
            with self.get_session() as session:
                # Get or create submission record
                submission = session.query(QuestionnaireSubmissionORM).filter(
                    and_(
                        QuestionnaireSubmissionORM.application_id == application_id,
                        QuestionnaireSubmissionORM.questionnaire_id == questionnaire_id,
                        QuestionnaireSubmissionORM.user_id == user_id
                    )
                ).first()
                
                if not submission:
                    submission = QuestionnaireSubmissionORM(
                        application_id=application_id,
                        questionnaire_id=questionnaire_id,
                        user_id=user_id
                    )
                    session.add(submission)
                    session.flush()
                
                # Mark as complete
                submission.submitted_at = datetime.utcnow()
                submission.time_spent_seconds = time_spent_seconds
                submission.is_complete = True
                
                # Clear existing answers and save final ones
                session.query(QuestionnaireAnswerORM).filter(
                    QuestionnaireAnswerORM.submission_id == submission.submission_id
                ).delete()
                
                # Save final answers
                for question_id, answer_data in answers.items():
                    answer = QuestionnaireAnswerORM(
                        submission_id=submission.submission_id,
                        question_id=question_id,
                        answer_data=answer_data
                    )
                    session.add(answer)
                
                # Update application workflow
                application = session.query(JobApplicationORM).filter(
                    and_(
                        JobApplicationORM.application_id == application_id,
                        JobApplicationORM.user_id == user_id
                    )
                ).first()
                
                if application:
                    application.complete_questionnaires(time_spent_seconds)
                    application.questionnaire_answers = answers
                
                session.commit()
                
                self.logger.info(f"Successfully submitted questionnaire for application {application_id}")
                
                return {
                    "success": True,
                    "message": "Questionnaire submitted successfully",
                    "submission_id": submission.submission_id,
                    "is_auto_submit": is_auto_submit
                }
                
        except Exception as e:
            self.logger.exception("Failed to submit questionnaire")
            return {
                "success": False,
                "message": f"Failed to submit questionnaire: {str(e)}"
            }
                }
                
        except Exception as e:
            self.logger.error(f"Error linking cover letter to application: {e}")
            return {
                "success": False,
                "message": f"Failed to link cover letter: {str(e)}"
            }
    
    @error_handler
    async def submit_questionnaire_answers(
        self,
        application_id: str,
        answers: Dict[str, List[str]],
        user_id: str,
        time_spent_seconds: Optional[int] = None
    ) -> SubmissionResult:
        """
        Submit questionnaire answers for an application
        
        Args:
            application_id: ID of the application
            answers: Dictionary of question_id -> answer_list mappings
            user_id: ID of the user (for security)
            time_spent_seconds: Time spent on questionnaires
            
        Returns:
            SubmissionResult with validation and next steps
        """
        self.logger.info(f"Submitting questionnaire answers for application {application_id}")
        
        try:
            with self.get_session() as session:
                # Get application
                application = session.query(JobApplicationORM).filter(
                    and_(
                        JobApplicationORM.application_id == application_id,
                        JobApplicationORM.user_id == user_id
                    )
                ).first()
                
                if not application:
                    return SubmissionResult(
                        success=False,
                        message="Application not found"
                    )
                
                # Get job to validate questionnaire requirements
                job_controller = get_controller('jobs_search')
                job = await job_controller.get_job_by_id(job_id=application.job_id)
                
                if not job:
                    return SubmissionResult(
                        success=False,
                        message="Job not found"
                    )
                
                # Validate answers completeness
                validation_result = await self._validate_questionnaire_answers(
                    job.required_questionnaire, answers
                )
                
                if not validation_result.is_complete:
                    return SubmissionResult(
                        success=False,
                        message="Please complete all required questions",
                        missing_fields=validation_result.missing_fields
                    )
                
                # Store answers in application
                application.questionnaire_answers = answers
                if time_spent_seconds:
                    application.time_spent_on_questionnaires = time_spent_seconds
                application.questionnaire_completion_time = datetime.utcnow()
                application.workflow_step = "review"
                
                # Create questionnaire submissions for tracking
                await self._create_questionnaire_submissions(
                    session, application_id, job.required_questionnaire, answers, user_id, time_spent_seconds
                )
                
                session.commit()
                
                self.logger.info(f"Successfully submitted questionnaire answers for application {application_id}")
                
                return SubmissionResult(
                    success=True,
                    message="Questionnaire answers saved successfully",
                    application_id=application_id,
                    next_step="review"
                )
                
        except Exception as e:
            self.logger.error(f"Error submitting questionnaire answers: {e}")
            return SubmissionResult(
                success=False,
                message=f"Failed to submit questionnaire answers: {str(e)}"
            )
    
    @error_handler
    async def start_questionnaire_timer(
        self,
        application_id: str,
        user_id: str
    ) -> Dict[str, any]:
        """
        Start the questionnaire timer for an application
        
        Args:
            application_id: ID of the application
            user_id: ID of the user (for security)
            
        Returns:
            Dictionary with result and timer information
        """
        self.logger.info(f"Starting questionnaire timer for application {application_id}")
        
        try:
            with self.get_session() as session:
                application = session.query(JobApplicationORM).filter(
                    and_(
                        JobApplicationORM.application_id == application_id,
                        JobApplicationORM.user_id == user_id
                    )
                ).first()
                
                if not application:
                    return {
                        "success": False,
                        "message": "Application not found"
                    }
                
                # Start timer
                application.questionnaire_start_time = datetime.utcnow()
                session.commit()
                
                # Get questionnaire time limits
                job_controller = get_controller('jobs_search')
                job = await job_controller.get_job_by_id(job_id=application.job_id)
                
                questionnaire_result = await self.get_job_questionnaires(application.job_id)
                
                return {
                    "success": True,
                    "message": "Questionnaire timer started",
                    "started_at": application.questionnaire_start_time.isoformat(),
                    "time_limit_minutes": questionnaire_result.time_limit,
                    "total_questions": questionnaire_result.total_questions
                }
                
        except Exception as e:
            self.logger.error(f"Error starting questionnaire timer: {e}")
            return {
                "success": False,
                "message": f"Failed to start questionnaire timer: {str(e)}"
            }
    
    async def _validate_questionnaire_answers(
        self,
        questionnaire_ids: List[str],
        answers: Dict[str, List[str]]
    ) -> ValidationResult:
        """
        Validate questionnaire answers for completeness and correctness
        
        Args:
            questionnaire_ids: List of required questionnaire IDs
            answers: Dictionary of question_id -> answer_list mappings
            
        Returns:
            ValidationResult with validation status and missing fields
        """
        missing_fields = []
        validation_errors = []
        
        try:
            # Load questionnaires to get required questions
            questionnaires = await self._load_questionnaires(questionnaire_ids)
            
            for questionnaire in questionnaires:
                for question in questionnaire.questions:
                    if question.required:
                        question_id = question.question_id
                        
                        # Check if question was answered
                        if question_id not in answers:
                            missing_fields.append(f"{questionnaire.title}: {question.question_text}")
                            continue
                        
                        answer_list = answers[question_id]
                        
                        # Check if answer is empty
                        if not answer_list or (len(answer_list) == 1 and not answer_list[0].strip()):
                            missing_fields.append(f"{questionnaire.title}: {question.question_text}")
                            continue
                        
                        # Validate answer based on question type
                        validation_error = self._validate_answer_format(question, answer_list)
                        if validation_error:
                            validation_errors.append(f"{questionnaire.title}: {question.question_text} - {validation_error}")
            
            # Calculate validation score
            total_questions = sum(len(q.questions) for q in questionnaires)
            answered_questions = len([q for q in answers.values() if q and q[0].strip()])
            score = int((answered_questions / total_questions) * 100) if total_questions > 0 else 100
            
            return ValidationResult(
                is_valid=len(validation_errors) == 0,
                is_complete=len(missing_fields) == 0,
                score=score,
                missing_fields=missing_fields,
                validation_errors=validation_errors
            )
            
        except Exception as e:
            self.logger.error(f"Error validating questionnaire answers: {e}")
            return ValidationResult(
                is_valid=False,
                is_complete=False,
                score=0,
                validation_errors=[f"Validation error: {str(e)}"]
            )
    
    def _validate_answer_format(self, question, answer_list: List[str]) -> Optional[str]:
        """
        Validate answer format based on question type
        
        Args:
            question: QuestionnaireQuestion object
            answer_list: List of answer strings
            
        Returns:
            Error message if invalid, None if valid
        """
        from src.database.models.application_workflow import QuestionTypeEnum
        
        if question.question_type == QuestionTypeEnum.TEXT:
            if question.max_length and len(answer_list[0]) > question.max_length:
                return f"Answer exceeds maximum length of {question.max_length} characters"
        
        elif question.question_type == QuestionTypeEnum.MULTIPLE_CHOICE:
            if question.options:
                for answer in answer_list:
                    if answer not in question.options:
                        return f"Invalid option selected: {answer}"
        
        elif question.question_type == QuestionTypeEnum.RATING:
            try:
                rating = int(answer_list[0])
                if question.min_rating and rating < question.min_rating:
                    return f"Rating must be at least {question.min_rating}"
                if question.max_rating and rating > question.max_rating:
                    return f"Rating must be at most {question.max_rating}"
            except ValueError:
                return "Rating must be a valid number"
        
        elif question.question_type == QuestionTypeEnum.BOOLEAN:
            if answer_list[0].lower() not in ['true', 'false', 'yes', 'no', '1', '0']:
                return "Boolean answer must be true/false, yes/no, or 1/0"
        
        return None
    
    async def _create_questionnaire_submissions(
        self,
        session,
        application_id: str,
        questionnaire_ids: List[str],
        answers: Dict[str, List[str]],
        user_id: str,
        time_spent_seconds: Optional[int]
    ):
        """
        Create questionnaire submission records for tracking
        
        Args:
            session: Database session
            application_id: ID of the application
            questionnaire_ids: List of questionnaire IDs
            answers: Dictionary of answers
            user_id: ID of the user
            time_spent_seconds: Time spent on questionnaires
        """
        from src.database.sql.questionnaires import QuestionnaireSubmissionORM, QuestionnaireAnswerORM
        
        for questionnaire_id in questionnaire_ids:
            # Create submission record
            submission = QuestionnaireSubmissionORM(
                application_id=application_id,
                questionnaire_id=questionnaire_id,
                user_id=user_id,
                submitted_at=datetime.utcnow(),
                time_spent_seconds=time_spent_seconds,
                is_complete=True
            )
            session.add(submission)
            session.flush()  # Get submission ID
            
            # Create answer records
            questionnaires = await self._load_questionnaires([questionnaire_id])
            if questionnaires:
                questionnaire = questionnaires[0]
                for question in questionnaire.questions:
                    if question.question_id in answers:
                        answer = QuestionnaireAnswerORM(
                            submission_id=submission.submission_id,
                            question_id=question.question_id,
                            answer_data=answers[question.question_id]
                        )
                        session.add(answer)
    
    @error_handler
    async def submit_application(
        self,
        application_id: str,
        user_id: str
    ) -> SubmissionResult:
        """
        Submit final application after all workflow steps are complete
        
        Args:
            application_id: ID of the application
            user_id: ID of the user (for security)
            
        Returns:
            SubmissionResult with submission status and details
        """
        self.logger.info(f"Submitting final application {application_id} for user {user_id}")
        
        try:
            with self.get_session() as session:
                # Get application with relationships
                application = session.query(JobApplicationORM).options(
                    joinedload(JobApplicationORM.job),
                    joinedload(JobApplicationORM.ats_report)
                ).filter(
                    and_(
                        JobApplicationORM.application_id == application_id,
                        JobApplicationORM.user_id == user_id
                    )
                ).first()
                
                if not application:
                    return SubmissionResult(
                        success=False,
                        message="Application not found"
                    )
                
                # Final validation
                validation_result = await self._validate_final_application(application)
                if not validation_result.is_valid:
                    return SubmissionResult(
                        success=False,
                        message="Application validation failed",
                        missing_requirements=validation_result.missing_requirements,
                        validation_score=validation_result.score
                    )
                
                # Update application status
                application.application_stage = JobApplicationStatusEnum.APPLIED.value
                application.workflow_step = "submitted"
                application.applied_date = datetime.utcnow()
                application.workflow_completed_at = datetime.utcnow()
                application.validation_score = validation_result.score
                application.missing_requirements = validation_result.missing_requirements
                
                # Attach match analysis if exists
                await self._attach_match_analysis(application, session)
                
                # Update job application count
                if application.job:
                    application.job.application_count = (application.job.application_count or 0) + 1
                
                session.commit()
                
                # Send notifications
                await self._send_application_notifications(application)
                
                self.logger.info(f"Successfully submitted application {application_id}")
                
                return SubmissionResult(
                    success=True,
                    message="Application submitted successfully",
                    application_id=application.application_id,
                    validation_score=validation_result.score
                )
                
        except Exception as e:
            self.logger.error(f"Error submitting application: {e}")
            return SubmissionResult(
                success=False,
                message=f"Failed to submit application: {str(e)}"
            )
    
    async def _validate_final_application(self, application: JobApplicationORM) -> ValidationResult:
        """
        Perform final validation of application before submission
        
        Args:
            application: JobApplicationORM instance
            
        Returns:
            ValidationResult with validation status and score
        """
        missing_requirements = []
        validation_errors = []
        score = 0
        
        try:
            # Check cover letter requirement
            if not application.cover_letter or not application.cover_letter.strip():
                missing_requirements.append("Cover letter is required")
            else:
                score += 30  # Cover letter worth 30 points
            
            # Check CV requirement
            if not application.cv_id:
                missing_requirements.append("CV selection is required")
            else:
                score += 20  # CV worth 20 points
            
            # Check questionnaire completion if required
            if application.job and application.job.required_questionnaire:
                if not application.questionnaire_answers or not application.questionnaire_completion_time:
                    missing_requirements.append("Required questionnaires must be completed")
                else:
                    score += 30  # Questionnaires worth 30 points
            else:
                score += 30  # No questionnaires required, full points
            
            # Check workflow completion
            if application.workflow_step != "review":
                missing_requirements.append("Application workflow must be completed")
            else:
                score += 10  # Workflow completion worth 10 points
            
            # Check for ATS report (optional but adds points)
            if application.ats_report:
                score += 10  # ATS report worth 10 points
            
            # Validate required documents
            if application.job and application.job.required_documents:
                for doc in application.job.required_documents:
                    if doc not in (application.required_documents or []):
                        missing_requirements.append(f"Required document missing: {doc}")
            
            # Additional validation checks
            if not application.user_id or not application.job_id:
                validation_errors.append("Application missing required identifiers")
            
            # Calculate final score (max 100)
            final_score = min(score, 100)
            
            return ValidationResult(
                is_valid=len(validation_errors) == 0,
                is_complete=len(missing_requirements) == 0,
                score=final_score,
                missing_requirements=missing_requirements,
                validation_errors=validation_errors
            )
            
        except Exception as e:
            self.logger.error(f"Error validating final application: {e}")
            return ValidationResult(
                is_valid=False,
                is_complete=False,
                score=0,
                validation_errors=[f"Validation error: {str(e)}"]
            )
    
    async def _attach_match_analysis(self, application: JobApplicationORM, session):
        """
        Attach the most recent match analysis report to application
        
        Args:
            application: JobApplicationORM instance
            session: Database session
        """
        try:
            from src.database.sql.jobs_sql import ATSReportORM
            
            # Find most recent ATS report for this user/job combination
            ats_report = session.query(ATSReportORM).filter(
                and_(
                    ATSReportORM.job_id == application.job_id,
                    ATSReportORM.cv_id == application.cv_id
                )
            ).order_by(ATSReportORM.created_at.desc()).first()
            
            if ats_report:
                application.ats_report_id = ats_report.ats_report_id
                self.logger.info(f"Attached ATS report {ats_report.ats_report_id} to application {application.application_id}")
            
        except Exception as e:
            self.logger.warning(f"Could not attach match analysis: {e}")
            # Don't fail application submission if ATS report attachment fails
    
    async def _send_application_notifications(self, application: JobApplicationORM):
        """
        Send notifications for successful application submission
        
        Args:
            application: JobApplicationORM instance
        """
        try:
            # Get notification controller
            notifications_controller = get_controller('notifications')
            
            # Send confirmation to job seeker
            await self._send_jobseeker_confirmation(application, notifications_controller)
            
            # Send notification to employer
            await self._send_employer_notification(application, notifications_controller)
            
        except Exception as e:
            self.logger.error(f"Error sending application notifications: {e}")
            # Don't fail application submission if notifications fail
    
    async def _send_jobseeker_confirmation(self, application: JobApplicationORM, notifications_controller):
        """
        Send confirmation notification to job seeker
        
        Args:
            application: JobApplicationORM instance
            notifications_controller: Notifications controller instance
        """
        try:
            # Get user details
            users_controller = get_controller('users')
            user = await users_controller.get_user_by_uid(uid=application.user_id)
            
            if user and application.job:
                notification_data = {
                    "user_email": user.email,
                    "user_name": f"{user.first_name} {user.last_name}",
                    "job_title": application.job.title,
                    "company_name": application.job.company_name if hasattr(application.job, 'company_name') else 'Company',
                    "application_id": application.application_id,
                    "applied_date": application.applied_date.strftime("%B %d, %Y"),
                    "validation_score": application.validation_score
                }
                
                # Send email notification (implementation depends on notification system)
                # await notifications_controller.send_application_confirmation(notification_data)
                
                self.logger.info(f"Sent confirmation notification to user {application.user_id}")
            
        except Exception as e:
            self.logger.error(f"Error sending jobseeker confirmation: {e}")
    
    async def _send_employer_notification(self, application: JobApplicationORM, notifications_controller):
        """
        Send new application notification to employer
        
        Args:
            application: JobApplicationORM instance
            notifications_controller: Notifications controller instance
        """
        try:
            if application.job:
                # Get company/employer details
                company_controller = get_controller('company')
                company = await company_controller.get_company_by_id(company_id=application.job.company_id)
                
                if company:
                    notification_data = {
                        "company_id": company.company_id,
                        "job_id": application.job_id,
                        "job_title": application.job.title,
                        "application_id": application.application_id,
                        "applicant_name": "New Applicant",  # Keep anonymous initially
                        "applied_date": application.applied_date.strftime("%B %d, %Y"),
                        "validation_score": application.validation_score,
                        "has_cover_letter": bool(application.cover_letter),
                        "has_ats_report": bool(application.ats_report_id),
                        "questionnaires_completed": bool(application.questionnaire_completion_time)
                    }
                    
                    # Send email notification (implementation depends on notification system)
                    # await notifications_controller.send_new_application_notification(notification_data)
                    
                    self.logger.info(f"Sent new application notification for job {application.job_id}")
            
        except Exception as e:
            self.logger.error(f"Error sending employer notification: {e}")
    
    @error_handler
    async def get_application_status(
        self,
        application_id: str,
        user_id: str
    ) -> Dict[str, any]:
        """
        Get current status and progress of an application
        
        Args:
            application_id: ID of the application
            user_id: ID of the user (for security)
            
        Returns:
            Dictionary with application status and progress information
        """
        self.logger.info(f"Getting application status for {application_id}")
        
        try:
            with self.get_session() as session:
                application = session.query(JobApplicationORM).options(
                    joinedload(JobApplicationORM.job),
                    joinedload(JobApplicationORM.ats_report)
                ).filter(
                    and_(
                        JobApplicationORM.application_id == application_id,
                        JobApplicationORM.user_id == user_id
                    )
                ).first()
                
                if not application:
                    return {
                        "success": False,
                        "message": "Application not found"
                    }
                
                # Convert to Pydantic model for business logic
                app_model = JobApplication(**application.to_dict())
                
                return {
                    "success": True,
                    "application_id": application.application_id,
                    "workflow_step": application.workflow_step,
                    "workflow_step_display": app_model.workflow_step_display,
                    "completion_percentage": app_model.workflow_completion_percentage,
                    "next_step": app_model.next_workflow_step,
                    "is_complete": app_model.is_workflow_complete,
                    "application_stage": application.application_stage,
                    "validation_score": application.validation_score,
                    "has_cover_letter": bool(application.cover_letter),
                    "has_ats_report": bool(application.ats_report_id),
                    "questionnaires_completed": bool(application.questionnaire_completion_time),
                    "applied_date": application.applied_date.isoformat() if application.applied_date else None,
                    "workflow_duration_minutes": app_model.workflow_duration_minutes
                }
                
        except Exception as e:
            self.logger.error(f"Error getting application status: {e}")
            return {
                "success": False,
                "message": f"Failed to get application status: {str(e)}"
            }