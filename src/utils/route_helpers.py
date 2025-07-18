# src/utils/route_helpers.py
from functools import lru_cache
from functools import wraps

# src/utils/route_helpers.py
from flask import g, current_app


# Cache the controller map since it's static
# @lru_cache(maxsize=1)
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
        'billing': 'get_billing_controller',
        'industry_taxonomy': 'get_industry_taxonomy_controller'}

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
        # NOTE: Here we get and Initialize a Controller which is Ussually a Class
        controller = getattr(factory, getter_name)()
        # Cache for current request
        # noinspection PyProtectedMember
        g._controllers[controller_name] = controller
        return controller
    except AttributeError:
        raise RuntimeError(f"Factory missing method: {getter_name}") from None
    except Exception as e:

        raise RuntimeError(
            f"Error getting controller '{controller_name}' via '{getter_name}': {type(e).__name__}: {e}"
        ) from e

# Cache the service map since it's static
@lru_cache(maxsize=1)
def _get_service_map():
    """Static service mapping configuration"""
    return {
        'send_mail': 'get_send_mail',
        'encryptor': 'get_encryptor',
        'scraper': 'get_junction_scraper',
        'notifications': 'get_notifications_controller',
        'company_document_loader': 'get_company_document_loader',
        'logger': 'get_init_logger',
        'ip_address': 'get_ip_address',
        'hashnode': 'get_hashnode_service',
        'hashnode_commander': 'get_hashnode_command_registry',
        'http_request': 'get_http_request_service',

    }


# noinspection DuplicatedCode
def get_service(service_name: str):
    """
    Helper function to get service from factory
    Uses request-level caching for performance
    """
    if not hasattr(g, '_services'):
        g._services = {}
    elif service_name in g._services:
        # noinspection PyProtectedMember
        return g._services[service_name]

    service_map = _get_service_map()
    if service_name not in service_map:
        raise ValueError(f"Unknown service: {service_name}. "
                         f"Valid options: {', '.join(service_map.keys())}")

    factory = getattr(current_app, 'extensions', {}).get('service_factory')
    if not factory:
        raise RuntimeError("Service factory not initialized in app context")
    getter_name = service_map[service_name]
    try:
        # NOTE: Services gets called where they are needed cause they often need extra data to run.
        service = getattr(factory, getter_name)
        g._services[service_name] = service
        return service
    except AttributeError:
        raise RuntimeError(f"Factory missing method: {getter_name}") from None
    except Exception as e:
        raise RuntimeError(f"Error getting service {service_name}: {str(e)}") from e

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