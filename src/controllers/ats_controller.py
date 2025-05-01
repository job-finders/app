from flask import Flask
from src.controllers.controller import Controllers
import os
import tempfile
import docx2txt
import fitz  # PyMuPDF for PDF
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
import re
import spacy

nlp = spacy.load("en_core_web_sm")


class ATSToolController(Controllers):
    def __init__(self):
        self.top_n_keywords = 30

    def init_app(self, app: Flask):
        # Route setup can be done here
        pass

    def clean_text(self, text: str) -> str:
        return re.sub(r'[^a-zA-Z\s]', '', text).lower()

    def extract_keywords(self, text: str, top_n: int = None) -> list:
        text = self.clean_text(text)
        vectorizer = CountVectorizer(stop_words='english', max_features=top_n or self.top_n_keywords)
        X = vectorizer.fit_transform([text])
        return vectorizer.get_feature_names_out().tolist()

    def extract_weighted_keywords(self, text: str, top_n: int = None) -> list:
        """Uses TF-IDF for more intelligent keyword ranking"""
        text = self.clean_text(text)
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = vectorizer.fit_transform([text])
        scores = zip(vectorizer.get_feature_names_out(), tfidf_matrix.toarray()[0])
        sorted_scores = sorted(scores, key=lambda x: x[1], reverse=True)
        return [kw for kw, score in sorted_scores[:(top_n or self.top_n_keywords)]]

    def categorize_keywords(self, text: str) -> dict:
        """Uses spaCy to identify parts of speech and categorize"""
        doc = nlp(text)
        categories = {
            "technical_skills": [],
            "soft_skills": [],
            "verbs": [],
            "nouns": [],
        }
        for token in doc:
            if token.pos_ == "VERB":
                categories["verbs"].append(token.text)
            elif token.pos_ == "NOUN":
                categories["nouns"].append(token.text)
            elif token.ent_type_ in ("SKILL", "ORG", "PRODUCT"):
                categories["technical_skills"].append(token.text)
            elif token.ent_type_ == "PERSON":
                categories["soft_skills"].append(token.text)
        return categories

    def extract_text(self, uploaded_file):
        file_ext = os.path.splitext(uploaded_file.filename)[-1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
            uploaded_file.save(tmp.name)
            tmp_path = tmp.name
        if file_ext == ".pdf":
            return self.extract_text_from_pdf(tmp_path)
        elif file_ext in [".docx", ".doc"]:
            return docx2txt.process(tmp_path)
        else:
            with open(tmp_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

    def extract_text_from_pdf(self, path: str) -> str:
        text = ""
        with fitz.open(path) as doc:
            for page in doc:
                text += page.get_text()
        return text

    def calculate_match_score(self, resume_keywords: list, job_keywords: list) -> dict:
        matched = set(resume_keywords) & set(job_keywords)
        missing = set(job_keywords) - set(resume_keywords)
        score = round(len(matched) / len(job_keywords) * 100, 2) if job_keywords else 0
        return {
            "score": score,
            "matched_keywords": list(matched),
            "missing_keywords": list(missing),
        }

    def get_resume_quality_insights(self, text: str) -> dict:
        word_count = len(text.split())
        action_verbs = ["managed", "developed", "led", "created", "implemented"]
        used_action_verbs = [word for word in text.split() if word.lower() in action_verbs]
        return {
            "word_count": word_count,
            "used_action_verbs": used_action_verbs,
            "action_verb_ratio": round(len(used_action_verbs) / word_count * 100, 2) if word_count else 0
        }
