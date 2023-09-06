import uuid

from pydantic import BaseModel, Field


class Notifications(BaseModel):
    email: str
    verification_id: str
    is_verified: bool = Field(default=False)


class CreateNotifications(BaseModel):
    email: str
    verification_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    is_verified: bool = Field(default=False)
