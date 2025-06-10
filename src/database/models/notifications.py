import uuid

from pydantic import BaseModel, Field, EmailStr


class Notifications(BaseModel):
    email: EmailStr
    verification_id: str
    is_verified: bool = Field(default=False)
    topic: str


# noinspection PyMethodParameters
class CreateNotifications(BaseModel):
    email: EmailStr
    verification_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    is_verified: bool = Field(default=False)
    topic: str | None


