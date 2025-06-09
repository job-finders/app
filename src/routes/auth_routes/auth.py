from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, Response, make_response

from src.authentication.jwt_helper import create_jwt
from src.routes import flask_error_handler
from src.database.constants import utc_time
from src.logger import init_logger
from src.authentication import login_required, user_details
from src.database.models.users import User
from src.database.models import Role
from src.utils.route_helpers import get_controller

auth_route = Blueprint("auth", __name__, template_folder="templates", url_prefix="/auth")
auth_logger = init_logger('auth_logger')

async def create_response(redirect_url, message=None, category=None) -> Response:
    response = make_response(redirect(redirect_url))
    if message and category:
        flash(message=message, category=category)
    return response


@auth_route.route("/login", methods=["GET", "POST"])
@flask_error_handler
@user_details
async def login(user: User):

    if user:
        auth_logger.info("Fetching login page")
        flash("you are already logged in", "success")
        return redirect(url_for("home.get_home"))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        remember_me = request.form.get("remember_me")
        auth_logger.info(f"Submitting Login Page: {email}, {password}")
        sixty_minutes = 60
        thirty_days = 30 * 24 * 60  # 30 days × 24 hours × 60 minutes

        remember_me_delay = thirty_days if remember_me else sixty_minutes
        users_controller = get_controller('users')
        user = await users_controller.login_user(email=email, password=password)
        if not user:
            auth_logger.info("Did not find User")
            flash("Invalid email or password", "danger")
            return redirect(url_for("auth.login"))
        if user.role == Role.EMPLOYER.value:
            auth_logger.info(f"Found User Role: {user.role}")
            response = await create_response(url_for('company.get_dashboard'))
        elif user.role == Role.SEEKER.value:
            auth_logger.info(f"Found User Role : {user.role}")
            response = await create_response(url_for('jobseekers.dashboard'))
        elif user.role == Role.SYSTEM_ADMIN.value:
            auth_logger.info(f"System Admin Role or : {user.role}")
        else:
            auth_logger.info(f"System Unknown Role or : {user.role}")
            return redirect("auth.login")

        expiration = utc_time() + timedelta(minutes=remember_me_delay)
        jwt_token = create_jwt(user.model_dump(exclude={'password_hash'}))
        response.set_cookie('access_token', value=jwt_token, expires=expiration, httponly=True, secure=True, samesite="Lax")

        flash("Login successful", "success")
        return response

    return render_template("login.html")


@auth_route.route("/logout")
@flask_error_handler
@login_required
async def logout(user: User):
    # Clear the session and the 'auth' cookie
    session.clear()
    response = make_response(redirect(url_for("auth.login")))
    # Expire the auth cookie
    response.set_cookie('access_token', '', expires=0, httponly=True)
    flash("Logged out successfully", "info")
    return response

@auth_route.route("/subscribe", methods=["POST", "GET"])
@flask_error_handler
@user_details
async def subscribe(user: User):

    if user:
        flash(message="You have been logged out", category="danger")
        return redirect(url_for("auth.logout"))

    if request.method.casefold() == "get":
        return render_template('register.html')

    email = request.form.get("email")
    password = request.form.get('password')
    role = request.form.get("role")
    remember_me = request.form.get("remember_me")  # Optional checkbox

    if not Role.is_valid_role(role):
        flash("Please enter a valid role.", "danger")
        return redirect(request.referrer or url_for("home.get_home"))

    if not email or "@" not in email or not password:
        flash("Please enter a valid email and password.", "danger")
        return redirect(request.referrer or url_for("home.get_home"))

    users_controller = get_controller('users')
    existing_user = await users_controller.get_user_by_email(email=email)
    if existing_user:
        flash("You are already subscribed!", "info")
        return redirect(request.referrer or url_for("home.get_home"))

    # Create and store the user

    user_data = User.create(
        name='John Doe',
        email=email,
        password=password,
        role=role
    )
    auth_logger.info(f"User Data: {user_data}")
    user = await users_controller.create_user(user_data)
    auth_logger.info(f"User: {user}")
    # Automatically log the user in
    response = make_response(redirect(url_for("home.get_home")))
    expiration = datetime.now(timezone.utc) + timedelta(minutes=30)
    jwt_token = create_jwt(user.model_dump(exclude={'password_hash'}))

    response.set_cookie("access_token", value=jwt_token, expires=expiration, httponly=True, secure=True, samesite="Lax")

    flash("Subscription successful! You are now logged in.", "success")
    return response


@auth_route.route("/password-reset", methods=["GET", "POST"])
@flask_error_handler
async def password_reset():
    if request.method == "GET":
        return render_template("password_reset.html")

    email = request.form.get("email")

    if not email or "@" not in email:
        flash("Please enter a valid email address.", "danger")
        return redirect(request.referrer or url_for("auth.password_reset"))

    users_controller = get_controller('users')
    user = await users_controller.get_user_by_email(email)
    if not user:
        flash("If the email exists in our system, a reset link has been sent.", "info")
        return redirect(url_for("auth.password_reset"))

    # Send the reset link (with async)
    await users_controller.send_reset_link(email)

    flash("Check your email for a password reset link.", "success")
    return redirect(url_for("auth.get_auth"))
