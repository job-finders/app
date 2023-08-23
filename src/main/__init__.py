from flask import Flask
from src.scrappers import JunctionScrapper, CareerScrapper
from src.utils import template_folder, static_folder, format_title

junction_scrapper = JunctionScrapper()
career_scrapper = CareerScrapper()


def create_app(config):
    """

    :param config:
    :return:
    """
    app: Flask = Flask(__name__)
    app.template_folder = template_folder()
    app.static_folder = static_folder()
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.config['BASE_URL'] = "https://rental-manager.site"

    with app.app_context():
        junction_scrapper.init_app(app=app)
        career_scrapper.init_app(app=app)
        from src.routes.home import home_route
        from src.routes.seo import seo_route
        app.register_blueprint(home_route)
        app.register_blueprint(seo_route)

        app.jinja_env.filters['title'] = format_title
    return app
