import re
import asyncio
from functools import wraps, lru_cache
from typing import Optional, Callable, Any
from flask import request, redirect, url_for, flash, g, abort, current_app

from src.database import UserORM, JobsORM, EmployerORM, CompanyBillingProfileORM
from src.database.models.billing import CompanyBillingProfile
from src.database.models.users import User
from src.database.models import Role


from src.authentication.jwt_helper import decode_jwt
from src.routes.utils import get_controller
from src.database.sql import Session
from src.logger import init_logger
auth_logger = init_logger('auth_logger')
# UUID validation to avoid unnecessary DB hits
UUID_REGEX = re.compile(r'^[a-f0-9]{8}-[a-f0-9]{4}-[1-5][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$', re.I)

def is_valid_uid(uid: str | None) -> bool:
    return bool(uid and UUID_REGEX.fullmatch(uid))


def get_minimal(model, key_field: str, key_value: str, fields: list[str], cache_prefix: str) -> Optional[dict[str, Any]]:
    cache_key = f"{cache_prefix}:{key_value}:{':'.join(fields)}"
    if cached := cache.get(cache_key):
        return cached

    with Session() as session:
        query = session.query(*[getattr(model, f) for f in fields])
        result = query.filter(getattr(model, key_field) == key_value).first()
        if not result:
            return None

        result_dict = dict(zip(fields, result))
        cache.set(cache_key, result_dict, timeout=300)
        return result_dict


def get_job_minimal(job_id: str, fields: list[str] = ['company_id', 'status']) -> Optional[dict[str, Any]]:
    return get_minimal(JobsORM, 'job_id', job_id, fields, 'job_min')


def get_employer_minimal(uid: str, fields: list[str] = ['company_id', 'employer_id']) -> Optional[dict[str, Any]]:
    return get_minimal(EmployerORM, 'user_uid', uid, fields, 'employer_min')

def employer_job_access_required(allow_admin=True):
    """sumary_line
        implementation of employer job access controll 
    Keyword arguments:
    argument -- description
    Return: return_description
    """
    
    def decorator(view_func):
        @wraps(view_func)
        async def wrapper(*args, **kwargs):
            job_id = kwargs.get('job_id')
            if not job_id:
                abort(400, "Job ID missing in request")

            user = g.current_user

            if allow_admin and user.role == Role.SYSTEM_ADMIN.value:
                return await view_func(*args, **kwargs)

            employer_dict = get_employer_minimal(user.uid)
            job_dict = get_job_minimal(job_id)

            if not job_dict:
                logger.warning(f"Job not found: {job_id}")
                abort(404, "Job not found")

            if employer_dict["company_id"] != job_dict["company_id"]:
                logger.warning(
                    f"Unauthorized job access attempt: "
                    f"User {user.uid} tried to access job {job_id} "
                    f"(Company: {employer_dict.get('company_id')} vs Job: {job_dict.get('company_id')})"
                )
                abort(403, "You don't have permission to access this job")

            return await view_func(*args, **kwargs)
        return wrapper
    return decorator

# =========================
# COMPANY ACCESS CONTROL

def company_access_control(user, resource_company_id: str, allow_admin=True) -> bool:
    """
    Validates whether the user has access to a resource based on company_id.
    
    Args:
        user: The current user object (must have .uid, .role)
        resource_company_id: The company_id attached to the resource
        allow_admin: Whether to allow system_admins to bypass check
    
    Returns:
        True if access is allowed, raises HTTPException otherwise
    """
    if allow_admin and user.role == 'system_admin':
        return True

    employer = get_employer_minimal(user.uid)
    if not employer:
        logger.warning(f"Access denied. User not found in employer table: {user.uid}")
        abort(403, "You don't have permission to access this resource")

    if employer['company_id'] != resource_company_id:
        logger.warning(
            f"Company access denied: user {user.uid} (company {employer['company_id']}) "
            f"vs resource (company {resource_company_id})"
        )
        abort(403, "You don't have permission to access this resource")

    return True


def company_access_required(allow_admin=True):
    """sumary_line
        allows access to a view function only if the user has access to the company.
    Keyword arguments:
    argument -- description
    Return: return_description
    """
    
    def decorator(view_func):
        @wraps(view_func)
        async def wrapper(*args, **kwargs):
            job_id = kwargs.get('job_id')
            if not job_id:
                abort(400, "Job ID missing in request")

            user = g.user
            job_dict = get_job_minimal(job_id)
            if not job_dict:
                logger.warning(f"Job not found: {job_id}")
                abort(404, "Job not found")

            company_access_control(user, job_dict["company_id"], allow_admin=allow_admin)

            return await view_func(*args, **kwargs)
        return wrapper
    return decorator


async def get_user_details(uid: str) -> User | None:
    """Query the database for a user by UID."""
    if not is_valid_uid(uid):
        auth_logger.warning(f"Rejected malformed UID: {uid}")
        return None

    with Session() as session:
        user = session.query(UserORM).filter(UserORM.uid == uid).first()
        if user:
            auth_logger.info(f"Authenticated UID {uid}: {user.to_dict()}")
            return User(**user.to_dict())
        else:
            auth_logger.info(f"No user found for UID {uid}")
            return None


async def resolve_user_from_jwt_cookie() -> User | None:
    token = request.cookies.get("access_token")
    if not token:
        return None

    payload = decode_jwt(token)
    if not payload:
        return None

    uid = payload.get("sub")
    role = payload.get("role")

    # Optionally, skip DB and construct user from token if data is complete
    user = await get_user_details(uid) if uid else None
    return user

