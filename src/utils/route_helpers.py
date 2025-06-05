# src/utils/route_helpers.py
from functools import lru_cache
from functools import wraps

# src/utils/route_helpers.py
from flask import g, current_app

from logger import init_logger


# Cache the controller map since it's static
@lru_cache(maxsize=1)
def _get_controller_map():
    """Static controller mapping configuration"""
    return {
        'jobs_search': 'get_jobs_search_controller',
        'jobs_workflow': 'get_jobs_workflow_controller',
        'resume': 'get_resume_controller',
        'company': 'get_company_controller',
        'users': 'get_users_controller',
        'ats': 'get_ats_controller',
        'job_seeker_profile': 'get_job_seeker_profile_controller',
        'employer_agents': 'get_employer_agents_controller',
        'employee_agents': 'get_employee_agents_controller',
        'admin_controller': 'get_admin_controller',
        'user_engagement': 'get_user_engagement_controller',
    }

def get_controller(controller_name: str):
    """
        Helper function to get controller from factory
        # Get controller map from cache
        # Check if already cached in this request
    """
    if not hasattr(g, '_controllers'):
        g._controllers = {}
    elif controller_name in g._controllers:
        # noinspection PyProtectedMember
        return g._controllers[controller_name]
    # Returns Controller Map
    controller_map = _get_controller_map()
    # Validate controller name
    if controller_name not in controller_map:
        raise ValueError(f"Unknown controller: {controller_name}. "
                         f"Valid options: {', '.join(controller_map.keys())}")
    # Get factory from app context
    factory = getattr(current_app, 'extensions', {}).get('controller_factory')
    if not factory:
        raise RuntimeError("Controller factory not initialized in app context")
    # Get controller getter method name
    getter_name = controller_map[controller_name]
    # Get controller instance
    try:
        controller = getattr(factory, getter_name)()
        # Cache for current request
        # noinspection PyProtectedMember
        g._controllers[controller_name] = controller
        return controller
    except AttributeError:
        raise RuntimeError(f"Factory missing method: {getter_name}") from None
    except Exception as e:
        raise RuntimeError(f"Error getting controller {controller_name}: {str(e)}") from e

def get_service(service_name: str):
    """Helper function to get service from factory"""
    factory = current_app.service_factory

    service_map = {
        'send_mail': factory.get_send_mail,
        'encryptor': factory.get_encryptor,
        'scraper': factory.get_junction_scraper,
        'notifications': factory.get_notifications_controller,
        "company_document_loader": factory.get_company_document_loader,
        "logger": init_logger
    }
    if service_name not in service_map:
        raise ValueError(f"Unknown service: {service_name}")
    return service_map[service_name]


def inject_controller(controller_name: str):
    """Decorator to inject controller into route function"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            controller = get_controller(controller_name)
            return f(controller, *args, **kwargs)
        return decorated_function
    return decorator


def inject_service(service_name: str):
    """Decorator to inject service into route function"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            service = get_service(service_name)
            return f(service, *args, **kwargs)
        return decorated_function
    return decorator