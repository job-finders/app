from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict


class PlanType(str, Enum):
    FREE = "free"
    PREMIUM = "premium"
    EMPLOYER = "employer"



class SubscriptionPlan(BaseModel):
    id: str
    name: str
    plan_type: PlanType
    description: Optional[str] = None
    monthly_price: float
    annual_price: Optional[float] = None
    features: List[str] = []
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)



class UserSubscription(BaseModel):
    id: str
    user_uid: str
    plan_id: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    is_active: bool = True
    auto_renew: bool = True

    model_config = ConfigDict(from_attributes=True)


class PaymentTransaction(BaseModel):
    id: str
    user_uid: str
    subscription_id: Optional[str] = None
    amount: float
    currency: str = "ZAR"
    status: str  # e.g. success, failed, pending
    provider: str  # e.g. PayFast, Stripe
    reference: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)


class CompanySubscription(BaseModel):
    company_id: str  # FK to company
    plan_id: Optional[str] = None
    trial_started_at: Optional[datetime] = None
    trial_days: int = 14
    subscribed: bool = False
    active_until: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

    def is_trial_active(self) -> bool:
        if not self.trial_started_at:
            return False
        return datetime.utcnow() < self.trial_started_at + timedelta(days=self.trial_days)

    def is_trial_expired(self) -> bool:
        return not self.is_trial_active() and not self.subscribed