async def resolve_user_from_cookie() -> User | None:
    """Resolve user from auth cookie."""
    uid = request.cookies.get('auth')
    auth_logger.info(f"Found UID Cookie: {uid}")
    return await get_user_details(uid)


# ==========================
#        DECORATORS
# ==========================

def login_required(route_function):
    @wraps(route_function)
    async def wrapper(*args, **kwargs):
        g.user = await resolve_user_from_jwt_cookie()
        if g.user :
            return await route_function(g.user, *args, **kwargs)

        flash("Login required", "danger")
        return redirect(url_for("auth.login"))
    return wrapper


def roles_required(*allowed_role: str):
    """Ensure the user has one of the allowed roles and store user in g"""
    def decorator(route_function):
        @wraps(route_function)
        async def wrapper(*args, **kwargs):
            # Resolve user and store in g object
            g.user = await resolve_user_from_jwt_cookie()
            
            if g.user and g.user.role in allowed_role:
                # Pass g.user instead of local user variable
                return await route_function(g.user, *args, **kwargs)

            flash("Access denied: insufficient privileges.", "danger")
            return redirect(url_for("home.get_home"))

        return wrapper
    return decorator


def system_admin_login(route_function):
    """Ensure the user is an admin (company context)."""
    return roles_required(Role.SYSTEM_ADMIN.value)(route_function)

def admin_login(route_function):
    """Ensure the user is an admin (company context)."""
    return roles_required(Role.ADMIN.value)(route_function)

def employer_login(route_function):
    """Add on Company and Employer Routes"""
    return roles_required(Role.EMPLOYER.value)(route_function)

def jobseeker_login(route_function):
    """Add on JobSeeker Only Routes"""
    return roles_required(Role.SEEKER.value)(route_function)

def user_details(route_function):
    """Inject user object into route if available (can be None)."""
    @wraps(route_function)
    async def wrapper(*args, **kwargs):
        user = await resolve_user_from_jwt_cookie()
        return await route_function(user, *args, **kwargs)
    return wrapper


# Company Billings . 

def get_current_company_subscription(uid: str):
    """Retrieve the current company based on the user's UID."""
    if not is_valid_uid(uid):
        auth_logger.warning(f"Invalid UID format: {uid}")
        return None
    with Session() as session:
        employer_orm = session.query(EmployerORM).filter(EmployerORM.user_uid == uid).first()
        if not employer_orm:
            auth_logger.info(f"Employer profile not found for: {uid}")
            return None
        company_id = employer_orm.company_id
        subscription_orm = session.query(CompanyBillingProfileORM).filter_by(company_id=company_id).first()
        if not subscription_orm:
            auth_logger.info(f"Company billing profile not found for: {uid}")
            return None
        return CompanyBillingProfile(**subscription_orm.to_dict())

def require_billing_role_from_trial(route_function):
    """Validate if billing role is trial or above."""
    @wraps(route_function)
    async def wrapper(*args, **kwargs):
        # Resolve user and store in g object
        g.user = await resolve_user_from_jwt_cookie()
        
        if not g.user:
            flash("Please log in to access this page", "danger")
            return redirect(url_for("auth.login"))
        
        try:
            # Run blocking DB call in separate thread
            billing_plan = await asyncio.to_thread(
                get_current_company_subscription, 
                uid=g.user.uid
            )
        except Exception as e:
            auth_logger.error(f"Billing check failed: {str(e)}")
            flash("Error retrieving subscription information", "danger")
            return redirect(url_for("company.get_dashboard"))

        if not billing_plan:
            flash("Company billing profile not found", "danger")
            return redirect(url_for("company.get_dashboard"))

        # Check subscription status
        if billing_plan.is_trial_valid or billing_plan.is_active_subscription_plan:
            return await route_function(*args, **kwargs)
        
        flash("You do not have an active subscription plan", "danger")
        return redirect(url_for("company.get_dashboard"))
    
    return wrapper


BILLING_TIERS = {
    "Trial": 0,
    "Starter": 1,
    "Growth": 2,
    "Professional": 3,
    "Enterprise": 4
}


def require_billing_role(minimum: str = "Trial"):
    """
    Requires the company billing plan to meet or exceed a minimum tier.
    Billing tiers: trial < basic < pro < enterprise
    """
    def decorator(route_function):
        @wraps(route_function)
        async def wrapper(*args, **kwargs):
            g.user = await resolve_user_from_jwt_cookie()

            if not g.user:
                flash("Please log in to access this page", "danger")
                return redirect(url_for("auth.login"))

            try:
                billing = await asyncio.to_thread(get_current_company_subscription, uid=g.user.uid)
            except Exception as e:
                auth_logger.error(f"Billing check failed: {str(e)}")
                flash("Error retrieving billing data", "danger")
                return redirect(url_for("company.get_dashboard"))

            if not billing:
                flash("Billing profile not found", "danger")
                return redirect(url_for("company.get_dashboard"))

            user_plan = billing.plan.lower() if billing.plan else "trial"
            user_plan_level = BILLING_TIERS.get(user_plan, 0)
            required_plan_level = BILLING_TIERS.get(minimum, 0)

            if user_plan_level < required_plan_level:
                flash(f"Access requires at least {minimum} subscription", "danger")
                return redirect(url_for("company.get_dashboard"))

            return await route_function(*args, **kwargs)
        return wrapper
    return decorator
