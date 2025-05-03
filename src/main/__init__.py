from flask import Flask


from src.utils import template_folder, static_folder, format_title, format_description, bootstrap_database
from src.emailer import SendMail
from src.controllers.encryptor import Encryptor

bootstrap_database()
send_mail = SendMail()
encryptor = Encryptor()

from src.controllers.jobs import JobsController
jobs_controller = JobsController()

from src.scrappers import JunctionScrapper, CareerScrapper, Scrapper



from src.controllers.users import UsersController

from src.controllers.storage import StorageController
from src.controllers.notifications_controller import NotificationsController

notifications_controller = NotificationsController()
from src.controllers.ats_controller import ATSToolController
from src.controllers.resume_controller import ResumeController

# initializing models and controllers

storage_controller = StorageController()
scrapper = Scrapper()
users_controller = UsersController()
ats_controller = ATSToolController()

resume_controller = ResumeController()

junction_scrapper = JunctionScrapper(scrapper=scrapper)
career_scrapper = CareerScrapper(scrapper=scrapper)


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
        ats_controller.init_app(app=app)
        encryptor.init_app(app=app)
        jobs_controller.init_app(app=app)
        junction_scrapper.init_app(app=app, timer_multiplier=run_every_hour)
        # career_scrapper.init_app(app=app)

        # importing routes
        from src.routes.auth import auth_route
        from src.routes.home import home_route
        from src.routes.jobs import jobs_route
        from src.routes.seo import seo_route
        from src.routes.blog import blog_route
        from src.routes.users import users_route
        from src.routes.jobseeker import jobseeker_route
        from src.routes.cron import cron_route
        from src.routes.ats_tool import ats_tool_route


        # registering routes
        app.register_blueprint(auth_route)
        app.register_blueprint(home_route)
        app.register_blueprint(jobs_route)
        app.register_blueprint(seo_route)
        app.register_blueprint(blog_route)

        app.register_blueprint(users_route)
        app.register_blueprint(jobseeker_route)

        app.register_blueprint(cron_route)
        app.register_blueprint(ats_tool_route)

        # registering filters
        app.jinja_env.filters['title'] = format_title
        app.jinja_env.filters['description'] = format_description
    return app, junction_scrapper
