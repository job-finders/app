
from urllib.parse import urlencode
import hashlib

class PayFastSubscription(BaseModel):
    subscription_id: str  # PayFast token or subscription reference
    company_id: str
    plan_id: str
    is_active: bool = True
    started_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    last_payment_date: Optional[datetime] = None

class Invoice(BaseModel):
    invoice_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    company_id: str
    plan_id: str
    amount: float
    currency: str = "ZAR"
    status: str = "pending"  # paid, failed, canceled
    created_at: datetime = Field(default_factory=utc_time)
    paid_at: Optional[datetime] = None
    payfast_ref: Optional[str] = None

from urllib.parse import urlencode
import hashlib

def generate_payfast_subscription_url(company, plan, billing_profile):
    data = {
        "merchant_id": PAYFAST_MERCHANT_ID,
        "merchant_key": PAYFAST_MERCHANT_KEY,
        "return_url": PAYFAST_RETURN_URL,
        "cancel_url": PAYFAST_CANCEL_URL,
        "notify_url": PAYFAST_NOTIFY_URL,
        "amount": f"{plan.price:.2f}",
        "item_name": plan.name,
        "name_first": company.admin_name,
        "email_address": company.admin_email,
        "subscription_type": 1,
        "billing_date": datetime.now().strftime("%Y-%m-%d"),
        "recurring_amount": f"{plan.price:.2f}",
        "frequency": 3,  # Monthly
        "cycles": 0,  # 0 = indefinite
    }

    # Generate signature
    query_string = urlencode(data)
    if PAYFAST_PASSPHRASE:
        query_string += f"&passphrase={PAYFAST_PASSPHRASE}"
    signature = hashlib.md5(query_string.encode()).hexdigest()
    data["signature"] = signature

    payfast_url = "https://sandbox.payfast.co.za/eng/process" if PAYFAST_SANDBOX else "https://www.payfast.co.za/eng/process"
    return f"{payfast_url}?{urlencode(data)}"


