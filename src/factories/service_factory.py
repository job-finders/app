# src/factories/service_factory.py
from typing import Dict, Any
from src.emailer import SendMail
from src.controllers.encryptor import Encryptor
from src.scrappers import JunctionScraper
from src.controllers.notifications import NotificationsController


class ServiceFactory:
    """Factory for creating and managing service instances"""

    def __init__(self, app=None):
        self.app = app
        self._services: Dict[str, Any] = {}

        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize factory with Flask app"""
        self.app = app
        app.extensions = getattr(app, 'extensions', {})
        app.extensions['service_factory'] = self

    def get_send_mail(self) -> SendMail:
        """Get SendMail service instance"""
        if 'send_mail' not in self._services:
            self._services['send_mail'] = SendMail()
        return self._services['send_mail']

    def get_encryptor(self) -> Encryptor:
        """Get Encryptor service instance"""
        if 'encryptor' not in self._services:
            encryptor = Encryptor()
            if self.app:
                encryptor.init_app(self.app)
            self._services['encryptor'] = encryptor
        return self._services['encryptor']

    def get_junction_scraper(self) -> JunctionScraper:
        """Get JunctionScraper service instance"""
        if 'junction_scraper' not in self._services:
            self._services['junction_scraper'] = JunctionScraper()
        return self._services['junction_scraper']

    def get_notifications_controller(self) -> NotificationsController:
        """Get NotificationsController service instance"""
        if 'notifications' not in self._services:
            self._services['notifications'] = NotificationsController()
        return self._services['notifications']

    def clear_cache(self):
        """Clear all cached service instances"""
        self._services.clear()

    @classmethod
    def get_current(cls):
        """Get current service factory from Flask app context"""
        from flask import current_app
        return current_app.extensions.get('service_factory')
