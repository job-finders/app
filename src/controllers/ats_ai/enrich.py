import openai
from typing import List
from .models import AIEnhancementSuggestion, SuggestionImpact
from .extract import build_keyword_intelligence

SYSTEM_PROMPT = """
You are a senior technical recruiter and ATS optimisation expert.
Given a job description and a list of high-impact missing keywords,
produce concrete, recruiter-friendly suggestions.
Return JSON only.
"""


def generate_suggestions(job: Job) -> List[AIEnhancementSuggestion]:
    keywords = build_keyword_intelligence(job)
    missing = [kw.keyword for kw in keywords if kw.keyword not in job.job_keyword_listing]

    prompt = f"""
Job Title: {job.title}
Description: {job.description}
Required Skills: {job.required_skills}
Preferred Skills: {job.preferred_skills}
Missing High-Impact Keywords: {missing}
"""
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        max_tokens=1000,
    )
    data = response.choices[0].message.content
    # Expect array of dicts that map to AIEnhancementSuggestion
    return [AIEnhancementSuggestion(**item) for item in data.get("suggestions", [])]
