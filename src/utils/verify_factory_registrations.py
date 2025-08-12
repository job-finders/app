"""
Factory Registration Verification Script

This script verifies that all job actions components are properly registered
in their respective factories and can be accessed through the established
patterns. It provides comprehensive validation of the factory pattern
implementation.
"""

import sys
import traceback
from typing import Dict, List, Any
from flask import Flask

# Import factories and helpers
from src.factories.controller_factory import ControllerFactory
from src.factories.service_factory import ServiceFactory
from src.utils.route_helpers import _get_controller_map, _get_service_map


class FactoryRegistrationVerifier:
    """Verifies factory registrations and dependency injection"""

    def __init__(self):
        """Initialize the verifier with Flask app context"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True

        # Initialize factories
        self.service_factory = ServiceFactory(self.app)
        self.controller_factory = ControllerFactory(self.app, self.service_factory)

        # Results tracking
        self.results: Dict[str, Dict[str, Any]] = {
            'controller_factory': {},
            'service_factory': {},
            'route_helpers': {},
            'integration': {}
        }

        self.errors: List[str] = []
        self.warnings: List[str] = []

    def verify_all(self) -> bool:
        """Run all verification checks"""
        print("🔍 Starting Factory Registration Verification...")
        print("=" * 60)

        with self.app.app_context():
            # Run all verification checks
            self.verify_controller_factory()
            self.verify_service_factory()
            self.verify_route_helpers()
            self.verify_integration()

        # Print results
        self.print_results()

        # Return overall success
        return len(self.errors) == 0

    def verify_controller_factory(self):
        """Verify controller factory registrations"""
        print("📋 Verifying Controller Factory...")

        # Check JobActionsController registration
        try:
            # Check method exists
            if hasattr(self.controller_factory, 'get_job_actions_controller'):
                self.results['controller_factory']['get_job_actions_controller'] = '✅ Method exists'

                # Check method is callable
                method = getattr(self.controller_factory, 'get_job_actions_controller')
                if callable(method):
                    self.results['controller_factory']['job_actions_callable'] = '✅ Method is callable'

                    # Try to instantiate (with mocked dependencies)
                    try:
                        controller = method()
                        self.results['controller_factory']['job_actions_instantiation'] = '✅ Can instantiate'

                        # Check controller type
                        from src.controllers.jobs.actions import JobActionsController
                        if isinstance(controller, JobActionsController):
                            self.results['controller_factory']['job_actions_type'] = '✅ Correct type'
                        else:
                            self.results['controller_factory']['job_actions_type'] = f'❌ Wrong type: {type(controller)}'
                            self.errors.append("JobActionsController has wrong type")

                    except Exception as e:
                        self.results['controller_factory']['job_actions_instantiation'] = f'❌ Instantiation failed: {e}'
                        self.errors.append(f"JobActionsController instantiation failed: {e}")

                else:
                    self.results['controller_factory']['job_actions_callable'] = '❌ Method not callable'
                    self.errors.append("get_job_actions_controller is not callable")

            else:
                self.results['controller_factory']['get_job_actions_controller'] = '❌ Method missing'
                self.errors.append("get_job_actions_controller method missing from ControllerFactory")

        except Exception as e:
            self.results['controller_factory']['error'] = f'❌ Verification failed: {e}'
            self.errors.append(f"Controller factory verification failed: {e}")

    def verify_service_factory(self):
        """Verify service factory registrations"""
        print("🔧 Verifying Service Factory...")

        # Check JobActionsService registration
        self._verify_service_registration(
            'get_job_actions_service',
            'JobActionsService',
            'src.services.job_actions_service'
        )

        # Check JobActionsAnalyticsService registration
        self._verify_service_registration(
            'get_job_actions_analytics_service',
            'JobActionsAnalyticsService',
            'src.services.job_actions_analytics'
        )

    def _verify_service_registration(self, method_name: str, class_name: str, module_path: str):
        """Helper method to verify individual service registration"""
        try:
            # Check method exists
            if hasattr(self.service_factory, method_name):
                self.results['service_factory'][method_name] = '✅ Method exists'

                # Check method is callable
                method = getattr(self.service_factory, method_name)
                if callable(method):
                    self.results['service_factory'][f'{method_name}_callable'] = '✅ Method is callable'

                    # Try to instantiate
                    try:
                        service = method()
                        self.results['service_factory'][f'{method_name}_instantiation'] = '✅ Can instantiate'

                        # Check service type
                        module = __import__(module_path, fromlist=[class_name])
                        expected_class = getattr(module, class_name)

                        if isinstance(service, expected_class):
                            self.results['service_factory'][f'{method_name}_type'] = '✅ Correct type'

                            # Check service interface
                            if hasattr(service, 'execute') and callable(service.execute):
                                self.results['service_factory'][f'{method_name}_interface'] = '✅ Has execute method'
                            else:
                                self.results['service_factory'][f'{method_name}_interface'] = '❌ Missing execute method'
                                self.errors.append(f"{class_name} missing execute method")

                        else:
                            self.results['service_factory'][f'{method_name}_type'] = f'❌ Wrong type: {type(service)}'
                            self.errors.append(f"{class_name} has wrong type")

                    except Exception as e:
                        self.results['service_factory'][f'{method_name}_instantiation'] = f'❌ Instantiation failed: {e}'
                        self.errors.append(f"{class_name} instantiation failed: {e}")

                else:
                    self.results['service_factory'][f'{method_name}_callable'] = '❌ Method not callable'
                    self.errors.append(f"{method_name} is not callable")

            else:
                self.results['service_factory'][method_name] = '❌ Method missing'
                self.errors.append(f"{method_name} method missing from ServiceFactory")

        except Exception as e:
            self.results['service_factory'][f'{method_name}_error'] = f'❌ Verification failed: {e}'
            self.errors.append(f"{method_name} verification failed: {e}")

    def verify_route_helpers(self):
        """Verify route helper mappings"""
        print("🗺️  Verifying Route Helper Mappings...")

        # Check controller mappings
        try:
            controller_map = _get_controller_map()

            if 'job_actions' in controller_map:
                expected_method = 'get_job_actions_controller'
                actual_method = controller_map['job_actions']

                if actual_method == expected_method:
                    self.results['route_helpers']['controller_mapping'] = '✅ job_actions mapped correctly'
                else:
                    self.results['route_helpers']['controller_mapping'] = f'❌ Wrong mapping: {actual_method}'
                    self.errors.append(f"job_actions controller mapping incorrect: {actual_method}")
            else:
                self.results['route_helpers']['controller_mapping'] = '❌ job_actions not in controller map'
                self.errors.append("job_actions not found in controller map")

        except Exception as e:
            self.results['route_helpers']['controller_mapping_error'] = f'❌ Error: {e}'
            self.errors.append(f"Controller mapping verification failed: {e}")

        # Check service mappings
        try:
            service_map = _get_service_map()

            # Check job_actions service mapping
            if 'job_actions' in service_map:
                expected_method = 'get_job_actions_service'
                actual_method = service_map['job_actions']

                if actual_method == expected_method:
                    self.results['route_helpers']['service_mapping'] = '✅ job_actions service mapped correctly'
                else:
                    self.results['route_helpers']['service_mapping'] = f'❌ Wrong mapping: {actual_method}'
                    self.errors.append(f"job_actions service mapping incorrect: {actual_method}")
            else:
                self.results['route_helpers']['service_mapping'] = '❌ job_actions not in service map'
                self.errors.append("job_actions not found in service map")

            # Check job_actions_analytics service mapping
            if 'job_actions_analytics' in service_map:
                expected_method = 'get_job_actions_analytics_service'
                actual_method = service_map['job_actions_analytics']

                if actual_method == expected_method:
                    self.results['route_helpers']['analytics_mapping'] = '✅ job_actions_analytics mapped correctly'
                else:
                    self.results['route_helpers']['analytics_mapping'] = f'❌ Wrong mapping: {actual_method}'
                    self.errors.append(f"job_actions_analytics mapping incorrect: {actual_method}")
            else:
                self.results['route_helpers']['analytics_mapping'] = '❌ job_actions_analytics not in service map'
                self.errors.append("job_actions_analytics not found in service map")

        except Exception as e:
            self.results['route_helpers']['service_mapping_error'] = f'❌ Error: {e}'
            self.errors.append(f"Service mapping verification failed: {e}")

    def verify_integration(self):
        """Verify integration between components"""
        print("🔗 Verifying Component Integration...")

        try:
            # Test controller-service integration
            controller = self.controller_factory.get_job_actions_controller()

            # Check if controller can be initialized
            try:
                controller.init_app(self.app)
                self.results['integration']['controller_init'] = '✅ Controller initializes successfully'

                # Check service dependencies
                if hasattr(controller, 'job_actions_service'):
                    self.results['integration']['service_dependency'] = '✅ Service dependency injected'
                else:
                    self.results['integration']['service_dependency'] = '❌ Service dependency missing'
                    self.warnings.append("Controller missing job_actions_service dependency")

                if hasattr(controller, 'analytics_service'):
                    self.results['integration']['analytics_dependency'] = '✅ Analytics dependency injected'
                else:
                    self.results['integration']['analytics_dependency'] = '❌ Analytics dependency missing'
                    self.warnings.append("Controller missing analytics_service dependency")

            except Exception as e:
                self.results['integration']['controller_init'] = f'❌ Controller init failed: {e}'
                self.errors.append(f"Controller initialization failed: {e}")

            # Test service singleton behavior
            service1 = self.service_factory.get_job_actions_service()
            service2 = self.service_factory.get_job_actions_service()

            if service1 is service2:
                self.results['integration']['singleton_behavior'] = '✅ Services are singletons'
            else:
                self.results['integration']['singleton_behavior'] = '❌ Services not singletons'
                self.warnings.append("Services should be singletons but are not")

        except Exception as e:
            self.results['integration']['error'] = f'❌ Integration verification failed: {e}'
            self.errors.append(f"Integration verification failed: {e}")

    def print_results(self):
        """Print verification results"""
        print("\n" + "=" * 60)
        print("📊 VERIFICATION RESULTS")
        print("=" * 60)

        # Print results by category
        for category, results in self.results.items():
            if results:
                print(f"\n{category.upper().replace('_', ' ')}:")
                for check, result in results.items():
                    print(f"  {check}: {result}")

        # Print summary
        print("\n" + "=" * 60)
        print("📈 SUMMARY")
        print("=" * 60)

        if self.errors:
            print(f"❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  • {error}")

        if self.warnings:
            print(f"⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  • {warning}")

        if not self.errors and not self.warnings:
            print("✅ ALL CHECKS PASSED - Factory registrations are working correctly!")
        elif not self.errors:
            print("✅ ALL CRITICAL CHECKS PASSED - Minor warnings present")
        else:
            print("❌ CRITICAL ERRORS FOUND - Factory registrations need fixing")

        print("=" * 60)


def main():
    """Main verification function"""
    verifier = FactoryRegistrationVerifier()

    try:
        success = verifier.verify_all()

        if success:
            print("\n🎉 Factory registration verification completed successfully!")
            sys.exit(0)
        else:
            print("\n💥 Factory registration verification failed!")
            sys.exit(1)

    except Exception as e:
        print(f"\n💥 Verification script failed with error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
