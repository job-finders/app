from flask_wtf.csrf import CSRFProtect
from flask import current_app

csrf = CSRFProtect()


def init_csrf_protection(app):
    csrf.init_app(app)
    app.config['WTF_CSRF_TIME_LIMIT'] = 1800  # 30 minutes

    # Exempt API endpoints if needed
    csrf.exempt('api.*')
