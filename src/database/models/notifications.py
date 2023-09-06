import uuid

from pydantic import BaseModel, Field, validator


class Notifications(BaseModel):
    email: str
    verification_id: str
    is_verified: bool = Field(default=False)
    topic: str


# noinspection PyMethodParameters
class CreateNotifications(BaseModel):
    email: str
    verification_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    is_verified: bool = Field(default=False)
    topic: str | None

    @validator("email", pre=True, always=True)
    def email_validator(cls, value):
        if isinstance(value, str):
            return value.lower()
        return value


