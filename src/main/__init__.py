from flask import Flask


from src.utils import template_folder, static_folder, format_title, format_description, intcomma, datetimeformat
from src.emailer import SendMail
from src.controllers.encryptor import Encryptor


send_mail = SendMail()
encryptor = Encryptor()

from src.controllers.jobs import JobsSearchController, JobsWorkflowController

job_search_controller = JobsSearchController()
jobs_workflow_controller = JobsWorkflowController()

from src.controllers.resumes import ResumeController
resume_controller = ResumeController()
from src.controllers.company import CompanyController
company_controller = CompanyController(jobs_controller=jobs_workflow_controller, resume_controller=resume_controller)
from src.scrappers import JunctionScraper

from src.controllers.users import UsersController
from src.controllers.notifications import NotificationsController

notifications_controller = NotificationsController()
from src.controllers.ats import ATSToolController


# initializing models and controllers



users_controller = UsersController()

ats_controller = ATSToolController()

junction_scrapper = JunctionScraper()


from src.controllers.jobseekers import JobSeekerProfilesController
job_seeker_profile_controller = JobSeekerProfilesController()

from src.controllers.agents import EmployerAgentsController, EmployeeAgentsController

employer_agents_controller = EmployerAgentsController()
employee_agents_controller = EmployeeAgentsController()

def create_app(config):
    """

    :param config:
    :return:
    """
    app: Flask = Flask(__name__)
    app.url_map.strict_slashes = False
    app.template_folder = template_folder()
    app.static_folder = static_folder()
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.config['BASE_URL'] = "https://jobfinders.site"


    with app.app_context():
        # initialization
        # storage_controller.init_app(app=app)
        #  12 hours
        run_every_hour = 12*60
        from src.main.boot import boot
        boot()

        users_controller.init_app(app=app)
        resume_controller.init_app(app=app)
        ats_controller.init_app(app=app, resume=resume_controller)

        encryptor.init_app(app=app)

        job_search_controller.init_app(app=app)
        jobs_workflow_controller.init_app(app=app)

        company_controller.init_app(app=app)

        # junction_scrapper.init_app(app=app, timer_multiplier=run_every_hour)
        # junction_scrapper.reload()
        junction_scrapper.init_app(app=app)


        job_seeker_profile_controller.init_app(app=app)
        # career_scrapper.init_app(app=app)

        # importing routes
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


        # registering routes
        app.register_blueprint(auth_route)
        app.register_blueprint(home_route)
        app.register_blueprint(jobs_workflow_route)
        app.register_blueprint(jobs_search_route)
        app.register_blueprint(seo_route)
        app.register_blueprint(blog_route)

        app.register_blueprint(users_route)
        app.register_blueprint(jobseeker_route)
        app.register_blueprint(jobseeker_profiles_bp)
        app.register_blueprint(resume_routes)
        app.register_blueprint(jobseeker_applications_route)

        app.register_blueprint(cron_route)
        app.register_blueprint(ats_tool_route)

        app.register_blueprint(company_bp)
        app.register_blueprint(company_search_routes)
        
        # registering filters
        app.jinja_env.filters['title'] = format_title
        app.jinja_env.filters['description'] = format_description
        app.jinja_env.filters['intcomma'] = intcomma
        app.jinja_env.filters['datetimeformat'] =  datetimeformat

        @app.template_filter('round')
        def round_filter(value, precision=0):
            return round(value, precision)

    return app
