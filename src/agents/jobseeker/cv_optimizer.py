# agents/jobseeker/cv_optimizer.py
from src.agents.base import BaseAgent
from src.database.models import Job, JobSeekerCV


from typing import List, Optional
from pydantic import BaseModel, Field


class SectionImprovement(BaseModel):
    """

    Represents a specific section of the CV where improvements can be made to better align with the job description
    or improve ATS compatibility.

    Attributes:
    - section: The name of the CV section to improve (e.g., "summary", "experience", "skills").
    - current_text: The current text in the specified section, if available.
    - suggested_text: A revised version of the section text that improves alignment with the job.
    - reason: A brief explanation of why this change improves the CV's quality or relevance.
    """
    section: str
    current_text: Optional[str]
    suggested_text: Optional[str]
    reason: Optional[str]


class MissingSkill(BaseModel):
    """
    Identifies a skill missing from the CV that is required or preferred in the job description.

    Attributes:
    - skill: The name of the missing skill (e.g., "Python", "project management").
    - event_type: Indicates whether the skill is "required" or "preferred".
    - reason: Explanation of why this skill is important for the job or why its absence is notable.
    """
    skill: str
    type: str  # e.g., "required", "preferred"
    reason: Optional[str]


class FormattingIssue(BaseModel):
    """
    Describes a formatting issue in the CV that may affect readability or ATS parsing.

    Attributes:
    - issue: Description of the formatting problem (e.g., inconsistent fonts, missing headers).
    - recommendation: Suggested change to correct or improve the formatting.
    """
    issue: str
    recommendation: str


class RedFlag(BaseModel):
    """
    Identifies potential red flags or concerns in the CV that may negatively affect job application success.

    Attributes:
    - issue: Description of the red flag (e.g., employment gap, vague job title).
    - impact: Severity of the issue ("low", "moderate", or "high").
    - suggestion: Optional recommendation for how to address or mitigate the issue.
    """
    issue: str
    impact: str  # e.g., "low", "moderate", "high"
    suggestion: Optional[str]


class KeywordMatchAnalysis(BaseModel):
    """
    Provides a breakdown of how well the CV matches the job description in terms of keyword usage.

    Attributes:
    - matched_keywords: List of keywords that are present in both the CV and job description.
    - missing_keywords: Keywords from the job description that are not found in the CV.
    - match_percentage: Percentage of important keywords that appear in the CV (0 to 100).
    """
    matched_keywords: List[str]
    missing_keywords: List[str]
    match_percentage: float


class CVOptimizationSuggestion(BaseModel):
    """
    Main structured output for CV optimization, summarizing all feedback, issues, and improvements.

    Attributes:
    - summary: High-level summary of the overall CV quality and improvement suggestions.
    - section_improvements: List of improvements for individual sections of the CV.
    - missing_skills: Skills that are missing from the CV but relevant to the job.
    - ats_keywords: Keywords recommended for better ATS alignment based on the job description.
    - formatting_issues: Formatting concerns that may hinder ATS readability or professional presentation.
    - red_flags: Potential issues in the CV that may raise concerns for employers or recruiters.
    - keyword_match_analysis: Object summarizing keyword overlap and match performance.
    - overall_score: Estimated CV-to-job match score (range: 0–100).
    """
    summary: str = Field(..., description="High-level summary of improvements.")
    section_improvements: List[SectionImprovement] = Field(default_factory=list)
    missing_skills: List[MissingSkill] = Field(default_factory=list)
    ats_keywords: List[str] = Field(default_factory=list, description="Recommended keywords for ATS matching.")
    formatting_issues: List[FormattingIssue] = Field(default_factory=list)
    red_flags: List[RedFlag] = Field(default_factory=list)
    keyword_match_analysis: Optional[KeywordMatchAnalysis] = None
    overall_score: Optional[float] = Field(None, description="An estimated CV-Job match score from 0 to 100.")

    class Config:
        from_attributes = True

class CVOptimizerAgent(BaseAgent):
    name = "cv_optimizer"
    description = "Suggests ATS-optimized improvements for a CV using job data."

    def prompt(self, cv: JobSeekerCV, job: Job) -> str:
        job_summary = job.ats_description
        job_skills = ", ".join(job.required_skills + job.preferred_skills)
        job_education = job.education_requirements or {}

        return (
            f"You are an ATS optimization assistant. Your task is to help a job seeker improve their CV "
            f"so it matches the job posting provided below.\n\n"
            f"## Job Posting ##\n"
            f"{job_summary}\n\n"
            f"Experience Level: {job.experience_level}\n"
            f"Education Requirements: {job_education}\n"
            f"Required Skills: {', '.join(job.required_skills)}\n"
            f"Preferred Skills: {', '.join(job.preferred_skills)}\n"
            f"Location: {job.location}\n\n"
            f"## Job Seeker CV ##\n"
            f"Professional Title: {cv.professional_title}\n"
            f"Summary: {cv.summary or 'N/A'}\n"
            f"Skills: {', '.join(cv.skills)}\n"
            f"Education: {[e.degree + ' at ' + e.institution for e in cv.education]}\n"
            f"Experience: {[exp.title + ' at ' + exp.company for exp in cv.experience]}\n"
            f"Certifications: {[c.name for c in (cv.certifications or [])]}\n"
            f"Projects: {[p.name for p in (cv.projects or [])]}\n"
            f"Languages: {[lang.name for lang in (cv.languages or [])]}\n"
            f"Awards: {[a.title for a in (cv.awards or [])]}\n\n"
            f"## Instructions ##\n"
            f"Compare the CV to the job posting and provide:\n"
            f"- A list of missing keywords or skills\n"
            f"- Suggestions for improving the summary or experience sections\n"
            f"- Format or layout improvements (if relevant for ATS parsing)\n"
            f"- Any potential red flags (e.g., missing experience, lack of degree)\n\n"
            f"Return the response as structured JSON for programmatic use."
        )

    def system_prompt(self) -> str:
        return (
            "You are a CV optimization assistant. Your role is to improve a job seeker's CV by comparing it against a job post "
            "and returning suggestions in structured JSON format. Focus on keyword alignment, relevance of experience, clarity of the summary, and ATS formatting best practices."
        )

    def output_model(self):
        return CVOptimizationSuggestion
