import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field, EmailStr, field_validator

from src.main import encryptor
from src.utils import format_reference  # assuming this is your own utility function


class Roles(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    permissions: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

    @field_validator('id')
    def format_id(cls, v):
        return format_reference("role") if v is None else v

    @field_validator('name')
    def name_must_be_alphanumeric(cls, v):
        if not re.match(r"^[a-zA-Z0-9_\- ]+$", v):
            raise ValueError("Role name must be alphanumeric with optional dashes, underscores, and spaces")
        return v


    @classmethod
    def default_roles(cls) -> List["Roles"]:
        return [
            cls(name="admin", description="System administrator with full access", permissions=["*"]),
            cls(name="employer", description="Employer who can post jobs and manage applicants", permissions=[
                "create_job", "view_applicants", "edit_job", "delete_job"
            ]),
            cls(name="seeker", description="Job seeker who can view and apply for jobs", permissions=[
                "view_jobs", "apply_job", "update_profile"
            ]),
        ]




class User(BaseModel):
    uid: str = Field(default_factory=lambda: str(uuid.uuid4()))  # Generate a default UUID if not provided
    name: str
    email: EmailStr
    password_hash: str
    role: str
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: Optional[datetime]  = Field(default_factory=lambda: datetime.now(timezone.utc))

    def __bool__(self):
        return bool(self.password_hash)

    @property
    def is_authenticated(self):
        return self.is_active

    # noinspection PyMethodParameters
    @field_validator('name')
    def name_must_be_valid(cls, v):
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v

    @field_validator('role')
    def role_must_be_valid(cls, v):
        allowed_roles = {'admin', 'employer', 'seeker'}
        if v not in allowed_roles:
            raise ValueError(f"Role must be one of {allowed_roles}")
        return v

    def check_password(self, password: str) -> bool:
        """
        :param password: Password to compare
        :return: Boolean indicating if password matches
        """
        return encryptor.compare_hashes(hash=self.password_hash, password=password)

    @classmethod
    def create(cls, name: str, email: str, password: str, role: str) -> "User":
        """
        Create a new User instance with a hashed password.
        """
        hashed = encryptor.create_hash(password)
        # noinspection PyTypeChecker
        return cls(name=name, email=email, password_hash=hashed, role=role)

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
