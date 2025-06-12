from abc import abstractmethod, ABC
from enum import Enum
from typing import List, Dict, Optional

from pydantic import BaseModel, Field

from src.database.models.jobs_model import Job
from src.database.models.jobseeker_profile import JobSeekerProfile


class JobRecommenderResult(BaseModel):
    profile : JobSeekerProfile
    recommended_jobs: List[Job]

class AdminPermissionLevel(Enum):
    __doc__ = """
    Enum representing different levels of administrative access.

    These levels are used to control access to administrative features across the system,
    allowing fine-grained role-based permission enforcement.

    Members:
        VIEWER (str): Read-only access, typically used for monitoring or auditing.
        MODERATOR (str): Can perform moderation tasks such as reviewing flagged content.
        ADMIN (str): Has broader access, including managing users and content.
        SUPER_ADMIN (str): Full access, including system-level configurations and overrides.
    """
    VIEWER = "viewer"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class AdminActionResult(BaseModel):
    __doc__ = """
    Standardized structure for returning results from admin service actions.

    This object is returned by all admin services and encapsulates the outcome of
    an operation, including whether it succeeded, a user-readable message, and
    optionally any resulting data or error details.

    Attributes:
        success (bool): Indicates whether the operation was successful.
        message (str): A human-readable message describing the result.
        data (Optional[Dict]): Additional payload data from the action (e.g., a report or entity info).
        errors (Optional[List[str]]): A list of errors encountered during the operation, if any.
    """
    success: bool
    message: str
    data: Optional[Dict] = None
    list_data: Optional[list[JobRecommenderResult]] = Field(default_factory=list)
    errors: Optional[List[str]] = None


class AdminServiceInterface(ABC):
    __doc__ = """
    Abstract base class for defining administrative service interfaces.

    This interface enforces a common structure for all admin-related services,
    such as compliance checks, moderation workflows, and reporting utilities.

    Subclasses must implement the `execute()` method to define the service's
    core behavior, typically triggered via an admin command or UI action.

    Expected Usage:
        This interface should be inherited by concrete service classes like:
            - ComplianceService
            - JobModerationService
            - UserAuditTrailService
        These services should encapsulate admin operations that involve complex
        business logic, data aggregation, or multi-step workflows.

    Dependencies:
        - AdminActionResult: A standardized result wrapper used by all admin services
          to return success/failure status, messages, and optional payloads.

    Side Effects:
        - Implementation-dependent (e.g., may include DB writes, external API calls, or
          real-time notifications, depending on subclass implementation).

    Methods:
        execute(*args, **kwargs)
            Abstract method to be implemented by subclasses.

            Args:
                *args: Positional arguments specific to the implementing service.
                **kwargs: Keyword arguments required for execution logic.

            Returns:
                AdminActionResult: Structured result indicating the outcome of the operation.

            Raises:
                NotImplementedError: If called directly from the interface without subclass implementation.
    """

    @abstractmethod
    def execute(self, *args, **kwargs) -> AdminActionResult:
        """
        Execute the main logic of the admin service.

        :param args: Variable positional arguments specific to the implementing class.
        :param kwargs: Keyword arguments required for executing the admin operation.
        :return: AdminActionResult containing success status, message, and optional data.
        :rtype: AdminActionResult
        :raises NotImplementedError: If the method is not implemented by a subclass.
        """
        pass
