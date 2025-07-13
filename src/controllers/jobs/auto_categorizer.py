from __future__ import annotations
import re
from typing import Tuple, Optional


class AutoCategorizer:
    """
    Lightweight, deterministic job-post categorizer.

    Returns
    -------
    (category_slug: str, confidence: float)
        confidence is 0-1; values < 0.15 are considered “unknown”.
    """

    # --------------------------------------------------
    # 1. Curated lexicon
    #    key   -> slug used in the job-portal taxonomy
    #    value -> list of (keyword, weight) tuples
    # --------------------------------------------------
    _LEXICON: dict[str, list[tuple[str, float]]] = {
        "programming": [
            ("software engineer", 3.0), ("developer", 2.5), ("programmer", 2.5),
            ("python", 2.0), ("java", 2.0), ("javascript", 2.0), ("react", 2.0),
            ("backend", 2.0), ("frontend", 2.0), ("fullstack", 2.0), ("api", 1.5),
            ("coding", 1.5), ("git", 1.0), ("microservice", 1.0)
        ],
        "information-technology": [
            ("it support", 3.0), ("network admin", 2.5), ("devops", 2.5),
            ("cybersecurity", 2.5), ("cloud", 2.0), ("systems analyst", 2.0),
            ("infrastructure", 2.0), ("data center", 2.0), ("help desk", 1.5),
            ("tech support", 1.5), ("linux", 1.0), ("windows server", 1.0)
        ],
        "data-science": [
            ("data scientist", 3.0), ("data analyst", 2.5), ("machine learning", 2.5),
            ("ml engineer", 2.5), ("ai", 2.0), ("statistics", 1.5), ("sql", 1.5),
            ("pandas", 1.0), ("tensorflow", 1.0), ("pytorch", 1.0)
        ],
        "engineering": [
            ("mechanical engineer", 3.0), ("civil engineer", 3.0), ("electrical engineer", 3.0),
            ("design engineer", 2.5), ("project engineer", 2.0), ("cad", 1.5),
            ("autocad", 1.5), ("solidworks", 1.5), ("pe (licensed)", 1.0)
        ],
        "building-construction": [
            ("construction manager", 3.0), ("site supervisor", 2.5), ("foreman", 2.0),
            ("plumber", 2.0), ("electrician", 2.0), ("carpenter", 2.0), ("bricklayer", 2.0),
            ("hvac", 1.5), ("welder", 1.5), ("scaffolding", 1.0)
        ],
        "business-management": [
            ("project manager", 3.0), ("operations manager", 3.0), ("business development", 2.5),
            ("strategy", 2.0), ("team lead", 2.0), ("director", 2.0), ("vp", 2.0),
            ("coordinator", 1.5), ("consultant", 1.5)
        ],
        "sales": [
            ("sales representative", 3.0), ("account executive", 2.5), ("sales manager", 2.5),
            ("business development rep", 2.5), ("inside sales", 2.0), ("field sales", 2.0),
            ("quota", 1.0), ("crm", 1.0)
        ],
        "finance": [
            ("accountant", 3.0), ("financial analyst", 2.5), ("bookkeeper", 2.5),
            ("auditor", 2.5), ("controller", 2.0), ("investment", 1.5), ("banking", 1.5),
            ("payroll", 1.5), ("cpa", 1.0)
        ],
        "marketing": [
            ("marketing manager", 3.0), ("digital marketing", 2.5), ("seo", 2.0),
            ("content marketing", 2.0), ("growth marketer", 2.0), ("social media", 1.5),
            ("campaign", 1.5), ("brand manager", 1.5)
        ],
        "education": [
            ("teacher", 3.0), ("professor", 2.5), ("lecturer", 2.5), ("instructor", 2.0),
            ("tutor", 2.0), ("curriculum", 1.5), ("e-learning", 1.5)
        ],
        "healthcare-nursing": [
            ("registered nurse", 3.0), ("rn", 2.5), ("nurse practitioner", 2.5),
            ("licensed practical nurse", 2.5), ("midwife", 2.0), ("caregiver", 1.5)
        ],
        "healthcare-other": [
            ("physician", 3.0), ("pharmacist", 2.5), ("lab technician", 2.0),
            ("radiologist", 2.0), ("therapist", 2.0), ("medical assistant", 1.5),
            ("dental hygienist", 1.5)
        ],
        "office-admin": [
            ("administrative assistant", 3.0), ("receptionist", 2.5), ("office assistant", 2.0),
            ("secretary", 2.0), ("clerk", 2.0), ("front desk", 1.5), ("scheduler", 1.5)
        ],
        "legal": [
            ("lawyer", 3.0), ("attorney", 3.0), ("paralegal", 2.5), ("legal assistant", 2.5),
            ("compliance", 2.0), ("contracts", 1.5)
        ],
        "hr": [
            ("hr manager", 3.0), ("recruiter", 2.5), ("talent acquisition", 2.0),
            ("hr generalist", 2.0), ("payroll specialist", 1.5), ("onboarding", 1.0)
        ],
        "customer-service": [
            ("customer service", 3.0), ("call center", 2.5), ("support agent", 2.0),
            ("help desk", 2.0), ("client success", 1.5)
        ],
        "cleaning-maintenance": [
            ("cleaner", 3.0), ("janitor", 2.5), ("custodian", 2.5), ("maintenance", 2.0),
            ("housekeeping", 2.0), ("groundskeeper", 1.5)
        ],
        "agriculture": [
            ("farm manager", 3.0), ("agricultural technician", 2.5), ("harvest", 2.0),
            ("crop", 2.0), ("irrigation", 2.0), ("livestock", 2.0), ("farming", 2.0)
        ],
        "transport-logistics": [
            ("driver", 2.5), ("logistics coordinator", 2.5), ("supply chain", 2.0),
            ("warehouse", 2.0), ("forklift", 1.5), ("courier", 1.5)
        ],
        "community-social-welfare": [
            ("social worker", 3.0), ("community outreach", 2.5), ("ngo", 2.0),
            ("welfare", 2.0), ("non-profit", 2.0), ("humanitarian", 1.5)
        ]
    }

    # --------------------------------------------------
    # 2. Categorization method
    # --------------------------------------------------
    @classmethod
    async def categorize(cls, title: str, description: str = "") -> Tuple[Optional[str], float]:
        title = (title or "").strip()
        description = (description or "").strip()
        if not title:
            return None, 0.0

        text = f"{title} {description}".lower()
        # Remove punctuation for cleaner matching
        text = re.sub(r"[^\w\s]", " ", text)

        scores = {cat: 0.0 for cat in cls._LEXICON}
        for cat, kw_list in cls._LEXICON.items():
            for kw, weight in kw_list:
                # Multi-word phrases first
                if " " in kw:
                    scores[cat] += weight * text.count(kw)
                else:
                    # Whole-word match to avoid “java” in “javascript”
                    scores[cat] += weight * len(re.findall(rf"\b{re.escape(kw)}\b", text))

        best_cat = max(scores, key=scores.get)
        best_score = scores[best_cat]
        total = sum(scores.values()) or 1  # avoid div by zero
        confidence = best_score / total

        if confidence < 0.15:
            return None, 0.0
        return best_cat, round(confidence, 3)
