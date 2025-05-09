import os
import re
import tempfile
from typing import Dict, List, Optional
import docx2txt
import fitz  # PyMuPDF
import spacy
from flask import Request, Flask
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer

from src.controllers.resume_controller import ResumeController
from src.database.models.resume import JobSeekerCV
from src.controllers.controller import Controllers, error_handler

# CPU-optimized NLP model
nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])
CLEAN_TEXT_PATTERN = re.compile(r'[^a-zA-Z0-9\+#\.\s]')
ACTION_VERBS = {"managed", "developed", "led", "created", "implemented"}


class ATSToolController(Controllers):
    """CPU-optimized ATS Analysis Toolkit"""

    def __init__(self):
        super().__init__()
        self.top_n_keywords = 30
        self._vectorizer_cache = {}
        self.nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])
        self.industry_keywords = self._load_industry_keywords()
        self.required_sections = ['experience', 'education', 'skills']
        self.resume_controller: ResumeController | None = None

    def init_app(self, app: Flask, resume: ResumeController):
        super().init_app(app=app)
        self.resume_controller = resume


    # CV Specifc ATS Checker
    def _load_industry_keywords(self):
        """Load industry-standard keywords from file or database"""
        # Example implementation - replace with actual data source
        return {
            'technology': ['python', 'aws', 'docker', 'kubernetes'],
            'business': ['project management', 'budgeting', 'strategic planning'],
            'common': ['communication', 'team leadership', 'problem solving']
        }

    async def generate_ats_report(self, cv: JobSeekerCV) -> dict:
        """Generate comprehensive ATS analysis report"""
        try:
            # Extract combined keywords from multiple sections
            combined_text = self._combine_cv_text(cv)
            cv_keywords = await self.extract_keywords(combined_text, top_n=50)

            # Get keyword matches
            industry_keywords = self._flatten_keywords()
            match_result = await self.calculate_match_score(cv_keywords, industry_keywords)

            # Calculate section completeness
            section_completeness = self._analyze_sections(cv)

            # Generate quality insights
            quality_metrics = await self.get_resume_quality_insights(combined_text)

            # Generate human-readable feedback
            feedback = self._generate_feedback(match_result, section_completeness, quality_metrics)

            return {
                'score': match_result['score'],
                'matched_keywords': match_result['matched_keywords'],
                'missing_keywords': match_result['missing_keywords'],
                'section_completeness': section_completeness,
                'quality_metrics': quality_metrics,
                'feedback': feedback
            }

        except Exception as e:
            return {
                'score': 0,
                'feedback': f"Error generating report: {str(e)}",
                'error': True
            }

    async def partial_ats_check(self, cv: JobSeekerCV) -> dict:
        """Quick ATS check for partial/incomplete CVs"""
        try:
            summary_keywords = await self.extract_keywords(cv.summary or "", top_n=15)
            industry_keywords = self._flatten_keywords()
            match_result = await self.calculate_match_score(summary_keywords, industry_keywords[:50])

            return {
                'score': match_result['score'],
                'matched_keywords': match_result['matched_keywords'],
                'missing_keywords': match_result['missing_keywords'][:5],
                'feedback': "Partial analysis based on summary only"
            }
        except Exception:
            return {'score': 0, 'feedback': "Quick analysis failed"}

    async def queue_ats_analysis(self, cv_id: str):
        """Simulated async analysis queue"""
        # In production, this would add to a task queue
        cv = await self.resume_controller.get_cv_by_id(cv_id)
        report = await self.generate_ats_report(cv)
        self.cache_report(cv_id, report)

    def cache_report(self, cv_id: str, report: dict):
        """Simple in-memory cache (replace with Redis/Memcached)"""
        if not hasattr(self, '_report_cache'):
            self._report_cache = {}
        self._report_cache[cv_id] = report

    def _combine_cv_text(self, cv: JobSeekerCV) -> str:
        """Combine relevant CV sections for analysis"""
        sections = [
            cv.professional_title or "",
            cv.summary or "",
            ' '.join(cv.skills),
            ' '.join([exp.description for exp in cv.experience]),
            ' '.join([edu.field_of_study for edu in cv.education])
        ]
        return ' '.join(sections)

    @staticmethod
    def _analyze_sections(cv: JobSeekerCV) -> dict:
        """Check for presence of critical sections"""
        return {
            'experience': bool(cv.experience),
            'education': bool(cv.education),
            'skills': bool(cv.skills),
            'certifications': bool(cv.certifications)
        }

    def _flatten_keywords(self) -> list:
        """Combine all industry keywords"""
        return [
            kw for category in self.industry_keywords.values()
            for kw in category
        ]

    @staticmethod
    def _generate_feedback(match_result, sections, quality) -> str:
        """Generate human-readable feedback"""
        feedback = []

        if match_result['score'] < 50:
            feedback.append("Your CV is missing many industry-standard keywords.")
        if not sections['experience']:
            feedback.append("Add work experience section.")
        if quality['verb_ratio'] < 20:
            feedback.append("Use more action verbs in descriptions.")

        return ' '.join(feedback) or "Looking good! Keep these suggestions in mind for future updates."

    #     END CV Specific ATS Checker

    @error_handler
    async def clean_text(self, text: str) -> str:
        """Optimized text cleaning for CPU"""
        text = CLEAN_TEXT_PATTERN.sub('', text).lower()
        return ' '.join(text.split())

    @error_handler
    async def extract_keywords(self, text: str, top_n: Optional[int] = None,
                               vectorizer_type: str = "count") -> list[str]:
        """Memory-efficient keyword extraction"""
        clean_text = await self.clean_text(text)
        top_n = top_n or self.top_n_keywords

        if vectorizer_type == "tfidf":
            vectorizer = TfidfVectorizer(stop_words='english', max_features=top_n)
        else:
            vectorizer = CountVectorizer(stop_words='english', max_features=top_n)

        try:
            matrix = vectorizer.fit_transform([clean_text])
            return vectorizer.get_feature_names_out().tolist()
        finally:
            del vectorizer  # Explicit cleanup

    @error_handler
    async def categorize_keywords(self, text: str) -> Dict[str, List[str]]:
        """CPU-optimized keyword categorization"""
        doc = self.nlp(text)
        categories = {
            "technical_skills": [],
            "action_verbs": [],
            "tools": [],
            "certifications": []
        }

        # Efficient pattern matching
        for token in doc:
            if token.pos_ == "VERB" and token.lemma_ in ACTION_VERBS:
                categories["action_verbs"].append(token.lemma_)
            elif token.pos_ == "NOUN" and token.is_alpha:
                categories["technical_skills"].append(token.text)

        # Simple pattern matching for certifications
        cert_patterns = [r'\bAWS\b', r'\bPMP\b', r'\bCCNA\b']
        categories["certifications"] = [
            match.group() for pattern in cert_patterns
            for match in re.finditer(pattern, text, re.IGNORECASE)
        ]

        return categories

    @error_handler
    async def extract_text(self, uploaded_file) -> str:
        """Memory-safe text extraction"""
        file_ext = os.path.splitext(uploaded_file.filename)[-1].lower()

        if file_ext == ".pdf":
            return await self._stream_pdf_text(uploaded_file)
        if file_ext in (".docx", ".doc"):
            return docx2txt.process(uploaded_file)
        return uploaded_file.read().decode('utf-8', errors='ignore')

    @staticmethod
    async def _stream_pdf_text(file_stream) -> str:
        """Memory-efficient PDF text extraction"""
        text = []
        with fitz.open(stream=file_stream.read(), filetype="pdf") as doc:
            for page in doc:
                text.append(page.get_text())
        return "\n".join(text)

    @error_handler
    async def calculate_match_score(self, resume_keywords: List[str],
                                    job_keywords: List[str]) -> Dict[str, float]:
        """Optimized matching algorithm"""
        job_set = set(job_keywords[:100])  # Limit for performance
        resume_set = set(resume_keywords[:100])

        matched = job_set & resume_set
        score = (len(matched) / len(job_set)) * 100 if job_set else 0

        return {
            "score": round(score, 2),
            "matched_keywords": sorted(matched),
            "missing_keywords": sorted(job_set - resume_set)
        }

    @error_handler
    async def get_resume_quality_insights(self, text: str) -> Dict:
        """Optimized quality metrics"""
        words = text.split()
        action_verbs = [word for word in words if word.lower() in ACTION_VERBS]

        return {
            "word_count": len(words),
            "action_verbs": action_verbs,
            "verb_ratio": round(len(action_verbs) / len(words) * 100, 2) if words else 0
        }

    @error_handler
    async def handle_ats_match(self, request: Request) -> Dict:
        """Optimized main endpoint"""
        uploaded_file = request.files.get("resume")
        job_desc = request.form.get("job_description", "")

        if not uploaded_file:
            raise ValueError("Resume file required")

        resume_text = await self.extract_text(uploaded_file)
        resume_keywords = await self.extract_keywords(resume_text)
        job_keywords = await self.extract_keywords(job_desc)

        return await self.calculate_match_score(resume_keywords, job_keywords)

