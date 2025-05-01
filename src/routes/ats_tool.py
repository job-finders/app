from flask import Blueprint, request, render_template
from src.main import ats_controller  # Assuming ats_controller is an instance of ATSToolController

ats_tool_route = Blueprint('ats', __name__)


@ats_tool_route.route("/ats-match", methods=["POST"])
def ats_match():
    context = ats_controller.handle_ats_match(request)
    return render_template("ats/compare.html", **context)


@ats_tool_route.route("/resume-quality", methods=["POST"])
def resume_quality():
    uploaded_file = request.files.get("resume")
    if not uploaded_file:
        return render_template("ats/resume_quality.html", error="No file uploaded.")

    resume_text = ats_controller.extract_text(uploaded_file)
    context = ats_controller.get_resume_quality_insights(resume_text)
    return render_template("ats/resume_quality.html", **context)


@ats_tool_route.route("/keyword-extract", methods=["POST"])
def keyword_extract():
    uploaded_file = request.files.get("resume")
    if not uploaded_file:
        return render_template("ats/keywords.html", error="Please upload a resume.")

    resume_text = ats_controller.extract_text(uploaded_file)
    context = {
        "keywords": ats_controller.extract_keywords(resume_text),
        "weighted_keywords": ats_controller.extract_weighted_keywords(resume_text)
    }
    return render_template("ats/keywords.html", **context)


@ats_tool_route.route("/categorize-keywords", methods=["POST"])
def categorize_keywords():
    uploaded_file = request.files.get("resume")
    if not uploaded_file:
        return render_template("ats/categories.html", error="Please upload a resume.")

    resume_text = ats_controller.extract_text(uploaded_file)
    context = ats_controller.categorize_keywords(resume_text)
    return render_template("ats/categories.html", **context)


@ats_tool_route.route("/ats-tools", methods=["GET", "POST"])
def ats_tools():
    if request.method == "GET":
        return render_template("ats/tools_results_inline.html")

    uploaded_file = request.files.get("resume")
    job_desc = request.form.get("job_description")

    if not uploaded_file or not job_desc:
        return render_template("ats/tools_results_inline.html", error="Please upload a resume and paste job description.")

    resume_text = ats_controller.extract_text(uploaded_file)

    context = {
        "match": ats_controller.handle_ats_match_text(resume_text, job_desc),
        "quality": ats_controller.get_resume_quality_insights(resume_text),
        "keywords": ats_controller.extract_keywords(resume_text),
        "weighted_keywords": ats_controller.extract_weighted_keywords(resume_text),
        "categorized": ats_controller.categorize_keywords(resume_text)
    }

    return render_template("ats/tools_results_inline.html", **context)
