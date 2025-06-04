# src/security/rate_limiting.py
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["100 per minute"])


def init_rate_limiting(app):
    limiter.init_app(app)

    # Stricter limits for sensitive endpoints
    limiter.limit("10/minute")(employee_agents_route)
    limiter.limit("5/minute")(employer_agents_route)

    # Exempt health check endpoint
    limiter.exempt("health.check_status")