import os
from flask import Flask



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

    blueprints = [
        auth_route, home_route, jobs_workflow_route, jobs_search_route,
        seo_route, blog_route, users_route, jobseeker_route,
        jobseeker_profiles_bp, resume_routes, jobseeker_applications_route,
        cron_route, ats_tool_route, company_bp, company_search_routes
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

# Create App Method
def create_app(config):
    """Flask application factory"""
    from src.utils import template_folder, static_folder
    app = Flask(__name__)
    app.url_map.strict_slashes = False
    app.template_folder = template_folder()
    app.static_folder = static_folder()
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.config['BASE_URL'] = "https://jobfinders.site"

    # Configure upload settings
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB limit
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    with app.app_context():
        # Initialize service and controller factories
        from src.factories.controller_factory import ControllerFactory
        from src.factories.service_factory import ServiceFactory
        service_factory = ServiceFactory(app)
        controller_factory = ControllerFactory(app, service_factory)

        # Store factories in app for access in routes
        app.service_factory = service_factory
        app.controller_factory = controller_factory

        # Run boot sequence
        from src.main.boot import boot
        boot()

        # Initialize scraper if needed
        scraper = service_factory.get_junction_scraper()
        scraper.init_app(app)

        # Registering Error Handling
        from src.main.error_handling import register_error_handlers
        register_error_handlers(app)

        # Register blueprints
        _register_blueprints(app)

        # Register template filters
        _register_template_filters(app)

        # Clean Controllers Upon Exit
        @app.teardown_appcontext
        def shutdown_controllers(exception=None):
            if _controller_factory := app.extensions.get('controller_factory'):
                _controller_factory.close_all()

    return app