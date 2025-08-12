"""
Test Factory Registrations

Comprehensive tests to verify that all job actions components are properly
registered in their respective factories and can be accessed through the
established patterns.
"""

import pytest
from unittest.mock import Mock, patch
from flask import Flask

from src.factories.controller_factory import ControllerFactory
from src.factories.service_factory import ServiceFactory
from src.utils.route_helpers import get_controller, get_service, _get_controller_map, _get_service_map


class TestFactoryRegistrations:
    """Test suite for factory registration verification"""

    def setup_method(self):
        """Set up test fixtures"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True

        # Initialize factories
        self.service_factory = ServiceFactory(self.app)
        self.controller_factory = ControllerFactory(self.app, self.service_factory)

        # Set up app context
        self.app_context = self.app.app_context()
        self.app_context.push()

    def teardown_method(self):
        """Clean up test fixtures"""
        if hasattr(self, 'app_context'):
            self.app_context.pop()

    def test_controller_factory_has_job_actions_controller(self):
        """Test that ControllerFactory has JobActionsController registration"""
        # Check that the method exists
        assert hasattr(self.controller_factory, 'get_job_actions_controller')

        # Check that it's callable
        assert callable(getattr(self.controller_factory, 'get_job_actions_controller'))

    def test_service_factory_has_job_actions_service(self):
        """Test that ServiceFactory has JobActionsService registration"""
        # Check that the method exists
        assert hasattr(self.service_factory, 'get_job_actions_service')

        # Check that it's callable
        assert callable(getattr(self.service_factory, 'get_job_actions_service'))

    def test_service_factory_has_job_actions_analytics_service(self):
        """Test that ServiceFactory has JobActionsAnalyticsService registration"""
        # Check that the method exists
        assert hasattr(self.service_factory, 'get_job_actions_analytics_service')

        # Check that it's callable
        assert callable(getattr(self.service_factory, 'get_job_actions_analytics_service'))

    def test_controller_map_includes_job_actions(self):
        """Test that controller map includes job_actions mapping"""
        controller_map = _get_controller_map()

        # Check that job_actions is in the map
        assert 'job_actions' in controller_map

        # Check that it maps to the correct method
        assert controller_map['job_actions'] == 'get_job_actions_controller'

    def test_service_map_includes_job_actions_services(self):
        """Test that service map includes job actions services"""
        service_map = _get_service_map()

        # Check that job_actions is in the map
        assert 'job_actions' in service_map
        assert service_map['job_actions'] == 'get_job_actions_service'

        # Check that job_actions_analytics is in the map
        assert 'job_actions_analytics' in service_map
        assert service_map['job_actions_analytics'] == 'get_job_actions_analytics_service'

    @patch('src.database.sql.Session')
    def test_job_actions_service_instantiation(self, mock_session):
        """Test that JobActionsService can be instantiated through factory"""
        # Mock the session to avoid database dependencies
        mock_session.return_value = Mock()

        # Get service through factory
        service = self.service_factory.get_job_actions_service()

        # Verify it's the correct type
        from src.services.job_actions_service import JobActionsService
        assert isinstance(service, JobActionsService)

        # Verify it has the required interface methods
        assert hasattr(service, 'execute')
        assert callable(service.execute)

    @patch('src.database.sql.Session')
    def test_job_actions_analytics_service_instantiation(self, mock_session):
        """Test that JobActionsAnalyticsService can be instantiated through factory"""
        # Mock the session to avoid database dependencies
        mock_session.return_value = Mock()

        # Get service through factory
        service = self.service_factory.get_job_actions_analytics_service()

        # Verify it's the correct type
        from src.services.job_actions_analytics import JobActionsAnalyticsService
        assert isinstance(service, JobActionsAnalyticsService)

        # Verify it has the required interface methods
        assert hasattr(service, 'execute')
        assert callable(service.execute)

    @patch('src.utils.route_helpers.get_service')
    def test_job_actions_controller_instantiation(self, mock_get_service):
        """Test that JobActionsController can be instantiated through factory"""
        # Mock the service dependencies
        mock_service = Mock()
        mock_get_service.return_value = lambda: mock_service

        # Get controller through factory
        controller = self.controller_factory.get_job_actions_controller()

        # Verify it's the correct type
        from src.controllers.jobs.actions import JobActionsController
        assert isinstance(controller, JobActionsController)

        # Verify it has the required methods
        assert hasattr(controller, 'like_job')
        assert hasattr(controller, 'unlike_job')
        assert hasattr(controller, 'save_job')
        assert hasattr(controller, 'unsave_job')
        assert hasattr(controller, 'share_job')

    @patch('src.utils.route_helpers.current_app')
    def test_get_controller_helper_function(self, mock_current_app):
        """Test that get_controller helper function works for job_actions"""
        # Mock the app context
        mock_current_app.extensions = {
            'controller_factory': self.controller_factory
        }

        # Mock the controller to avoid initialization issues
        mock_controller = Mock()
        self.controller_factory._controllers['job_actions'] = mock_controller

        with self.app.test_request_context():
            # Test getting controller through helper
            controller = get_controller('job_actions')
            assert controller is mock_controller

    @patch('src.utils.route_helpers.current_app')
    def test_get_service_helper_function(self, mock_current_app):
        """Test that get_service helper function works for job actions services"""
        # Mock the app context
        mock_current_app.extensions = {
            'service_factory': self.service_factory
        }

        # Mock the services to avoid initialization issues
        mock_service = Mock()
        self.service_factory._services['job_actions'] = mock_service

        with self.app.test_request_context():
            # Test getting service through helper
            service_getter = get_service('job_actions')
            assert callable(service_getter)

    def test_factory_singleton_behavior(self):
        """Test that factories return the same instance on multiple calls"""
        # Test service factory singleton behavior
        service1 = self.service_factory.get_job_actions_service()
        service2 = self.service_factory.get_job_actions_service()
        assert service1 is service2

        analytics1 = self.service_factory.get_job_actions_analytics_service()
        analytics2 = self.service_factory.get_job_actions_analytics_service()
        assert analytics1 is analytics2

        # Test controller factory singleton behavior
        controller1 = self.controller_factory.get_job_actions_controller()
        controller2 = self.controller_factory.get_job_actions_controller()
        assert controller1 is controller2

    def test_factory_clear_cache_functionality(self):
        """Test that factory cache clearing works properly"""
        # Get services to populate cache
        service = self.service_factory.get_job_actions_service()
        analytics = self.service_factory.get_job_actions_analytics_service()

        # Verify they're cached
        assert 'job_actions' in self.service_factory._services
        assert 'job_actions_analytics' in self.service_factory._services

        # Clear cache
        self.service_factory.clear_cache()

        # Verify cache is cleared
        assert 'job_actions' not in self.service_factory._services
        assert 'job_actions_analytics' not in self.service_factory._services

    def test_controller_factory_dependency_injection(self):
        """Test that controller factory properly injects dependencies"""
        controller = self.controller_factory.get_job_actions_controller()

        # Verify that the controller has the factory reference
        assert hasattr(controller, 'factory')
        assert controller.factory is self.controller_factory

    def test_service_factory_session_injection(self):
        """Test that service factory properly injects session factory"""
        service = self.service_factory.get_job_actions_service()

        # Verify that the service has the session factory
        assert hasattr(service, 'session_factory')
        assert callable(service.session_factory)

        analytics = self.service_factory.get_job_actions_analytics_service()

        # Verify that the analytics service has the session factory
        assert hasattr(analytics, 'session_factory')
        assert callable(analytics.session_factory)


class TestFactoryIntegration:
    """Integration tests for factory pattern usage"""

    def setup_method(self):
        """Set up test fixtures"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True

        # Initialize factories
        self.service_factory = ServiceFactory(self.app)
        self.controller_factory = ControllerFactory(self.app, self.service_factory)

        # Set up app context
        self.app_context = self.app.app_context()
        self.app_context.push()

    def teardown_method(self):
        """Clean up test fixtures"""
        if hasattr(self, 'app_context'):
            self.app_context.pop()

    @patch('src.database.sql.Session')
    @patch('src.utils.route_helpers.get_service')
    def test_controller_service_integration(self, mock_get_service, mock_session):
        """Test that controller properly integrates with service layer"""
        # Mock dependencies
        mock_session.return_value = Mock()
        mock_service = Mock()
        mock_get_service.return_value = lambda: mock_service

        # Get controller and initialize it
        controller = self.controller_factory.get_job_actions_controller()
        controller.init_app(self.app)

        # Verify service integration
        assert controller.job_actions_service is mock_service

    def test_factory_error_handling(self):
        """Test that factories handle errors gracefully"""
        # Test invalid controller name
        with pytest.raises(ValueError, match="Unknown controller"):
            get_controller('invalid_controller')

        # Test invalid service name
        with pytest.raises(ValueError, match="Unknown service"):
            get_service('invalid_service')

    def test_factory_thread_safety(self):
        """Test that factories are thread-safe"""
        import threading
        import time

        results = []

        def get_service_in_thread():
            service = self.service_factory.get_job_actions_service()
            results.append(service)

        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=get_service_in_thread)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all threads got the same instance
        assert len(results) == 5
        assert all(service is results[0] for service in results)


if __name__ == '__main__':
    pytest.main([__file__])
