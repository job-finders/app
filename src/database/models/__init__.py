from src.database.models.jobs_model import Job
from src.database.models.seo import SEO

from enum import Enum



class Role(str, Enum):
    ADMIN = "admin"
    EMPLOYER = "employer"
    SEEKER = "seeker"
    SYSTEM_ADMIN = "system_admin"



    @classmethod
    def is_valid_role(cls, role_str: str) -> bool:
        try:
            # Try to get the enum value, will raise ValueError if invalid
            cls(role_str)
            return True
        except ValueError:
            return False
