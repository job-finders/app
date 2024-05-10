from flask import Flask
from src.emailer import SendMail
from src.scrappers import JunctionScrapper, CareerScrapper, Scrapper
from src.utils import template_folder, static_folder, format_title, format_description, bootstrap_database


bootstrap_database()
send_mail = SendMail()

from src.controllers import StorageController, NotificationsController
notifications_controller = NotificationsController()

# initializing models and controllers

storage_controller = StorageController()
scrapper = Scrapper()
junction_scrapper = JunctionScrapper(scrapper=scrapper)
career_scrapper = CareerScrapper(scrapper=scrapper)


def create_app(config):
    """

    :param config:
    :return:
    """
    app: Flask = Flask(__name__)
    app.template_folder = template_folder()
    app.static_folder = static_folder()
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.config['BASE_URL'] = "https://jobfinders.site"

    with app.app_context():
        # initialization
        # storage_controller.init_app(app=app)
        run_every_hour = 3
        junction_scrapper.init_app(app=app, timer_multiplier=run_every_hour)
        # career_scrapper.init_app(app=app)

        # importing routes
        from src.routes.home import home_route
        from src.routes.seo import seo_route
        from src.routes.blog import blog_route

        # registering routes
        app.register_blueprint(home_route)
        app.register_blueprint(seo_route)
        app.register_blueprint(blog_route)

        # registering filters
        app.jinja_env.filters['title'] = format_title
        app.jinja_env.filters['description'] = format_description
    return app, junction_scrapper
