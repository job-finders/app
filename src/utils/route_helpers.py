# src/utils/route_helpers.py
from flask import current_app
from functools import wraps


def get_controller(controller_name: str):
    """Helper function to get controller from factory"""
    factory = current_app.controller_factory

    controller_map = {
        'jobs_search': factory.get_jobs_search_controller,
        'jobs_workflow': factory.get_jobs_workflow_controller,
        'resume': factory.get_resume_controller,
        'company': factory.get_company_controller,
        'users': factory.get_users_controller,
        'ats': factory.get_ats_controller,
        'job_seeker_profile': factory.get_job_seeker_profile_controller,
        'employer_agents': factory.get_employer_agents_controller,
        'employee_agents': factory.get_employee_agents_controller,
    }

    if controller_name not in controller_map:
        raise ValueError(f"Unknown controller: {controller_name}")

    return controller_map[controller_name]()


def get_service(service_name: str):
    """Helper function to get service from factory"""
    factory = current_app.service_factory

    service_map = {
        'send_mail': factory.get_send_mail,
        'encryptor': factory.get_encryptor,
        'scraper': factory.get_junction_scraper,
        'notifications': factory.get_notifications_controller,
    }

    if service_name not in service_map:
        raise ValueError(f"Unknown service: {service_name}")

    return service_map[service_name]()


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