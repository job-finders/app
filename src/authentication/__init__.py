import re
import asyncio
from functools import wraps, lru_cache
from flask import request, redirect, url_for, flash, g



from src.database.sql.billing_sql import CompanyBillingProfileORM
from src.database.models.billing import CompanyBillingProfile
from src.database.sql.employer import EmployerORM
from src.authentication.jwt_helper import decode_jwt
from src.database.models import Role
from src.logger import init_logger
from src.database.models.users import User
from src.database.sql import Session
from src.database.sql.users import UserORM


auth_logger = init_logger('auth_logger')

# UUID validation to avoid unnecessary DB hits
UUID_REGEX = re.compile(r'^[a-f0-9]{8}-[a-f0-9]{4}-[1-5][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$', re.I)

@lru_cache
def is_valid_uid(uid: str | None) -> bool:
    return bool(uid and UUID_REGEX.fullmatch(uid))

@lru_cache
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

"""
@route.get("/feature")
@roles_required("admin", "manager")  # Sets g.user
@require_billing_role_from_trial    # Requires g.user
@cached                             # Can now use g.user in cache keys
async def premium_feature(user: User):
    # user comes from roles_required decorator
    # g.user is also available
    return render_template(...)
"""