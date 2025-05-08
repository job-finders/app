import os
import re
import tempfile
from typing import Dict, List, Optional

import docx2txt
import fitz  # PyMuPDF
import spacy
from flask import Request, Flask
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer

from src.controllers.controller import Controllers, error_handler

# Pre-load NLP model and compile regex patterns
nlp = spacy.load("en_core_web_sm")
CLEAN_TEXT_PATTERN = re.compile(r'[^a-zA-Z\s]')
ACTION_VERBS = {"managed", "developed", "led", "created", "implemented"}


class ATSToolController(Controllers):
    """ATS (Applicant Tracking System) Analysis Toolkit

    Provides functionality for resume parsing, keyword extraction, and job description matching.

    Attributes:
        top_n_keywords: Default number of keywords to extract (default: 30)
    """

    def __init__(self):
        super().__init__()
        self.top_n_keywords = 30
        self._vectorizer_cache = {}  # For potential vectorizer reuse

    def init_app(self, app: Flask):
        super().init_app(app=app)

    @error_handler
    async def clean_text(self, text: str) -> str:
        """Normalize text for processing

        Args:
            text: Raw input text

        Returns:
            Lowercase text with only alphabetical characters and whitespace
        """
        return CLEAN_TEXT_PATTERN.sub('', text).lower()

    @error_handler
    async def extract_keywords(
            self,
            text: str,
            top_n: Optional[int] = None,
            vectorizer_type: str = "count"
    ) -> List[str]:
        """Extract keywords from text using different vectorization methods

        Args:
            text: Input text to analyze
            top_n: Number of top keywords to return
            vectorizer_type: 'count' for frequency-based, 'tfidf' for weighted

        Returns:
            List of extracted keywords ordered by significance
        """
        clean_text = await self.clean_text(text)
        top_n = top_n or self.top_n_keywords

        if vectorizer_type == "tfidf":
            vectorizer = TfidfVectorizer(stop_words='english')
            matrix = vectorizer.fit_transform([clean_text])
            features = vectorizer.get_feature_names_out()
            scores = matrix.toarray()[0]
            return [kw for kw, _ in sorted(zip(features, scores),
                                           key=lambda x: x[1], reverse=True)[:top_n]]

        # Default to CountVectorizer
        vectorizer = CountVectorizer(
            stop_words='english',
            max_features=top_n
        )
        matrix = vectorizer.fit_transform([clean_text])
        return vectorizer.get_feature_names_out().tolist()

    @error_handler
    async def extract_weighted_keywords(
            self,
            text: str,
            top_n: Optional[int] = None
    ) -> Dict[str, float]:
        """Extract keywords with weights using TF-IDF

        Args:
            text: Resume text
            top_n: Number of top weighted keywords to return

        Returns:
            Dictionary of keywords and their weights sorted by importance
        """
        clean_text = await self.clean_text(text)
        top_n = top_n or self.top_n_keywords

        vectorizer = TfidfVectorizer(stop_words='english')
        matrix = vectorizer.fit_transform([clean_text])
        features = vectorizer.get_feature_names_out()
        scores = matrix.toarray()[0]

        weighted_keywords = {kw: round(score, 4) for kw, score in zip(features, scores)}
        sorted_keywords = dict(sorted(weighted_keywords.items(), key=lambda x: x[1], reverse=True)[:top_n])
        return sorted_keywords

    @error_handler
    async def categorize_keywords(self, text: str) -> Dict[str, List[str]]:
        """Categorize text elements using NLP analysis

        Args:
            text: Input text to categorize

        Returns:
            Dictionary mapping categories to relevant tokens:
            {
                "technical_skills": [],
                "soft_skills": [],
                "verbs": [],
                "nouns": []
            }
        """
        doc = nlp(text)
        categories = {
            "technical_skills": [],
            "soft_skills": [],
            "verbs": [],
            "nouns": [],
        }

        for token in doc:
            if token.pos_ == "VERB":
                categories["verbs"].append(token.lemma_)
            elif token.pos_ == "NOUN":
                categories["nouns"].append(token.lemma_)
            if token.ent_type_ in ("SKILL", "ORG", "PRODUCT"):
                categories["technical_skills"].append(token.text)
            elif token.ent_type_ == "PERSON":
                categories["soft_skills"].append(token.text)

        return categories

    @error_handler
    async def extract_text(self, uploaded_file) -> str:
        """Extract text from various file formats

        Args:
            uploaded_file: File object from Flask request

        Returns:
            Extracted text content as a single string

        Raises:
            ValueError: For unsupported file types
        """
        file_ext = os.path.splitext(uploaded_file.filename)[-1].lower()

        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
            uploaded_file.save(tmp.name)
            try:
                if file_ext == ".pdf":
                    return await self._extract_pdf_text(tmp.name)
                if file_ext in (".docx", ".doc"):
                    return docx2txt.process(tmp.name)
                return self._read_text_file(tmp.name)
            finally:
                os.unlink(tmp.name)  # Clean up temp file

    @staticmethod
    async def _extract_pdf_text(path: str) -> str:
        """Extract text content from PDF files"""
        text = []
        with fitz.open(path) as doc:
            for page in doc:
                text.append(page.get_text())
        return "\n".join(text)

    @staticmethod
    def _read_text_file(path: str) -> str:
        """Read text from plain text files"""
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    @error_handler
    async def calculate_match_score(
            self,
            resume_keywords: List[str],
            job_keywords: List[str]
    ) -> Dict[str, float]:
        """Calculate match score between resume and job description

        Args:
            resume_keywords: Keywords from resume
            job_keywords: Keywords from job description

        Returns:
            Dictionary with match metrics:
            {
                "score": percentage match,
                "matched_keywords": [],
                "missing_keywords": []
            }
        """
        job_set = set(job_keywords)
        resume_set = set(resume_keywords)

        matched = job_set & resume_set
        missing = job_set - resume_set

        score = (len(matched) / len(job_set)) * 100 if job_set else 0.0

        return {
            "score": round(score, 2),
            "matched_keywords": sorted(matched),
            "missing_keywords": sorted(missing)
        }

    @error_handler
    async def get_resume_quality_insights(self, text: str) -> Dict:
        """Analyze resume text quality metrics

        Args:
            text: Resume text content

        Returns:
            Quality metrics dictionary:
            {
                "word_count": int,
                "used_action_verbs": list,
                "action_verb_ratio": float
            }
        """
        words = text.split()
        used_verbs = [word for word in words if word.lower() in ACTION_VERBS]
        total_words = len(words)

        return {
            "word_count": total_words,
            "used_action_verbs": used_verbs,
            "action_verb_ratio":
                round((len(used_verbs) / total_words * 100), 2) if total_words else 0
        }

    @error_handler
    async def handle_ats_match(self, request: Request) -> Dict:
        """Main endpoint for ATS match analysis

        Args:
            request: Flask request object with files/form data

        Returns:
            Match analysis results

        Raises:
            ValueError: If missing required files/data
        """
        if not (uploaded_file := request.files.get("resume")):
            raise ValueError("Resume file is required")
        if not (job_desc := request.form.get("job_description")):
            raise ValueError("Job description is required")

        resume_text = await self.extract_text(uploaded_file)
        resume_keywords = await self.extract_keywords(resume_text)
        job_keywords = await self.extract_keywords(job_desc)

        analysis = await self.calculate_match_score(resume_keywords, job_keywords)

        return {
            "score": analysis["score"],
            "matched": analysis["matched_keywords"],
            "missing": analysis["missing_keywords"]
        }