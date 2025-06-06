# src/factories/service_factory.py
from typing import Dict, Any

from src.logger import init_logger
from src.emailer import SendMail
from src.controllers.encryptor import Encryptor
from src.scrappers import JunctionScraper
from src.controllers.notifications import NotificationsController
from src.utils.file_uploads import CompanyDocumentsService

def get_ip_address() -> str:
    """insert a way to obtain the current ip location"""
    from src.routes.utils import get_client_ip
    from flask import request, current_app
    try:
        with current_app.app_context():
            return get_client_ip(_request=request)
    except Exception as e:
        return "0.0.0.0"


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
    def get_company_document_loader(self):
        """return a utility to obtain company uploaded file"""
        if "company_document_loader" not in self._services:
            self._services["company_document_loader"] = CompanyDocumentsService()
        return self._services["company_document_loader"]
    def get_ip_address(self):
        if "ip_address" not in self._services:
            self._services["ip_address"] = get_ip_address()
    def get_init_logger(self):
        if "logger" not in self._services:
            self._services["logger"] = init_logger
    def clear_cache(self):
        """Clear all cached service instances"""
        self._services.clear()

    @classmethod
    def get_current(cls):
        """Get current service factory from Flask app context"""
        from flask import current_app
        return current_app.extensions.get('service_factory')
