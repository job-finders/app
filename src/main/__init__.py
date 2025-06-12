import logging
import os

import timedelta
from flask import g, Flask, request
from werkzeug.middleware.proxy_fix import ProxyFix
import atexit



def _register_blueprints(app):
    """Register all route blueprints"""

    from src.routes.auth_routes import auth_route
    from src.routes.home_routes import home_route
    from src.routes.jobs_routes import jobs_workflow_route, jobs_search_route
    from src.routes.seo_routes import seo_route
    from src.routes.blog_routes import blog_route
    from src.routes.users_routes import users_route
    from src.routes.jobseeker_routes import jobseeker_route, jobseeker_profiles_bp, jobseeker_applications_route
    from src.routes.resumes_routes import resume_routes
    from src.routes.cron_routes import cron_route
    from src.routes.ats_routes import ats_tool_route
    from src.routes.company_routes import company_bp, company_search_routes
    from src.routes.billing_routes import billing_route

    blueprints = [
        auth_route, home_route, jobs_workflow_route, jobs_search_route,
        seo_route, blog_route, users_route, jobseeker_route,
        jobseeker_profiles_bp, resume_routes, jobseeker_applications_route,
        cron_route, ats_tool_route, company_bp, company_search_routes, billing_route
    ]
    for blueprint in blueprints:
        app.register_blueprint(blueprint)

def _register_template_filters(app):
    """Register Jinja2 template filters"""
    from src.utils import format_title, format_description, intcomma, datetimeformat, current_year
    app.jinja_env.filters['title'] = format_title
    app.jinja_env.filters['description'] = format_description
    app.jinja_env.filters['intcomma'] = intcomma
    app.jinja_env.filters['datetimeformat'] = datetimeformat
    app.jinja_env.filters['current_year'] = current_year

    @app.template_filter('round')
    def round_filter(value, precision=0):
        return round(value, precision)

    # Add safe HTML filter
    import bleach
    @app.template_filter('safe_html')
    def safe_html_filter(html):
        """Sanitize HTML output to prevent XSS"""
        return bleach.clean(html, tags=bleach.sanitizer.ALLOWED_TAGS + ['p', 'br', 'div'])

def supported_content_types () -> dict[str, str]:
    """

    :return:
    """
    return {
        # Documents
        'pdf': 'application/pdf',
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'txt': 'text/plain',
        'md': 'text/markdown',
        'rtf': 'application/rtf',
        'odt': 'application/vnd.oasis.opendocument.text',
        # Images
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'gif': 'image/gif',
        'bmp': 'image/bmp',
        'webp': 'image/webp',
        'svg': 'image/svg+xml',
        'ico': 'image/x-icon',
        'tiff': 'image/tiff',
        'tif': 'image/tiff',
    }


# Create App Method
def create_app(config):
    """Flask application factory with enhanced security"""
    from src.utils import template_folder, static_folder
    app = Flask(__name__)

    # ========================
    # 1. Fundamental Security
    # ========================
    app.url_map.strict_slashes = False
    app.config['SECRET_KEY'] = os.environ.get('APP_SECRET_KEY', config.SECRET_KEY)
    app.config['SESSION_COOKIE_SECURE'] = True  # Only send cookies over HTTPS
    app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent client-side JS access
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta.Timedelta(minutes=30)  # Shorter sessions


    # Proxy configuration
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,
        x_proto=1,
        x_host=1,
        x_prefix=1
    )

    # ========================
    # 2. Content Security
    # ========================
    app.template_folder = template_folder()
    app.static_folder = static_folder()
    app.config['BASE_URL'] = "https://jobfinders.site"

    # Configure upload settings
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB limit
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Safe file upload validation
    app.config['ALLOWED_EXTENSIONS'] = {
        'pdf', 'doc', 'docx', 'txt', 'md', 'rtf', 'odt',
        'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg', 'ico', 'tiff', 'tif'
    }
    app.config['CONTENT_TYPE_MAP'] = supported_content_types()

    with app.app_context():
        # ========================
        # 3. Security Monitoring
        # ========================
        # Initialize security logging
        security_logger = logging.getLogger('security')
        security_logger.setLevel(logging.WARNING)
        security_handler = logging.FileHandler('security.log')
        security_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        security_logger.addHandler(security_handler)

        # Initialize service and controller factories
        from src.factories.controller_factory import ControllerFactory
        from src.factories.service_factory import ServiceFactory
        service_factory = ServiceFactory(app)
        controller_factory = ControllerFactory(app, service_factory)

        # Store factories in app for access in routes
        app.service_factory = service_factory
        app.controller_factory = controller_factory

        # ========================
        # 5. Boot Sequence
        # ========================
        # Run boot sequence
        # Run boot sequence
        from src.main.boot import boot
        boot()

        # Initialize scraper if needed
        scraper = service_factory.get_junction_scraper()
        scraper.init_app(app)
        # ========================
        # 6. Security Middleware
        # ========================
        # Adding Security headers
        from src.firewall.headers import configure_security_headers
        configure_security_headers(app)

        from src.firewall.monitor import detect_attacks
        # Security Middleware
        app.before_request(detect_attacks)
        # Database security
        from src.firewall.database_sec import safe_query
        app.extensions['safe_query'] = safe_query

        # CSRF Protection
        # from src.firewall.csrf import init_csrf_protection
        # init_csrf_protection(app)

        # ========================
        # 7. Error Handling
        # ========================
        from src.main.error_handling import register_error_handlers
        register_error_handlers(app)
        # ========================
        # BLUE PRINTS REGISTRATIONS
        # ========================
        # Register blueprints
        _register_blueprints(app)
        # Register template filters
        _register_template_filters(app)

        # ========================
        # ADD AND INITIALIZE RATE LIMITER
        from src.firewall.rate_limiting import limiter, update_cloudflare_ips
        limiter.init_app(app)
        update_cloudflare_ips()
        
        # ========================
        # 9. Secure Teardown
        # ========================
        # Clean Controllers Upon Exit
        @app.teardown_appcontext
        def shutdown_controllers(exception=None):
            if _controller_factory := app.extensions.get('controller_factory'):
                _controller_factory.close_all()

            # Clear sensitive data from g Object
            for key in list(vars(g).keys()):
                controller = getattr(g, key, None)
                if hasattr(controller, 'close_sessions'):
                    controller.close_sessions()
        # ========================
        # 10. Security Auditing
        # ========================
        @app.after_request
        def security_audit(response):
            """Log security-relevant request/response data"""
            from src.firewall.auditing import log_security_event
            log_security_event(request, response)
            return response

        ############################################
        ## AP SCHEDULER INTERGRATION
        ############################################
        from src.tasks.task_scheduler.ap_scheduler import create_scheduler
        from src.tasks.task_scheduler.admin_ap_scheduler import schedule_app_tasks

        scheduler = create_scheduler(app=app)

        # This Schedules Admin Jobs that are suppose to run in AP Scheduler
        schedule_app_tasks(scheduler=scheduler, app=app)
        scheduler.start()
        atexit.register(scheduler.shutdown)        

    return app