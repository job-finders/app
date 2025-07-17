from enum import Enum
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Union
import uuid
from datetime import datetime

class NotificationChannel(str, Enum):
    email = "email"
    sms = "sms"
    in_app = "in_app"

class NotificationType(str, Enum):
    email_verification = "email_verification"
    job_alert = "job_alert"
    applicant_applied = "applicant_applied"

class NotificationPayload(BaseModel):
    # Generic payload, interpreted by the channel-specific sender
    subject: Optional[str] = None
    body: Optional[str] = None
    data: dict = {}

class BaseNotification(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    company_id: Optional[str] = None
    email: Optional[EmailStr] = None
    notification_type: NotificationType
    channel: NotificationChannel
    payload: NotificationPayload
    is_sent: bool = False
    sent_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
