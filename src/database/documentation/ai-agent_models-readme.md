# agent_models.py Documentation

## Overview

This module defines Pydantic models used by AI agents within the Job Finders platform. These models represent various types of data, including CV optimization suggestions, cover letter outputs, job match insights, job post insights, and candidate benchmark reports.

## Models

### CVOptimizationSuggestion

Represents suggestions for optimizing a candidate's CV.

*   `summary`: A summary of the CV's strengths and weaknesses.
*   `suggested_changes`: A list of specific changes to improve the CV.
*   `ats_keywords`: A list of keywords to include for better ATS compatibility.

### CoverLetterOutput

Represents the output of a cover letter generation process.

*   `opening`: The opening paragraph of the cover letter.
*   `body`: The main body of the cover letter.
*   `closing`: The closing paragraph of the cover letter.

### JobMatchInsights

Represents insights into how well a candidate matches a job.

*   `match_score`: A numerical score representing the match quality.
*   `reasons`: A list of reasons why the candidate is a good or bad match.
*   `suggested_improvements`: A list of suggestions for the candidate to improve their match.

### JobPostInsights

Represents insights into the quality and effectiveness of a job post.

*   `clarity_score`: A numerical score representing the clarity of the job description.
*   `salary_benchmark`: A benchmark of the salary offered compared to similar jobs.
*   `missing_information`: A list of information missing from the job description.
*   `suggestions`: A list of suggestions for improving the job post.

### CandidateBenchmarkReport

Represents a comprehensive candidate evaluation report containing dual-perspective insights

*   `summary`: Concise overall assessment of candidate-job fit
*   `percentile_rank`: Candidate's competitive position percentile (0-100 scale)
*   `key_strengths`: Candidate's strongest qualifications relative to position
*   `development_areas`: Areas needing improvement for this specific role
*   `employer_insights`: Hiring considerations specific to employer perspective
*   `candidate_insights`: Career development insights specific to candidate perspective
*   `interview_indicators`: Key areas to explore during interviews (employer only)
*   `cv_optimization_tips`: Specific CV improvements for this role (candidate only)
*   `risk_factors`: Potential concerns about candidate fit (employer only)
*   `growth_opportunities`: Career development paths (candidate only)

## Relationships to SQL Models

This model corresponds to the following SQL model:

*   [`AgentSessionORM`](src/database/sql/agent_session.py:8)

The `AgentSessionORM` stores the `agent_name` and `context_data`, which can include instances of the models defined in `agent_models.py`.