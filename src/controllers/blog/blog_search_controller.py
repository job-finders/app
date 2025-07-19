from src.controllers.controller import Controllers


class BlogSearchController(Controllers):
    pass

    def __init__(self, factory):
        super().__init__(factory)
        # Job search specific initialization
        # self.cache = CacheManager()

    def init_app(self, app):
        super().init_app(app)
        # App-specific initialization
        # self.cache.init_app(app)