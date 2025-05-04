from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


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
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "from_attributes": True
    }


class UserSubscription(BaseModel):
    id: str
    user_uid: str
    plan_id: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    is_active: bool = True
    auto_renew: bool = True

    model_config = {
        "from_attributes": True
    }


class PaymentTransaction(BaseModel):
    id: str
    user_uid: str
    subscription_id: Optional[str] = None
    amount: float
    currency: str = "ZAR"
    status: str  # e.g. success, failed, pending
    provider: str  # e.g. PayFast, Stripe
    reference: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "from_attributes": True
    }


