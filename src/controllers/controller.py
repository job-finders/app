from flask import Flask
from pymysql import OperationalError

from src.database.sql import Session
from src.logger import init_logger


class Controllers:
    """
        **Controllers**
            registers controllers
    """

    def __init__(self, session_maker=Session):
        self.sessions = [session_maker() for _ in range(20)]
        self.logger = init_logger(self.__class__.__name__)

    def get_session(self) -> Session:
        try:
            if self.sessions:
                return self.sessions.pop()
            self.sessions = [Session() for _ in range(20)]
            return self.get_session()
        except OperationalError as e:
            self.logger.info("Operational Error")

    def setup_error_handler(self, app: Flask):
        # app.add_url_rule("")
        pass

    def init_app(self, app: Flask):
        """
            **init_app**
        :param app:
        :return:
        """
        self.setup_error_handler(app=app)

        session_maker = app.config.get('session_maker')
        session_limit = app.config.get('session_limit')

        if session_maker and session_limit:
            self.sessions = [session_maker() for _ in range(session_limit)]
