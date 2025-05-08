from flask import Blueprint, request, render_template

from src.logger import init_logger
from src.main import ats_controller  # Assuming ats_controller is an instance of ATSToolController

ats_tool_route = Blueprint('ats', __name__)
ats_logger = init_logger("ats_tool")

@ats_tool_route.route("/ats-match", methods=["POST"])
async def ats_match():
    context = await ats_controller.handle_ats_match(request)
    return render_template("ats/compare.html", **context)


@ats_tool_route.route("/resume-quality", methods=["POST"])
async def resume_quality():
    uploaded_file = request.files.get("resume")
    if not uploaded_file:
        return render_template("ats/resume_quality.html", error="No file uploaded.")

    resume_text = await  ats_controller.extract_text(uploaded_file)
    context = await ats_controller.get_resume_quality_insights(resume_text)
    return render_template("ats/resume_quality.html", **context)


@ats_tool_route.route("/keyword-extract", methods=["POST"])
async def keyword_extract():
    uploaded_file = request.files.get("resume")
    if not uploaded_file:
        return render_template("ats/keywords.html", error="Please upload a resume.")

    resume_text = await ats_controller.extract_text(uploaded_file)
    context = {
        "keywords": await ats_controller.extract_keywords(resume_text),
        "weighted_keywords": await ats_controller.extract_weighted_keywords(resume_text)
    }
    return render_template("ats/keywords.html", **context)


@ats_tool_route.route("/categorize-keywords", methods=["POST"])
async def categorize_keywords():
    uploaded_file = request.files.get("resume")
    if not uploaded_file:
        return render_template("ats/categories.html", error="Please upload a resume.")

    resume_text = await ats_controller.extract_text(uploaded_file)
    context = await ats_controller.categorize_keywords(resume_text)
    return render_template("ats/categories.html", **context)


@ats_tool_route.route("/ats-tools", methods=["GET", "POST"])
async def ats_tools():
    if request.method == "GET":
        return render_template("ats/tools_results_inline.html")

    uploaded_file = request.files.get("resume")
    job_desc = request.form.get("job_description")

    if not uploaded_file or not job_desc:
        return render_template("ats/tools_results_inline.html", error="Please upload a resume and paste job description.")

    resume_text = await ats_controller.extract_text(uploaded_file)

    context = {
        "match": await ats_controller.handle_ats_match(resume_text, job_desc),
        "quality": await ats_controller.get_resume_quality_insights(resume_text),
        "keywords": await ats_controller.extract_keywords(resume_text),
        "weighted_keywords": await ats_controller.extract_weighted_keywords(resume_text),
        "categorized": await ats_controller.categorize_keywords(resume_text)
    }
    ats_logger.info(f"ATS TOOL : {context}")
    return render_template("ats/tools_results_inline.html", **context)
