# Standard Library
import uuid
from datetime import datetime, timezone, timedelta

# Flask & Third-Party
from flask import Blueprint, request, render_template, redirect, url_for, flash

# Authentication
from src.authentication import employer_login, require_billing_role
# Domain Models
from src.database.models import (
    Employer,
    User,
)
# Logger
from src.logger import init_logger
# Routes
from src.routes import flask_error_handler
# Services
# Utilities
from src.utils.route_helpers import get_controller

# Controllers

employer_route = Blueprint('employer', __name__, url_prefix='/dashboard/employer')
logger = init_logger("company_routes")


# Add these routes after your existing company routes

@employer_route.route("/employers/invite", methods=["POST"])
@flask_error_handler
@employer_login
@require_billing_role()
async def invite_employer(user: User):
    """Endpoint to invite a new team member to the company"""
    if user.role != "employer":
        flash("You must be an employer to perform this action", "danger")
        return redirect(url_for("company.employers_list"))

    company_controller = get_controller('company')
    employer_profile = await company_controller.get_employer_by_uid(user_id=user.uid)

    if not employer_profile or not employer_profile.is_admin:
        flash("Only company administrators can invite new team members", "danger")
        return redirect(url_for("company.employers_list"))

    form_data = request.get_json() if request.is_json else request.form
    full_name = form_data.get("full_name")
    email = form_data.get("email")
    role = form_data.get("role", "team_member")  # Default to team_member

    # Validate input
    if not full_name or not email:
        flash("Full name and email are required", "danger")
        return redirect(url_for("company.employers_list"))

    try:
        # Create employer record with pending status
        new_employer = Employer(
            user_uid=str(uuid.uuid4()),  # Temporary UID until user registers
            company_id=employer_profile.company_id,
            full_name=full_name,
            company_email=email,
            is_admin=(role == "admin"),
            is_verified=False
        )

        # Save employer record
        created_employer = await company_controller.register_employer(
            employer_data=new_employer
        )

        # Generate invitation token
        invitation_token = str(uuid.uuid4())
        await company_controller.create_employer_invitation(
            employer_id=created_employer.employer_id,
            token=invitation_token,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )

        # Send invitation email (pseudo-code)
        # send_invitation_email(email, full_name, invitation_token)

        flash(f"Invitation sent to {full_name} at {email}", "success")
    except Exception as e:
        logger.error(f"Error inviting employer: {str(e)}")
        flash("Failed to send invitation. Please try again.", "danger")

    return redirect(url_for("company.employers_list"))


@employer_route.route("/employers/<employer_id>/resend-invite", methods=["POST"])
@flask_error_handler
@employer_login
@require_billing_role()
async def resend_employer_invitation(user: User, employer_id: str):
    """Endpoint to resend an invitation to a team member"""
    if user.role != "employer":
        flash("You must be an employer to perform this action", "danger")
        return redirect(url_for("company.employers_list"))

    company_controller = get_controller('company')
    employer_profile = await company_controller.get_employer_by_uid(user_id=user.uid)

    if not employer_profile or not employer_profile.is_admin:
        flash("Only company administrators can resend invitations", "danger")
        return redirect(url_for("company.employers_list"))

    try:
        # Get employer to resend to
        target_employer = await company_controller.get_employer_by_id(employer_id)

        if not target_employer or target_employer.company_id != employer_profile.company_id:
            flash("Invalid employer specified", "danger")
            return redirect(url_for("company.employers_list"))

        if target_employer.is_verified:
            flash("This team member has already joined", "info")
            return redirect(url_for("company.employers_list"))

        # Generate new invitation token
        invitation_token = str(uuid.uuid4())
        await company_controller.create_employer_invitation(
            employer_id=target_employer.employer_id,
            token=invitation_token,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )

        # Send invitation email (pseudo-code)
        # send_invitation_email(
        #   target_employer.company_email, 
        #   target_employer.full_name, 
        #   invitation_token
        # )

        flash(f"Invitation resent to {target_employer.full_name}", "success")
    except Exception as e:
        logger.error(f"Error resending invitation: {str(e)}")
        flash("Failed to resend invitation. Please try again.", "danger")

    return redirect(url_for("company.employers_list"))


