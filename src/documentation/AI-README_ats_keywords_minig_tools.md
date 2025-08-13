# ATS Keywords Mining Tools Documentation

This module defines keyword extraction tools for optimizing job descriptions, leveraging industry taxonomies, peer job analysis, and parsed CV data.

## Overview

The module provides a set of classes that inherit from a base `KeywordTool` class. Each class implements a `fetch` method to extract relevant keywords from different sources to improve the Applicant Tracking System (ATS) score of job descriptions.

## Classes

### `IndustryTaxonomyTool(KeywordTool)`

- **Purpose**: Extracts keywords from an industry taxonomy based on the job title, description, and skills.
- **Source Type**: `KeywordSourceType.INDUSTRY_TAXONOMY`
- **Methods**:
  - `fetch(job: ATSOptimisationInput) -> list[tuple[str, int]]`:
    - Fetches keywords from the `industry_taxonomy` controller based on the job's title, description, and skills.
    - Returns a list of keywords and their frequencies.
    - **Dependencies**:
      - `industry_taxonomy` controller (TODO: Add to factory).
- **Example Usage**:
  ```python
  tool = IndustryTaxonomyTool()
  keywords = await tool.fetch(job_data)
  ```

### `PeerJobsTool(KeywordTool)`

- **Purpose**: Extracts keywords from successful peer job postings.
- **Source Type**: `KeywordSourceType.PEER_JOBS`
- **AI-readable Task List**:
  1.  Acquire `jobs_workflow` controller: `j_ctl = get_controller("jobs_workflow")`
  2.  Fetch similar jobs: `similar_jobs: list[Job] = await j_ctl.get_similar_jobs(job.id)`
  3.  Compute success metrics:
      -   `applications_count = job.total_applications`
      -   `hired_count = await j_ctl.count_applications_by_stage(job.job_id, "hired")`
      -   `average_ats_score = job.job_ats_score or 0`
  4.  Filter jobs: Keep jobs where `(hired_count ≥ min_success OR applications_count ≥ min_applications) AND average_ats_score ≥ min_ats_score`
  5.  Tokenize & aggregate keywords: Use `job.ats_description` for rich text.
  6.  Return `list[tuple[str, int]]` sorted by descending frequency.
- **Attributes**:
  - `min_success` (int): Minimum number of successful (hired) applications for a job to be considered. Default: 1.
  - `min_applications` (int): Minimum total applications for a job to be considered. Default: 15.
  - `min_ats_score` (int): Minimum ATS score for a job to be considered. Default: 70.
  - `similar_jobs_limit` (int): Maximum number of similar jobs to fetch. Default: 20.
- **Methods**:
  - `fetch(job: ATSOptimisationInput) -> list[tuple[str, int]]`:
    - Fetches similar jobs, filters them based on success metrics, and extracts keywords from their ATS descriptions.
    - Returns a list of keywords and their frequencies.
    - **Dependencies**:
      - `jobs_workflow` controller.
      - `jobs_search` controller.
- **Example Usage**:
  ```python
  tool = PeerJobsTool(min_success=2, min_applications=20)
  keywords = await tool.fetch(job_data)
  ```

### `ParsedCVsTool(KeywordTool)`

- **Purpose**: Extracts keywords from successful resumes (CVs) that have been parsed.
- **Source Type**: `KeywordSourceType.PARSED_CVS`
- **AI-readable Task List**:
  1.  Acquire controllers:
      -   `resume_controller = get_controller("resume")`
      -   `job_controller = get_controller("jobs_workflow")`
  2.  Obtain similar jobs that have applications: `similar_jobs = await job_controller.get_similar_jobs(job.id); relevant_jobs = [j for j in similar_jobs if getattr(j, "applications_count", 0) > 0]`
  3.  For each job, fetch the most-successful resumes:
      -   `outcome in success_outcomes`
      -   `min_ats_score ≥ min_resume_ats_score`
      -   `trust_score ≥ min_trust_score` (optional quality gate)
  4.  Aggregate weighted keywords from the **entire resume context**:
      -   skills (highest weight)
      -   professional_title
      -   summary
      -   experience
      -   projects
      -   certifications
      -   languages
  5.  Return keywords sorted by `(tf-idf * trust_score)` descending.

- **Attributes**:
  - `success_outcomes` (list[str] | None): List of application outcomes considered successful. Default: `["interviewed", "hired"]`.
  - `min_resume_ats_score` (int): Minimum ATS score for a resume to be considered. Default: 70.
  - `min_trust_score` (int): Minimum trust score for a resume to be considered. Default: 60.
  - `similar_jobs_limit` (int): Maximum number of similar jobs to fetch. Default: 20.
  - `resumes_per_job_limit` (int): Maximum number of resumes to fetch per job. Default: 20.
  - `weight_skills` (int): Weight for skills keywords. Default: 3.
  - `weight_title` (int): Weight for professional title keywords. Default: 2.
  - `weight_summary` (int): Weight for summary keywords. Default: 2.
  - `weight_other` (int): Weight for other keywords (experience, projects, etc.). Default: 1.
- **Methods**:
  - `fetch(job: ATSOptimisationInput) -> list[tuple[str, int]]`:
    - Fetches similar jobs, collects successful resumes, and extracts weighted keywords from the entire resume context.
    - Returns keywords sorted by weighted TF-IDF.
    - **Dependencies**:
      -   `resume` controller.
      -   `jobs_search` controller.
- **Example Usage**:
  ```python
  tool = ParsedCVsTool(min_resume_ats_score=80, weight_skills=5)
  keywords = await tool.fetch(job_data)
  ```

## Usage Patterns

1.  **Initialization**: Create an instance of the desired keyword tool, configuring any relevant parameters.
2.  **Fetching Keywords**: Call the `fetch` method, passing in an `ATSOptimisationInput` object representing the job.
3.  **Analyzing Results**: Process the returned list of keywords and their frequencies to optimize the job description.

## Example

```python
from src.controllers.agents.ats_keywords_minig_tools import IndustryTaxonomyTool, PeerJobsTool, ParsedCVsTool
from src.database.models import ATSOptimisationInput

# Sample job data
job_data = ATSOptimisationInput(
    job_id="123",
    title="Software Engineer",
    description="We are looking for a skilled software engineer...",
    required_skills=["python", "java", "aws"],
    preferred_skills=["docker", "kubernetes"]
)

# Use IndustryTaxonomyTool
industry_tool = IndustryTaxonomyTool()
industry_keywords = await industry_tool.fetch(job_data)
print("Industry Keywords:", industry_keywords)

# Use PeerJobsTool
peer_tool = PeerJobsTool()
peer_keywords = await peer_tool.fetch(job_data)
print("Peer Job Keywords:", peer_keywords)

# Use ParsedCVsTool
cv_tool = ParsedCVsTool()
cv_keywords = await cv_tool.fetch(job_data)
print("CV Keywords:", cv_keywords)
```

## Notes

-   The `industry_taxonomy` controller is a TODO and needs to be added to the factory for the `IndustryTaxonomyTool` to function correctly.
-   These tools leverage other controllers and services to gather data, so ensure those dependencies are properly configured.
-   Consider the performance implications of fetching and processing large amounts of data, especially when using the `ParsedCVsTool`.