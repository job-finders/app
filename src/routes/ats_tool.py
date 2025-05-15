from flask import Blueprint, request, render_template

from src.logger import init_logger
from src.main import ats_controller  # Assuming ats_controller is an instance of ATSToolController

ats_tool_route = Blueprint('ats', __name__)
ats_logger = init_logger("ats_tool")

@ats_tool_route.route("/ats-match", methods=["POST"])
@login_required
async def ats_match(user: User):
    """
    Perform ATS match scoring based on uploaded resume and provided job description.

    This endpoint accepts a POST request with multipart form-data containing a resume file
    and job description. It extracts the resume text, compares it with the job description, 
    and returns a compatibility score and breakdown.

    How it works:
        1. Extract the file and job description from the request.
        2. Use `ats_controller.handle_ats_match()` to compute the match.
        3. Render a results template with scoring details.

    Example usage:
        POST /ats-match
        FormData: { resume: <file>, job_description: <text> }
    """
    context = await ats_controller.handle_ats_match(current_user=user, request=request)
    return render_template("ats/compare.html", **context)


@ats_tool_route.route("/resume-quality", methods=["POST"])
@login_required
async def resume_quality(user: User):
    """
    Analyze the quality of an uploaded resume and return structured improvement insights.

    This route processes a single uploaded PDF/DOCX resume and evaluates its quality using
    multiple heuristic and semantic rules.

    How it works:
        1. Checks for a resume in the request files.
        2. Extracts raw text using the ATS controller.
        3. Calls `get_resume_quality_insights()` for scoring, formatting, etc.
        4. Renders a report with improvement advice.

    Example usage:
        POST /resume-quality
        FormData: { resume: <file> }
    """
    uploaded_file = request.files.get("resume")
    if not uploaded_file:
        return render_template("ats/resume_quality.html", error="No file uploaded.")
    resume_text = await ats_controller.extract_text(uploaded_file)
    context = await ats_controller.get_resume_quality_insights(resume_text)
    context.update(current_user=user)
    return render_template("ats/resume_quality.html", **context)


@ats_tool_route.route("/keyword-extract", methods=["POST"])
@login_required
async def keyword_extract(user: User):
    """
    Extract key and weighted keywords from a resume file.

    This endpoint processes an uploaded resume, identifies high-frequency and domain-relevant
    keywords, and returns a structured view of them.

    How it works:
        1. Resume is uploaded and extracted to text.
        2. Calls `extract_keywords()` and `extract_weighted_keywords()` from the ATS controller.
        3. Combines and returns both basic and weighted keyword structures.

    Example usage:
        POST /keyword-extract
        FormData: { resume: <file> }
    """
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
    """
    Categorize extracted resume keywords into logical groups (e.g., technical, soft skills).

    This endpoint enhances keyword understanding by grouping resume keywords into meaningful
    categories for better readability and ATS alignment.

    How it works:
        1. Resume is uploaded and converted to plain text.
        2. Keywords are categorized using ATS NLP techniques.
        3. Categories and sub-keywords are displayed in the template.

    Example usage:
        POST /categorize-keywords
        FormData: { resume: <file> }
    """
    uploaded_file = request.files.get("resume")
    if not uploaded_file:
        return render_template("ats/categories.html", error="Please upload a resume.")
    resume_text = await ats_controller.extract_text(uploaded_file)
    context = await ats_controller.categorize_keywords(resume_text)
    return render_template("ats/categories.html", **context)


@ats_tool_route.route("/ats-tools", methods=["GET", "POST"])
async def ats_tools():
    """
    Unified endpoint for multiple ATS tools including match scoring, quality check,
    keyword extraction, and categorization — all from a single resume upload.

    How it works:
        - GET: Renders the upload form and UI.
        - POST:
            1. Extracts resume and job description.
            2. Processes resume for ATS match, quality, keywords, and categorization.
            3. Logs and displays results inline.

    Example usage:
        GET /ats-tools
        POST /ats-tools
        FormData: { resume: <file>, job_description: <text> }
    """
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


