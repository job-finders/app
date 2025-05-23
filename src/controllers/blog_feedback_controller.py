# /controllers/blog_feedback_controller.py
from flask import Blueprint, request, redirect, url_for, render_template
from src.database.models.blog_insight_models import BlogFeedback
from src.services.image_selector import get_suggested_images

blog_feedback_bp = Blueprint('blog_feedback', __name__)

@blog_feedback_bp.route("/blog-dashboard", methods=["GET"])
def dashboard():
    images = get_suggested_images()
    return render_template("blog_dashboard/index.html", suggested_images=images)

@blog_feedback_bp.route("/blog-feedback", methods=["POST"])
def submit_feedback():
    article_id = request.form["article_id"]
    feedback_score = int(request.form["feedback_score"])
    comments = request.form.get("comments")

    feedback = BlogFeedback(
        article_id=article_id,
        feedback_score=feedback_score,
        comments=comments
    )
    db_session.add(feedback)
    db_session.commit()
    return redirect(url_for("blog_feedback.dashboard"))
