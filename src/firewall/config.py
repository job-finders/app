# src/config.py
from datetime import timedelta


class SecurityConfig:
    # Set in production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)

    # JWT Configuration
    JWT_ALGORITHM = 'HS256'
    JWT_ISSUER = 'your-app-name'
    JWT_AUDIENCE = 'your-app-client'

    # Password Policy
    PASSWORD_MIN_LENGTH = 12
    PASSWORD_COMPLEXITY = {
        'min_lower': 1,
        'min_upper': 1,
        'min_digit': 1,
        'min_special': 1
    }

    # Security Headers
    CSP_DIRECTIVES = {
        'default-src': "'self'",
        'script-src': "'self' 'unsafe-inline'",
        'style-src': "'self' 'unsafe-inline'",
        'img-src': "'self' data:",
        'font-src': "'self'",
        'connect-src': "'self'",
        'frame-ancestors': "'none'",
        'form-action': "'self'"
    }