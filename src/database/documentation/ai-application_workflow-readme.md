# application_workflow.py Documentation

## Overview

This module defines Pydantic models for managing the job application workflow process, including cover letter generation, questionnaire handling, and application submission.

## Models

### WorkflowStepEnum

An enumeration of possible workflow steps:

*   `DRAFT`: Initial draft state.
*   `COVER_LETTER`: Cover letter generation step.
*   `QUESTIONNAIRES`: Questionnaire completion step.
*   `REVIEW`: Application review step.
*   `SUBMITTED`: Application submitted.

### QuestionTypeEnum

An enumeration of possible question types for questionnaires:

*   `MULTIPLE_CHOICE`: Multiple choice question.
*   `TEXT`: Text-based question.
*   `BOOLEAN`: Boolean (true/false) question.
*   `RATING`: Rating scale question.

### ApplicationWorkflowResult

Represents the result of starting an application workflow.

*   `success`: Indicates whether the workflow started successfully.
*   `message`: An optional message describing the result.
*   `application_id`: The ID of the application.
*   `next_step`: The next workflow step to be completed.
*   `cover_letter_exists`: Indicates whether a cover letter already exists.
*   `questionnaires_required`: Indicates whether questionnaires are required.
*   `workflow_step`: The current workflow step.

### QuestionnaireQuestion

Represents an individual question within a questionnaire.

*   `question_id`: Unique identifier for the question (UUID).
*   `question_text`: The text of the question.
*   `question_type`: The type of question (from `QuestionTypeEnum`).
*   `required`: Indicates whether the question is required.
*   `options`: A list of options for multiple choice questions.
*   `max_length`: The maximum length for text-based questions.
*   `min_rating`: The minimum rating value for rating questions.
*   `max_rating`: The maximum rating value for rating questions.
*   `order_index`: Order of question in the questionnaire

### Questionnaire

Represents a questionnaire definition.

*   `questionnaire_id`: Unique identifier for the questionnaire (UUID).
*   `title`: The title of the questionnaire.
*   `description`: An optional description of the questionnaire.
*   `time_limit`: The time limit for completing the questionnaire (in minutes).
*   `questions`: A list of `QuestionnaireQuestion` objects.
*   `is_active`: Indicates whether the questionnaire is active.
*   `created_at`: The date and time the questionnaire was created.

### QuestionnaireResult

Represents the result of retrieving a questionnaire.

*   `success`: Indicates whether the retrieval was successful.
*   `questionnaires`: A list of `Questionnaire` objects.
*   `time_limit`: The total time limit for completing the questionnaires (in minutes).
*   `message`: An optional message describing the result.
*   `total_questions`: The total number of questions in all questionnaires.

### ValidationResult

Represents the result of validating an application.

*   `is_valid`: Indicates whether the application is valid.
*   `is_complete`: Indicates whether the application is complete.
*   `score`: A score representing the quality of the application.
*   `missing_fields`: A list of missing fields in the application.
*   `missing_requirements`: A list of missing requirements for the application.
*   `validation_errors`: A list of validation errors in the application.

### SubmissionResult

Represents the result of submitting an application.

*   `success`: Indicates whether the submission was successful.
*   `message`: A message describing the result.
*   `application_id`: The ID of the submitted application.
*   `missing_fields`: A list of missing fields in the application.
*   `missing_requirements`: A list of missing requirements for the application.
*   `validation_score`: The validation score for the application.
*   `next_step`: The next step in the application process.

### CoverLetterSession

Represents a cover letter generation session.

*   `session_id`: Unique identifier for the session (UUID).
*   `user_id`: The ID of the user creating the cover letter.
*   `job_id`: The ID of the job the cover letter is for.
*   `cv_id`: The ID of the CV being used.
*   `draft_text`: The draft text of the cover letter.
*   `selected_tone`: The selected tone for the cover letter.
*   `generated_letter`: The generated cover letter text.
*   `created_at`: The date and time the session was created.
*   `expires_at`: The date and time the session expires.
*   `is_active`: Indicates whether the session is active.

### QuestionnaireAnswer

Represents an individual answer to a questionnaire question.

*   `question_id`: The ID of the question being answered.
*   `answer`: The answer to the question.
*   `answered_at`: The date and time the question was answered.

### QuestionnaireSubmission

Represents a complete questionnaire submission.

*   `application_id`: The ID of the application the submission is for.
*   `questionnaire_id`: The ID of the questionnaire being submitted.
*   `answers`: A list of `QuestionnaireAnswer` objects.
*   `started_at`: The date and time the questionnaire was started.
*   `submitted_at`: The date and time the questionnaire was submitted.
*   `time_spent_seconds`: The time spent completing the questionnaire (in seconds).
*   `is_complete`: Indicates whether the questionnaire is complete.

### ApplicationProgress

Represents the progress of an application through the workflow.

*   `application_id`: The ID of the application.
*   `current_step`: The current workflow step (from `WorkflowStepEnum`).
*   `completed_steps`: A list of completed workflow steps.
*   `cover_letter_completed`: Indicates whether the cover letter has been completed.
*   `questionnaires_completed`: Indicates whether the questionnaires have been completed.
*   `validation_passed`: Indicates whether the application has passed validation.
*   `completion_percentage`: The percentage of the workflow that has been completed.

## Relationships to SQL Models

This model has some relationship to the following SQL models:

*   [`JobApplicationORM`](src/database/sql/jobs_sql.py:333)

It defines the application workflow and is used in the `JobApplicationORM` model to track the progress of an application.