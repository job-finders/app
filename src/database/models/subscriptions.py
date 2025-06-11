from datetime import timedelta
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict, AwareDatetime

from database.constants import utc_time


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
    created_at: AwareDatetime = Field(default_factory=utc_time)

    model_config = ConfigDict(from_attributes=True)



class UserSubscription(BaseModel):
    id: str
    user_uid: str
    plan_id: str
    started_at: AwareDatetime = Field(default_factory=utc_time)
    expires_at: Optional[AwareDatetime] = Field(default=None)
    is_active: bool = Field(default=True)
    auto_renew: bool = Field(default=True)

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
    timestamp: AwareDatetime = Field(default_factory=utc_time)

    model_config = ConfigDict(from_attributes=True)


class CompanySubscription(BaseModel):
    company_id: str  # FK to company
    plan_id: Optional[str] = Field(default=None)
    trial_started_at: Optional[AwareDatetime] = Field(default=None)
    trial_days: int = Field(default=14)
    subscribed: bool = Field(default=False)
    active_until: Optional[AwareDatetime] = Field(default=None)
    model_config = ConfigDict(from_attributes=True)

    def is_trial_active(self) -> bool:
        if not self.trial_started_at:
            return False
        return utc_time() < self.trial_started_at + timedelta(days=self.trial_days)

    def is_trial_expired(self) -> bool:
        return not self.is_trial_active() and not self.subscribed

