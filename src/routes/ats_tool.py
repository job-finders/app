from flask import Flask, Blueprint, request, render_template
import os
import tempfile
import docx2txt
import fitz  # PyMuPDF for PDF

from sklearn.feature_extraction.text import CountVectorizer

import re

def clean_text(text):
    # Remove special characters and lower the text
    return re.sub(r'[^a-zA-Z\s]', '', text).lower()

def extract_keywords(text, top_n=30):
    text = clean_text(text)
    vectorizer = CountVectorizer(stop_words='english', max_features=top_n)
    X = vectorizer.fit_transform([text])
    return vectorizer.get_feature_names_out().tolist()


def extract_text(uploaded_file):
    file_ext = os.path.splitext(uploaded_file.filename)[-1].lower()

    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
        uploaded_file.save(tmp.name)
        tmp_path = tmp.name

    if file_ext == ".pdf":
        return extract_text_from_pdf(tmp_path)
    elif file_ext in [".docx", ".doc"]:
        return docx2txt.process(tmp_path)
    else:
        with open(tmp_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()


def extract_text_from_pdf(path):
    text = ""
    with fitz.open(path) as doc:
        for page in doc:
            text += page.get_text()
    return text



ats_tool_route = Blueprint('ats', __name__)


@ats_tool_route.route("/ats-match", methods=["POST"])
def ats_match():

    resume_text = extract_text(request.files["resume"])
    job_desc = request.form["job_description"]

    resume_keywords = extract_keywords(resume_text)
    job_keywords = extract_keywords(job_desc)

    matched = set(resume_keywords) & set(job_keywords)
    missing = set(job_keywords) - set(resume_keywords)

    score = round(len(matched) / len(job_keywords) * 100, 2)

    context = {'score': score, 'matched': matched, 'missing': missing}

    return render_template("ats/compare.html", score=score, matched=matched, missing=missing)
