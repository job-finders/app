import json, os, re, uuid, aiohttp, docx2txt, fitz, spacy

from datetime import datetime, timezone
from typing import Dict, List, Optional
from flask import Request, Flask
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer

from src.controllers.controller import Controllers, error_handler
from src.database.models.jobs_model import Job, ATSReport
from src.database.sql.config import ConfigurationORM
from src.database.models.resume import JobSeekerCV
from src.controllers.resumes import ResumeController

# single, shared spaCy model instance
_NLP = spacy.load("en_core_web_sm", disable=["parser", "ner"])
CLEAN_TEXT_PATTERN = re.compile(r'[^a-zA-Z0-9\+#\.\s]')
ACTION_VERBS = {"manage", "develop", "lead", "create", "implement"}


class ATSToolController(Controllers):
    """CPU‑optimized ATS Analysis Toolkit"""

    def __init__(self, factory):
        super().__init__(factory)
        self.top_n_keywords = 30
        self.industry_keywords = self._load_industry_keywords()
        self.required_sections = ["experience", "education", "skills"]


    def init_app(self, app: Flask):
        super().init_app(app=app)


    # ─── Public API ───────────────────────────────────────────────────────────

    @error_handler
    async def handle_ats_match(self, request: Request) -> Dict:
        """Endpoint: upload resume + job description → match score"""
        uploaded = request.files.get("resume")
        job_desc = request.form.get("job_description", "")
        if not uploaded:
            raise ValueError("Resume file required")

        text = await self.extract_text(uploaded)
        resume_kw = await self.extract_keywords(text)
        job_kw = await self.extract_keywords(job_desc)
        return await self.calculate_match_score(resume_kw, job_kw)

    async def generate_cover_letter(
        self,
        job: Job,
        cv: JobSeekerCV,
        use_ai: bool = False,
        ai_config: Optional[dict] = None
    ) -> str:
        """Generate a cover letter, optionally via GPT/Deepseek."""
        if use_ai and ai_config:
            try:
                return await self._generate_ai_cover_letter(job, cv, ai_config)
            except Exception:
                self.logger.warning("AI cover letter failed, falling back")
        return self._generate_basic_cover_letter(job, cv)

    async def recommend_salary(
        self, job: Job, use_ai: bool = False, ai_config: Optional[dict] = None
    ) -> dict:
        """Generate salary recommendation (config → posting → fallback)."""
        if use_ai and ai_config:
            try:
                return await self._generate_ai_salary(job, ai_config)
            except Exception:
                self.logger.warning("AI salary recommendation failed")
        return self._basic_salary_recommendation(job)

    # ─── Core Helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _load_industry_keywords() -> Dict[str, List[str]]:
        # TODO: pull from DB or file
        return {
            "technology": ["python", "aws", "docker", "kubernetes"],
            "business": ["project management", "budgeting", "strategic planning"],
            "common": ["communication", "team leadership", "problem solving"],
        }

    @staticmethod
    def _clean_text_sync(text: str) -> str:
        """Strip out punctuation, lower-case, collapse whitespace."""
        cleaned = CLEAN_TEXT_PATTERN.sub("", text).lower()
        return " ".join(cleaned.split())

    @error_handler
    async def clean_text(self, text: str) -> str:
        return self._clean_text_sync(text)

    @error_handler
    async def extract_keywords(self, text: str, top_n: Optional[int] = None, vectorizer_type: str = "count"):
        clean = self._clean_text_sync(text)
        n = top_n or self.top_n_keywords
        if vectorizer_type == "tfidf":
            vec = TfidfVectorizer(stop_words="english", max_features=n)
        else:
            vec = CountVectorizer(stop_words="english", max_features=n)
        try:
            mat = vec.fit_transform([clean])
            return vec.get_feature_names_out().tolist()
        finally:
            del vec

    @error_handler
    async def calculate_match_score(
        self, resume_keywords: List[str], job_keywords: List[str]
    ) -> Dict[str, object]:
        job_set = set(job_keywords[:100])
        res_set = set(resume_keywords[:100])
        matched = job_set & res_set
        score = round((len(matched) / len(job_set) * 100) if job_set else 0, 2)
        return {
            "score": score,
            "matched_keywords": sorted(matched),
            "missing_keywords": sorted(job_set - res_set),
        }

    # ─── Readability & Feedback ────────────────────────────────────────────────

    @staticmethod
    async def _calculate_readability(text: str) -> float:
        doc = _NLP(text)
        sentences = list(doc.sents)
        words = [t for t in doc if t.is_alpha]
        if not sentences or not words:
            return 0.0
        avg_sent = len(words) / len(sentences)
        avg_word = sum(len(t.text) for t in words) / len(words)
        # simplified Flesch: 100 − (SentenceLen + 3×WordLen)
        return max(0.0, min(100.0, 100 - (avg_sent + 3 * avg_word)))

    @staticmethod
    async def _analyze_action_verbs(text: str) -> Dict[str, object]:
        doc = _NLP(text.lower())
        found = [tok.lemma_ for tok in doc if tok.lemma_ in ACTION_VERBS]
        total = len(list(doc))
        ratio = len(found) / total if total else 0.0
        return {
            "count": len(found),
            "score": ratio,
            "suggestions": list(ACTION_VERBS - set(found))[:3],
        }

    @staticmethod
    def _analyze_sections(cv: JobSeekerCV) -> dict[str, bool]:
        return {
            "experience": bool(cv.experience),
            "education": bool(cv.education),
            "skills": bool(cv.skills),
            "certifications": bool(cv.certifications),
            "languages": bool(cv.languages),
        }

    @staticmethod
    def _generate_human_readable_feedback(match_result: dict, sections: dict, quality: dict) -> str:
        fb = []
        if match_result["score"] < 50:
            fb.append("Your CV is missing many industry-standard keywords.")
        for sec in ("experience", "education", "certifications", "languages"):
            if not sections.get(sec):
                fb.append(f"Add {sec.title()} section.")
        if quality.get("verb_ratio", 0) < 0.2:
            fb.append("Use more action verbs.")
        return " ".join(fb) or "Looking good! Keep these suggestions in mind."

    async def generate_industry_ats_report(self, cv: JobSeekerCV) -> dict:
        """
        ATS Analysis for Internal Resumes
        Industry keyword–based ATS analysis.
        
        """
        text = " ".join([
            cv.professional_title or "",
            cv.summary or "",
            *cv.skills,
            *[e.description for e in cv.experience],
        ])
        kws = await self.extract_keywords(text, top_n=30)
        industry = [w for w in self.industry_keywords.get("common", []) + kws]
        match = await self.calculate_match_score(kws, industry)
        secs = self._analyze_sections(cv)
        quality = await self._analyze_action_verbs(text)
        feedback = self._generate_human_readable_feedback(match, secs, quality)
        return {
            "score": match["score"],
            "matched_keywords": match["matched_keywords"],
            "missing_keywords": match["missing_keywords"],
            "section_completeness": secs,
            "quality_metrics": quality,
            "feedback": feedback,
        }

    @error_handler
    async def get_resume_quality_insights(self, resume_text: str) -> dict:
        """
            This is for uploaded CV
        Generate resume quality metrics (readability, verb usage, section checks).
        
        """
        readability = await self._calculate_readability(resume_text)
        verb_analysis = await self._analyze_action_verbs(resume_text)
        doc = _NLP(resume_text)
        section_check = {
            "has_experience": any(token.lemma_ == "experience" for token in doc),
            "has_education": any(token.lemma_ == "education" for token in doc),
        }
        return {
            "readability_score": readability,
            "action_verbs": verb_analysis,
            "section_check": section_check,
            "suggestions": [
                "Use bullet points for achievements",
                "Quantify results with metrics",
            ]  # AI-generated
        }


    # ─── File/Text Extraction ──────────────────────────────────────────────────

    async def extract_text(self, uploaded_file) -> str:
        ext = os.path.splitext(uploaded_file.filename)[1].lower()
        if ext == ".pdf":
            return await self._stream_pdf_text(uploaded_file)
        if ext in (".docx", ".doc"):
            return docx2txt.process(uploaded_file)
        return uploaded_file.read().decode("utf-8", errors="ignore")

    @staticmethod
    async def _stream_pdf_text(file_stream) -> str:
        text = []
        with fitz.open(stream=file_stream.read(), filetype="pdf") as doc:
            for page in doc:
                text.append(page.get_text())
        return "\n".join(text)

    # ─── AI‑Driven Cover & Salary (GPT / Deepseek) ──────────────────────────────

    @staticmethod
    async def _generate_basic_cover_letter(job: Job, cv: JobSeekerCV) -> str:
        """Simple template fallback."""
        return (
            f"Dear Hiring Manager,\n\n"
            f"I’m excited to apply for {job.title} at {job.company}.\n"
            f"My background in {', '.join(cv.skills[:3])} makes me a strong fit...\n\n"
            f"Sincerely,\n"
            f"{cv.first_name} {cv.last_name}"
        )

    async def _generate_ai_cover_letter(
        self, job: Job, cv: JobSeekerCV, config: dict
    ) -> str:
        prompt = self._create_ai_professional_cover_letter_prompt(job, cv)
        response = await self._call_ai_api(
            prompt=prompt,
            api_key=config.get("api_key"),
            model=config.get("model", "gpt-4"),
        )
        return "\n".join(line.strip() for line in response.splitlines() if line.strip())

    @staticmethod
    def _create_ai_professional_cover_letter_prompt(
            job: Job, cv: JobSeekerCV
    ) -> str:
        return (
            f"Write a concise cover letter for {job.title} at {job.company}.\n"
            f"Key skills: {', '.join(job.required_skills[:5])}\n"
            f"Applicant: {cv.first_name} {cv.last_name}, expertise in {', '.join(cv.skills[:5])}."
        )

    @staticmethod
    async def _call_ai_api(prompt: str, api_key: str, model: str = "deepseek-chat") -> str:
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a career advisor."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 800,
        }
        async with aiohttp.ClientSession() as session:
            resp = await session.post(url, json=payload, headers=headers, timeout=10)
            resp.raise_for_status()
            data = await resp.json()
        return data["choices"][0]["message"]["content"].strip()

    async def _generate_ai_salary(self, job: Job, config: dict) -> dict:
        prompt = (
            f"Suggest a salary range for {job.title} in {job.location} "
            f"with skills {', '.join(job.required_skills[:3])}."
        )
        response = await self._call_ai_api(
            prompt=prompt, api_key=config.get("api_key"), model=config.get("model", "gpt-4")
        )
        # Extract JSON blob
        match = re.search(r"\{.*\}", response, re.DOTALL)
        if not match:
            raise ValueError("AI salary response malformed")
        data = json.loads(match.group())
        return {
            "range": [float(data["range"][0]), float(data["range"][1])],
            "basis": data.get("basis", ""),
            "currency": data.get("currency", "ZAR"),
            "confidence": data.get("confidence", 80),
            "source": "AI",
        }

    def _basic_salary_recommendation(self, job: Job) -> dict:
        # 1) config-driven override
        if job.category:
            key = f"salary_range:{job.category.lower()}"
            with self.get_session() as s:
                cfg = s.query(ConfigurationORM).filter_by(type=key).first()
            if cfg:
                rng = ConfigurationORM._cast_value(cfg.value, cfg.data_type)
                if isinstance(rng, list) and len(rng) == 2:
                    return {"range": [*rng], "basis": "Config", "currency": "ZAR", "confidence": 95}
        # 2) from posting
        if job.salary and "," in job.salary:
            try:
                lo, hi = [float(x.replace("$", "").replace(",", "").strip()) for x in job.salary.split(",")]
                return {"range": [lo, hi], "basis": "Posting", "currency": "USD", "confidence": 85}
            except Exception:
                self.logger.warning("Failed to parse job.salary")
        # 3) experience fallback
        levels = {"entry": (40000, 60000), "mid": (60000, 90000), "senior": (90000, 130000)}
        lvl = "mid"
        desc = (job.description or "").lower()
        if "senior" in desc:
            lvl = "senior"
        elif "junior" in desc:
            lvl = "entry"
        lo, hi = levels[lvl]
        return {"range": [lo, hi], "basis": "Fallback", "currency": "ZAR", "confidence": 65}

    # ─── Bulk helpers ─────────────────────────────────────────────────────────

    async def _generate_single_report(
        self, job_id: str, desc: str, cv: JobSeekerCV
    ) -> ATSReport:
        """Single‐CV ATSReport for a job."""
        kws = await self.extract_keywords(self._combine_cv_text(cv))
        self.industry_keywords = self._load_industry_keywords()  # reset per job
        match = await self.calculate_match_score(kws, kws + self._flatten_vk())
        feedback = await self._generate_human_readable_feedback(
            match, self._analyze_sections(cv), await self._analyze_action_verbs(self._combine_cv_text(cv))
        )
        return ATSReport(
            ats_report_id=str(uuid.uuid4()),
            job_id=job_id,
            cv_id=cv.cv_id,
            score=match["score"],
            matched_keywords=match["matched_keywords"],
            missing_keywords=match["missing_keywords"],
            feedback=feedback,
            created_at=datetime.now(timezone.utc)
        )

    async def generate_cvs_job_description_ats_report(
        self, job_id: str, desc: str, cvs: List[JobSeekerCV]
    ) -> ATSReport:
        """Pick the CV with the best score."""
        best = None
        best_score = -1
        for cv in cvs:
            rpt = await self._generate_single_report(job_id, desc, cv)
            if rpt.score > best_score:
                best_score, best = rpt.score, rpt
        return best or ATSReport(
            ats_report_id=str(uuid.uuid4()),
            job_id=job_id, cv_id="", score=0.0,
            matched_keywords=[], missing_keywords=[], feedback="", created_at=datetime.now(timezone.utc)
        )

    # ─── Text assembly ────────────────────────────────────────────────────────

    @staticmethod
    def _combine_cv_text(cv: JobSeekerCV) -> str:
        parts = [
            cv.professional_title or "",
            cv.summary or "",
            " ".join(cv.skills or []),
            " ".join(
                f"{e.title or ''} {e.company_name or ''} {e.description or ''} {e.location or ''}"
                for e in cv.experience or []
            ),
            " ".join(
                f"{edu.degree or ''} {edu.field_of_study or ''} {edu.institution_name or ''} {edu.description or ''}"
                for edu in cv.education or []
            ),
            " ".join(cert.name for cert in getattr(cv, "certifications", []) or []),
            " ".join(lang for lang in getattr(cv, "languages", []) or []),
            " ".join(proj.description for proj in getattr(cv, "projects", []) or []),
        ]
        return " ".join(filter(None, parts))
