from datetime import datetime, timedelta

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, Response, make_response

from src.database.models.users import User
from src.database.models import Role
from src.main import users_controller

auth_route = Blueprint("auth", __name__, template_folder="templates")


async def create_response(redirect_url, message=None, category=None) -> Response:
    response = make_response(redirect(redirect_url))
    if message and category:
        flash(message=message, category=category)
    return response



@auth_route.route("/login", methods=["GET", "POST"])
async def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        remember_me = request.form.get("remember_me")
        thirty_days = 0
        thirty_minutes = 0
        REMEMBER_ME_DELAY = thirty_days if remember_me else thirty_minutes

        user = await users_controller.login_user(email=email, password=password)
        if not user:
            flash("Invalid email or password", "danger")
            return redirect(url_for("auth.login"))

        response = await create_response(url_for('home.get_home'))

        expiration = datetime.utcnow() + timedelta(minutes=REMEMBER_ME_DELAY)

        response.set_cookie('auth', value=user.uid, expires=expiration, httponly=True)

        flash("Login successful", "success")

        return redirect(url_for("home.get_home"))

    return render_template("login.html")


@auth_route.route("/logout")
async def logout():
    # Clear the session and the 'auth' cookie
    session.clear()
    response = make_response(redirect(url_for("auth.login")))

    # Expire the auth cookie
    response.set_cookie('auth', '', expires=0, httponly=True)

    flash("Logged out successfully", "info")

    return response

@auth_route.route("/subscribe", methods=["POST", "GET"])
async def subscribe():

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
    user = await users_controller.create_user(user_data)

    # Automatically log the user in
    response = make_response(redirect(url_for("home.get_home")))
    expiration = datetime.utcnow() + timedelta(minutes=30)

    response.set_cookie("auth", value=user.uid, expires=expiration, httponly=True)

    flash("Subscription successful! You are now logged in.", "success")
    return response



@auth_route.route("/password-reset", methods=["GET", "POST"])
async def password_reset():
    if request.method == "GET":
        return render_template("password_reset.html")

    email = request.form.get("email")

    if not email or "@" not in email:
        flash("Please enter a valid email address.", "danger")
        return redirect(request.referrer or url_for("auth.password_reset"))

    user = await users_controller.get_user_by_email(email)
    if not user:
        flash("If the email exists in our system, a reset link has been sent.", "info")
        return redirect(url_for("auth.password_reset"))

    # Send the reset link (with async)
    await users_controller.send_reset_link(email)

    flash("Check your email for a password reset link.", "success")
    return redirect(url_for("auth.get_auth"))
