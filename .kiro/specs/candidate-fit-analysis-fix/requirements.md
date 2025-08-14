# Requirements Document

## Introduction

This feature fixes the broken AI-Based Candidate Fit Analysis functionality in the job detail page. Currently, the "
Analyze Match" button in the job sidebar does not work because it calls a non-existent API endpoint. The system already
has the backend infrastructure for candidate analysis through the candidate benchmark controller, but the frontend
integration is incomplete.

The feature will connect the existing UI components to the correct backend endpoints, ensuring job seekers can analyze
how well their CV matches a specific job posting using AI-powered insights.

## Requirements

### Requirement 1

**User Story:** As a job seeker, I want to analyze how well my CV matches a job posting, so that I can understand my fit
for the role and improve my application strategy.

#### Acceptance Criteria

1. WHEN I select a CV from the dropdown in the "AI Based - Candidate Fit Analysis" section THEN the system SHALL
   validate that a CV is selected
2. WHEN I click the "Analyze Match" button THEN the system SHALL call the correct backend endpoint for employee
   candidate analysis
3. WHEN the analysis is processing THEN the button SHALL show a loading state with spinner and "Analyzing..." text
4. WHEN the analysis completes successfully THEN the system SHALL display the match results in the designated results
   area
5. WHEN the analysis fails THEN the system SHALL display an appropriate error message to the user
6. WHEN the analysis completes (success or failure) THEN the button SHALL return to its original state

### Requirement 2

**User Story:** As a job seeker, I want to see detailed AI-powered insights about my job match, so that I can understand
my strengths and areas for improvement.

#### Acceptance Criteria

1. WHEN the candidate analysis completes successfully THEN the system SHALL display a match score as a percentage or
   rating
2. WHEN the analysis results are shown THEN the system SHALL display a summary of key insights about the match
3. WHEN the results include recommendations THEN the system SHALL display actionable suggestions for improvement
4. WHEN the results are displayed THEN they SHALL be formatted in a user-friendly, readable manner
5. WHEN multiple analyses are performed THEN the previous results SHALL be replaced with new results

### Requirement 3

**User Story:** As a developer, I want the candidate analysis to use the existing backend infrastructure, so that we
maintain consistency and avoid code duplication.

#### Acceptance Criteria

1. WHEN implementing the fix THEN the system SHALL use the existing `/agents/employee/v1/jobs/<job_id>/match-analysis`
   endpoint
2. WHEN calling the backend THEN the system SHALL pass the correct job_id and cv_id parameters
3. WHEN handling the response THEN the system SHALL properly parse the CandidateBenchmarkReport model structure
4. WHEN errors occur THEN the system SHALL handle them using the existing error handling patterns
5. WHEN authentication is required THEN the system SHALL use the existing jobseeker authentication

### Requirement 4

**User Story:** As a system administrator, I want proper error handling and logging for candidate analysis requests, so
that I can monitor and troubleshoot issues.

#### Acceptance Criteria

1. WHEN a candidate analysis request fails THEN the system SHALL log the error with appropriate detail level
2. WHEN network errors occur THEN the system SHALL display user-friendly error messages
3. WHEN validation errors occur THEN the system SHALL display specific validation feedback
4. WHEN the CV list is empty THEN the system SHALL display appropriate messaging to guide the user
5. WHEN the job data is missing THEN the system SHALL handle the error gracefully

### Requirement 5

**User Story:** As a job seeker, I want the analysis feature to work seamlessly with my existing CV management, so that
I can easily analyze different CVs against the same job.

#### Acceptance Criteria

1. WHEN I have multiple CVs THEN the dropdown SHALL display all my available CVs with meaningful titles
2. WHEN I select a different CV THEN I SHALL be able to run a new analysis with that CV
3. WHEN I have no CVs uploaded THEN the system SHALL display guidance on how to upload a CV
4. WHEN my CV data is incomplete THEN the system SHALL still attempt analysis but may show limited results
5. WHEN switching between CVs THEN the previous analysis results SHALL be cleared appropriately