@ats_tool_route.route("/summary-generator", methods=["POST"])
async def summary_generator():
    """
    Generates a professional resume summary from an uploaded resume.

    How it works:
        1. Uploads and extracts resume text.
        2. Passes resume to `generate_summary()` which builds a summary based on experience.
        3. Renders a preview of the generated summary.

    Example usage:
        POST /summary-generator
        FormData: { resume: <file> }
    """
    uploaded_file = request.files.get("resume")
    if not uploaded_file:
        return render_template("ats/summary.html", error="No file uploaded.")
    resume_text = await ats_controller.extract_text(uploaded_file)
    context = await ats_controller.generate_summary(resume_text)
    return render_template("ats/summary.html", **context)


@ats_tool_route.route("/top-skills", methods=["POST"])
async def top_skills():
    """
    Extracts and returns top skills from a resume.

    How it works:
        1. Uploads a resume file.
        2. Extracts resume text.
        3. Identifies dominant and relevant skillsets.

    Example usage:
        POST /top-skills
        FormData: { resume: <file> }
    """
    uploaded_file = request.files.get("resume")
    if not uploaded_file:
        return render_template("ats/top_skills.html", error="No file uploaded.")
    resume_text = await ats_controller.extract_text(uploaded_file)
    skills = await ats_controller.get_top_skills(resume_text)
    return render_template("ats/top_skills.html", skills=skills)


@ats_tool_route.route("/api/ats-score", methods=["POST"])
async def ats_score_api():
    """
    API endpoint that returns raw ATS score (non-HTML) based on resume and job description.

    How it works:
        1. Expects a resume file and job_description in form-data.
        2. Returns raw ATS match score JSON.

    Example usage:
        POST /api/ats-score
        FormData: { resume: <file>, job_description: <text> }
    """
    uploaded_file = request.files.get("resume")
    job_desc = request.form.get("job_description")
    if not uploaded_file or not job_desc:
        return {"error": "Missing data"}, 400
    resume_text = await ats_controller.extract_text(uploaded_file)
    score = await ats_controller.handle_ats_match(resume_text, job_desc)
    return score


@ats_tool_route.route("/api/ats-score-json", methods=["POST"])
async def ats_score_api_json():
    """
    Identical to `/api/ats-score`. Returns structured ATS score from resume and job description.

    Intended for JSON-consuming clients.

    Example usage:
        POST /api/ats-score-json
        FormData: { resume: <file>, job_description: <text> }
    """
    uploaded_file = request.files.get("resume")
    job_desc = request.form.get("job_description")
    if not uploaded_file or not job_desc:
        return {"error": "Missing data"}, 400
    resume_text = await ats_controller.extract_text(uploaded_file)
    score = await ats_controller.handle_ats_match(resume_text, job_desc)
    return score


@ats_tool_route.route("/parse-metadata", methods=["POST"])
async def parse_metadata():
    """
    Extracts metadata (e.g. name, email, phone) from uploaded resume.

    Example usage:
        POST /parse-metadata
        FormData: { resume: <file> }
    """
    uploaded_file = request.files.get("resume")
    if not uploaded_file:
        return render_template("ats/metadata.html", error="No file uploaded.")
    resume_text = await ats_controller.extract_text(uploaded_file)
    metadata = await ats_controller.extract_metadata(resume_text)
    return render_template("ats/metadata.html", metadata=metadata)


@ats_tool_route.route("/improvement-suggestions", methods=["POST"])
async def improvement_suggestions():
    """
    Provides improvement recommendations for a resume based on common ATS weaknesses.

    Example usage:
        POST /improvement-suggestions
        FormData: { resume: <file> }
    """
    uploaded_file = request.files.get("resume")
    if not uploaded_file:
        return render_template("ats/improvements.html", error="No file uploaded.")
    resume_text = await ats_controller.extract_text(uploaded_file)
    suggestions = await ats_controller.recommend_improvements(resume_text)
    return render_template("ats/improvements.html", suggestions=suggestions)
