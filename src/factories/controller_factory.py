# src/factories/controller_factory.py
import threading
import time
from typing import Dict, Any

from src.controllers.agents.candidate_benchmark_controller import CandidateBenchMarkController
from src.controllers.agents.employer_ats_optimization_controller import EmployerATSOptimizationController
from src.controllers.jobs.industrial_taxonomy import IndustryTaxonomyController
from src.controllers.admin import AdminController
from src.controllers.agents import EmployeeAgentsController
from src.controllers.agents import EmployerAgentsController
from src.controllers.analytics import UserEngagementController
from src.controllers.ats import ATSToolController
from src.controllers.billing.billing_controller import BillingController
from src.controllers.company import CompanyController
from src.controllers.jobs import JobsSearchController
from src.controllers.jobs import JobsWorkflowController
from src.controllers.jobseekers import JobSeekerProfilesController
from src.controllers.resumes import ResumeController
from src.controllers.users import UsersController


from src.logger import init_logger


class ControllerFactory:
    """Factory for creating and managing controller instances with performance optimizations"""

    def __init__(self, app=None, service_factory=None):
        self.app = app
        self.service_factory = service_factory
        self._controllers: Dict[str, Any] = {}
        self._lock = threading.RLock()  # Reentrant lock for thread safety
        self._access_times: Dict[str, float] = {}
        self._cache_expiry = 3600  # 1 hour in seconds
        self.logger = init_logger(self.__class__.__name__)

        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize factory with Flask app"""
        self.app = app
        # app.extensions = getattr(app, 'extensions', {})
        app.extensions['controller_factory'] = self

        # Pre-warm critical controllers
        self.prewarm_controllers(['users', 'jobs_search', 'jobs_workflow'])

        # Setup periodic cache cleanup
        if not hasattr(app, 'controller_cache_cleanup_registered'):
            app.controller_cache_cleanup_registered = True
            self._setup_cache_cleanup()

    def _setup_cache_cleanup(self):
        """Set up periodic cache cleanup using APScheduler or similar"""
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            scheduler = BackgroundScheduler()
            scheduler.add_job(
                func=self.clean_old_controllers,
                trigger='interval',
                minutes=30
            )
            scheduler.start()
        except ImportError:
            # Fallback to simple thread if APScheduler not available
            import threading
            def cleanup_loop():
                while True:
                    time.sleep(1800)  # 30 minutes
                    self.clean_old_controllers()

            thread = threading.Thread(target=cleanup_loop, daemon=True)
            thread.start()

    def prewarm_controllers(self, controller_names):
        """Initialize frequently used controllers during app startup"""
        self.logger.info(f"PRE Warming Started")
        for name in controller_names:
            getter_name = f'get_{name}_controller'
            self.logger.info(f"Getter Name : {getter_name}")
            
            if hasattr(self, getter_name):
                getattr(self, getter_name)()
                self.logger.info(f"PRE WARMED : {getter_name}")


    def get_jobs_search_controller(self) -> JobsSearchController:
        """Get JobsSearchController instance with thread safety"""
        self.logger.info(f"Getting JobSearchController")
        return self._get_controller('jobs_search', JobsSearchController)

    def get_billing_controller(self) -> BillingController:
        """Get BillingController instance"""
        self.logger.info(f"Getting BillingController")
        return self._get_controller('billing', BillingController)

    def get_jobs_workflow_controller(self) -> JobsWorkflowController:
        """Get JobsWorkflowController instance with thread safety"""
        self.logger.info(f"Getting JobsWorkflowController")
        return self._get_controller('jobs_workflow', JobsWorkflowController)

    def get_resume_controller(self) -> ResumeController:
        """Get ResumeController instance with thread safety"""
        self.logger.info(f"Getting ResumeController")
        return self._get_controller('resume', ResumeController)

    def get_company_controller(self) -> CompanyController:
        """Get CompanyController instance with dependency flexibility"""
        self.logger.info(f"Getting CompanyController")
        return self._get_controller("company", CompanyController)

    def get_users_controller(self) -> UsersController:
        """Get UsersController instance with thread safety"""
        self.logger.info(f"Getting UsersController")
        return self._get_controller('users', UsersController)

    def get_ats_controller(self) -> ATSToolController:
        """Get ATSToolController instance with dependency flexibility"""
        self.logger.info(f"Getting ATSToolController")
        return self._get_controller('ats', ATSToolController)

    def get_job_seeker_profile_controller(self) -> JobSeekerProfilesController:
        """Get JobSeekerProfilesController instance"""
        self.logger.info(f"Getting JobSeekerProfilesController")
        return self._get_controller('job_seeker_profile', JobSeekerProfilesController)

    def get_employer_agents_controller(self) -> EmployerAgentsController:
        """Get EmployerAgentsController instance"""
        self.logger.info(f"Getting EmployerAgentsController")
        return self._get_controller('employer_agents', EmployerAgentsController)

    def get_employee_agents_controller(self) -> EmployeeAgentsController:
        """Get EmployeeAgentsController instance"""
        self.logger.info(f"Getting EmployeeAgentsController")
        return self._get_controller('employee_agents', EmployeeAgentsController)

    def get_admin_controller(self) -> AdminController:
        """Get AdminController instance"""
        self.logger.info(f"Getting AdminController")
        return self._get_controller('admin_controller', AdminController)

    def get_user_engagement_controller(self) -> UserEngagementController:
        """
            USer Engagement Controller
        :return:
        """
        self.logger.info(f"Getting UserEngagementController")
        return self._get_controller('user_engagement', UserEngagementController)

    def get_industry_taxonomy_controller(self) -> IndustryTaxonomyController:
        """Get IndustryTaxonomyController instance"""
        
        self.logger.info(f"Getting IndustryTaxonomyController")
        return self._get_controller('industry_taxonomy', IndustryTaxonomyController)

    def get_employer_ats_optimization_tool_controller(self) -> EmployerATSOptimizationController:
        """Get EmployerATSOptimizationController instance"""
        self.logger.info(f"Getting EmployerATSOptimizationController")
        return self._get_controller('employer_ats_optimization', EmployerATSOptimizationController)

    def get_candidate_benchmark_controller(self) -> CandidateBenchMarkController:
        """ Get Candidate BenchMarking Controller
            :return:
        """
        return self._get_controller('candidate_benchmarking', CandidateBenchMarkController)

    def _get_controller(self, name: str, controller_class):
        """Thread-safe controller getter with double-checked locking"""
        # First check without lock for performance
        from src.controllers.controller import ControllerInitException
        if controller := self._controllers.get(name):
            self._access_times[name] = time.time()
            return controller

        with self._lock:
            # Second check with lock for thread safety
            if controller := self._controllers.get(name):
                self._access_times[name] = time.time()
                return controller
            try:
                # Create new instance
                controller = controller_class(self)  # Pass factory for dependency access
                if self.app:
                    self.logger.info(f"Initializing Controller : {name}")
                    controller.init_app(self.app)

            except Exception as e:
                raise ControllerInitException(name, controller_class, "Error during instantiation", e) from e

            self._controllers[name] = controller
            self._access_times[name] = time.time()
            return controller

    def clean_old_controllers(self):
        """Clear infrequently used controllers to save memory"""
        with self._lock:
            current_time = time.time()
            to_delete = []

            for name, last_access in self._access_times.items():
                if current_time - last_access > self._cache_expiry:
                    to_delete.append(name)

            for name in to_delete:
                if controller := self._controllers.pop(name, None):
                    # Clean up resources if controller supports it
                    self.logger.info(f"Cleaning Up Resource for Controller : {name}")
                    if hasattr(controller, 'close'):
                        controller.close()
                self._access_times.pop(name, None)

    def clear_cache(self):
        """Clear all cached controller instances with resource cleanup"""
        with self._lock:
            for name, controller in list(self._controllers.items()):
                if hasattr(controller, 'close'):
                    controller.close()
                del self._controllers[name]
            self._access_times.clear()

    def close_all(self):
        """Alias for clear_cache for better semantics"""
        self.clear_cache()

    @classmethod
    def get_current(cls):
        """Get current controller factory from Flask app context"""
        from flask import current_app
        return current_app.extensions.get('controller_factory')

    def __del__(self):
        """Ensure resource cleanup on factory destruction"""
        self.close_all()