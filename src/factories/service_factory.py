# src/factories/service_factory.py
from typing import Dict, Any

from services.hashnode.hashnode_agemt_interface import HashnodeAgentCommandRegistry
from services.hashnode.hashnode_client import HashnodeService
from src.services.ip_address_service import get_ip_address
from src.logger import init_logger
from src.emailer import SendMail
from src.controllers.encryptor import Encryptor
from src.scrappers import JunctionScraper
from src.controllers.notifications import NotificationsController
from src.utils.file_uploads import CompanyDocumentsService



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
        return self._services["ip_address"]

    def get_init_logger(self):
        if "logger" not in self._services:
            self._services["logger"] = init_logger
        return self._services['logger']

    def get_hashnode_service(self) -> HashnodeService:
        """
        Get or create a singleton instance of HashnodeService.

        Requires the Hashnode API token, which should be configured in the app config.

        Returns:
            HashnodeService: Instance for interacting with Hashnode APIs.
        :return:
        """
        if 'hashnode_service' not in self._services:
            token = self.app.config.get("HASHNODE_API_TOKEN")
            if not token:
                raise ValueError("HASHNODE_API_TOKEN not set in config")
            self._services['hashnode_service'] = HashnodeService(token)
        return self._services['hashnode_service']

    def get_hashnode_command_registry(self) -> HashnodeAgentCommandRegistry:
        """
        Retrieve or initialize the HashnodeAgentCommandRegistry used by AI agents
        to interact with the Hashnode blogging platform.

        This registry exposes structured command metadata and function bindings
        that can be introspected or called by intelligent agents (e.g., LLMs or task runners)
        to perform actions like:
        - Fetching user info
        - Retrieving blog posts
        - Creating new posts
        - Updating existing posts

        The registry wraps the `HashnodeService`, which handles low-level API communication.
        It is lazily instantiated and cached in `_services`.

        Returns:
            HashnodeAgentCommandRegistry: The registry instance exposing Hashnode command functions.

        Raises:
            RuntimeError: If the HashnodeService could not be initialized (e.g., missing token config).

        Example:
            registry = factory.get_hashnode_command_registry()
            commands = registry.get_commands()
            result = await commands["create_post"]["fn"](CreatePostInput(...))

        Notes for AI Agents:
            Use this interface to dynamically list available commands, understand input requirements,
            and call blogging operations without hardcoding logic.
        """
        if 'hashnode_command_registry' not in self._services:
            service = self.get_hashnode_service()
            self._services['hashnode_command_registry'] = HashnodeAgentCommandRegistry(service)
        return self._services['hashnode_command_registry']

    def clear_cache(self):
        """Clear all cached service instances"""
        self._services.clear()

    @classmethod
    def get_current(cls):
        """Get current service factory from Flask app context"""
        from flask import current_app
        return current_app.extensions.get('service_factory')