@employer_route.route("/employers/<employer_id>/remove", methods=["POST"])
@flask_error_handler
@employer_login
@require_billing_role()
async def remove_employer(user: User, employer_id: str):
    """Endpoint to remove a team member from the company"""
    if user.role != "employer":
        flash("You must be an employer to perform this action", "danger")
        return redirect(url_for("company.employers_list"))

    company_controller = get_controller('company')
    employer_profile = await company_controller.get_employer_by_uid(user_id=user.uid)

    if not employer_profile or not employer_profile.is_admin:
        flash("Only company administrators can remove team members", "danger")
        return redirect(url_for("company.employers_list"))

    # Cannot remove self
    if employer_profile.employer_id == employer_id:
        flash("You cannot remove yourself from the company", "danger")
        return redirect(url_for("company.employers_list"))

    try:
        # Get employer to remove
        target_employer = await company_controller.get_employer_by_id(employer_id)

        if not target_employer or target_employer.company_id != employer_profile.company_id:
            flash("Invalid employer specified", "danger")
            return redirect(url_for("company.employers_list"))

        # Deactivate employer
        await company_controller.deactivate_employer(employer_id)

        flash(f"{target_employer.full_name} has been removed from your company", "success")
    except Exception as e:
        logger.error(f"Error removing employer: {str(e)}")
        flash("Failed to remove team member. Please try again.", "danger")

    return redirect(url_for("company.employers_list"))


@employer_route.route("/employers/<employer_id>/update-role", methods=["POST"])
@flask_error_handler
@employer_login
@require_billing_role()
async def update_employer_role(user: User, employer_id: str):
    """Endpoint to update a team member's role (admin/regular)"""
    if user.role != "employer":
        flash("You must be an employer to perform this action", "danger")
        return redirect(url_for("company.employers_list"))

    company_controller = get_controller('company')
    employer_profile = await company_controller.get_employer_by_uid(user_id=user.uid)

    if not employer_profile or not employer_profile.is_admin:
        flash("Only company administrators can update roles", "danger")
        return redirect(url_for("company.employers_list"))

    # Cannot update own role
    if employer_profile.employer_id == employer_id:
        flash("You cannot change your own role", "danger")
        return redirect(url_for("company.employers_list"))

    form_data = request.get_json() if request.is_json else request.form
    is_admin = form_data.get("is_admin", "false") == "true"

    try:
        # Get employer to update
        target_employer = await company_controller.get_employer_by_id(employer_id)

        if not target_employer or target_employer.company_id != employer_profile.company_id:
            flash("Invalid employer specified", "danger")
            return redirect(url_for("company.employers_list"))

        # Update role
        await company_controller.update_employer_role(
            employer_id=employer_id,
            is_admin=is_admin
        )

        role = "Administrator" if is_admin else "Team Member"
        flash(f"{target_employer.full_name}'s role updated to {role}", "success")
    except Exception as e:
        logger.error(f"Error updating employer role: {str(e)}")
        flash("Failed to update role. Please try again.", "danger")

    return redirect(url_for("company.employers_list"))


@employer_route.route("/join-company/<token>", methods=["GET", "POST"])
@flask_error_handler
async def join_company(token: str):
    """Endpoint for invited users to complete their registration"""
    company_controller = get_controller('company')

    # Validate token
    invitation = await company_controller.get_invitation_by_token(token)
    if not invitation or invitation.expires_at < datetime.now(timezone.utc):
        flash("Invalid or expired invitation link", "danger")
        return redirect(url_for("auth.login"))

    # Get employer details
    employer = await company_controller.get_employer_by_id(invitation.employer_id)
    if not employer or employer.is_verified:
        flash("Invalid invitation or you've already joined", "danger")
        return redirect(url_for("auth.login"))

    # Get company details
    company = await company_controller.get_company_by_id(employer.company_id)

    if request.method == "GET":
        context = {
            "full_name": employer.full_name,
            "email": employer.company_email,
            "company_name": company.name if company else "Unknown Company",
            "token": token
        }
        return render_template("company/join_company.html", **context)

    # Handle POST (form submission)
    form_data = request.form
    password = form_data.get("password")
    confirm_password = form_data.get("confirm_password")

    # Validate passwords match
    if password != confirm_password:
        flash("Passwords do not match", "danger")
        return redirect(request.url)

    try:
        # Create user account
        user_controller = get_controller('users')
        user = await user_controller.register_user(
            email=employer.company_email,
            password=password,
            full_name=employer.full_name,
            role="employer"
        )

        # Link employer to user account
        await company_controller.link_employer_to_user(
            employer_id=employer.employer_id,
            user_uid=user.uid
        )

        # Mark employer as verified
        await company_controller.mark_employer_as_verified(employer.employer_id)

        # Delete invitation
        await company_controller.delete_invitation(invitation.invitation_id)

        flash("Account created successfully! You can now log in", "success")
        return redirect(url_for("auth.login"))

    except Exception as e:
        logger.error(f"Error completing registration: {str(e)}")
        flash("Failed to complete registration. Please try again.", "danger")
        return redirect(request.url)
