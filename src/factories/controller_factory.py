# src/factories/controller_factory.py
from typing import Dict, Any
from src.controllers.jobs import JobsSearchController, JobsWorkflowController
from src.controllers.resumes import ResumeController
from src.controllers.company import CompanyController
from src.controllers.users import UsersController
from src.controllers.ats import ATSToolController
from src.controllers.jobseekers import JobSeekerProfilesController
from src.controllers.agents import EmployerAgentsController, EmployeeAgentsController


class ControllerFactory:
    """Factory for creating and managing controller instances"""

    def __init__(self, app=None, service_factory=None):
        self.app = app
        self.service_factory = service_factory
        self._controllers: Dict[str, Any] = {}

        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize factory with Flask app"""
        self.app = app
        app.extensions = getattr(app, 'extensions', {})
        app.extensions['controller_factory'] = self

    def get_jobs_search_controller(self) -> JobsSearchController:
        """Get JobsSearchController instance"""
        if 'jobs_search' not in self._controllers:
            controller = JobsSearchController()
            if self.app:
                controller.init_app(self.app)
            self._controllers['jobs_search'] = controller
        return self._controllers['jobs_search']

    def get_jobs_workflow_controller(self) -> JobsWorkflowController:
        """Get JobsWorkflowController instance"""
        if 'jobs_workflow' not in self._controllers:
            controller = JobsWorkflowController()
            if self.app:
                controller.init_app(self.app)
            self._controllers['jobs_workflow'] = controller
        return self._controllers['jobs_workflow']

    def get_resume_controller(self) -> ResumeController:
        """Get ResumeController instance"""
        if 'resume' not in self._controllers:
            controller = ResumeController()
            if self.app:
                controller.init_app(self.app)
            self._controllers['resume'] = controller
        return self._controllers['resume']

    def get_company_controller(self) -> CompanyController:
        """Get CompanyController instance"""
        if 'company' not in self._controllers:
            jobs_controller = self.get_jobs_workflow_controller()
            resume_controller = self.get_resume_controller()

            controller = CompanyController(
                jobs_controller=jobs_controller,
                resume_controller=resume_controller
            )
            if self.app:
                controller.init_app(self.app)
            self._controllers['company'] = controller
        return self._controllers['company']

    def get_users_controller(self) -> UsersController:
        """Get UsersController instance"""
        if 'users' not in self._controllers:
            controller = UsersController()
            if self.app:
                controller.init_app(self.app)
            self._controllers['users'] = controller
        return self._controllers['users']

    def get_ats_controller(self) -> ATSToolController:
        """Get ATSToolController instance"""
        if 'ats' not in self._controllers:
            controller = ATSToolController()
            if self.app:
                resume_controller = self.get_resume_controller()
                controller.init_app(self.app, resume=resume_controller)
            self._controllers['ats'] = controller
        return self._controllers['ats']

    def get_job_seeker_profile_controller(self) -> JobSeekerProfilesController:
        """Get JobSeekerProfilesController instance"""
        if 'job_seeker_profile' not in self._controllers:
            controller = JobSeekerProfilesController()
            if self.app:
                controller.init_app(self.app)
            self._controllers['job_seeker_profile'] = controller
        return self._controllers['job_seeker_profile']

    def get_employer_agents_controller(self) -> EmployerAgentsController:
        """Get EmployerAgentsController instance"""
        if 'employer_agents' not in self._controllers:
            self._controllers['employer_agents'] = EmployerAgentsController()
        return self._controllers['employer_agents']

    def get_employee_agents_controller(self) -> EmployeeAgentsController:
        """Get EmployeeAgentsController instance"""
        if 'employee_agents' not in self._controllers:
            self._controllers['employee_agents'] = EmployeeAgentsController()
        return self._controllers['employee_agents']

    def clear_cache(self):
        """Clear all cached controller instances"""
        self._controllers.clear()

    @classmethod
    def get_current(cls):
        """Get current controller factory from Flask app context"""
        from flask import current_app
        return current_app.extensions.get('controller_factory')