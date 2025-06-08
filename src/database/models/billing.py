from typing import Literal, Dict
import uuid
from datetime import date, timezone
from datetime import datetime
from decimal import Decimal
from typing import Literal
from typing import Optional

from pydantic import BaseModel, Field


class BillingPlan(BaseModel):
    """
    Represents a billing plan/subscription tier for companies.

    This model defines the various subscription plans available to companies,
    including pricing, features, and billing cycle information.

    Attributes:
        plan_id: Unique identifier for the billing plan
        name: Name of the plan (e.g., "Starter", "Growth")
        description: Optional detailed plan description
        price: Monthly cost in ZAR (as a decimal)
        currency: Currency used for the plan (default "ZAR")
        is_active: Is the plan currently available
        is_featured: Should be promoted on pricing page
        is_trial: Is this a free trial plan

        max_open_jobs: Limit on simultaneous job posts
        max_users: Limit on active users
        max_applicants_per_job: Applicant cap per job

        allow_priority_support: Premium support access
        show_branding: Show platform branding or not

        sort_order: UI ordering priority
        created_at: When plan was added
        updated_at: When plan was last changed
    """

    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None

    price: Decimal = Field(default=Decimal("0.00"))
    currency: str = Field(default="ZAR")

    is_active: bool = True
    is_featured: bool = False
    is_trial: bool = False

    max_open_jobs: Optional[int] = None
    max_users: Optional[int] = None
    max_applicants_per_job: Optional[int] = None

    allow_priority_support: bool = False
    show_branding: bool = True

    sort_order: int = 0

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class CompanyBillingProfile(BaseModel):
    """
    Tracks the billing and subscription status for a company.
    
    This model maintains the current billing state for each company,
    including their active plan, trial status, and payment information.
    
    Attributes:
        company_id: Reference to the company this billing profile belongs to
        current_plan_id: ID of the currently active billing plan
        subscription_start: Date when the current subscription began
        subscription_end: Date when the current subscription ends
        trial_active: Whether the company is currently in a trial period
        trial_end_date: When the trial period expires (if applicable)
        is_payment_overdue: Whether there are outstanding payment issues
        auto_renew: Whether the subscription should automatically renew
        last_invoice_id: Reference to the most recent invoice
    """
    company_id: str
    current_plan_id: Optional[str]
    subscription_start: Optional[date]
    subscription_end: Optional[date]
    trial_active: bool = False
    trial_end_date: Optional[date]
    is_payment_overdue: bool = False

    auto_renew: bool = True
    last_invoice_id: Optional[str]

    class Config:
        from_attributes = True

    @property
    def is_trial_valid(self):
        today = datetime.now(timezone.utc).date()
        return self.trial_active and today <= self.trial_end_date


    @property
    def active_subscription_plan_id(self) -> Optional[str]:
        """
        Returns the plan ID if the subscription is active, else None.
        """
        today = datetime.now(timezone.utc).date()

        if self.current_plan_id and self.subscription_start and self.subscription_end:
            if self.subscription_start <= today <= self.subscription_end:
                return self.current_plan_id
        return None


    @property
    def is_active_subscription_plan(self) -> bool:
        """
        Returns True if the company has an active paid subscription,
        not expired, and not in a trial.
        """
        today = datetime.now(timezone.utc).date()

        # Must have a plan and valid subscription period
        if not self.current_plan_id:
            return False

        if self.subscription_start and self.subscription_end:
            return self.subscription_start <= today <= self.subscription_end

        return False


class InvoiceStatusEnum(str):
    """
    Enumeration of possible invoice statuses.
    
    Defines the various states an invoice can be in during its lifecycle.
    """
    PENDING = "Pending"   # Invoice created but not yet paid
    PAID = "Paid"         # Invoice successfully paid
    FAILED = "Failed"     # Payment attempt failed
    CANCELED = "Canceled" # Invoice was canceled before payment


class Invoice(BaseModel):
    """
    Represents a billing invoice for a company's subscription.
    
    This model tracks individual invoices generated for companies,
    including payment status and associated billing information.
    
    Attributes:
        invoice_id: Unique identifier for the invoice
        company_id: Reference to the company being billed
        plan_id: Reference to the billing plan being invoiced
        status: Current payment status of the invoice
        amount: Total amount due on the invoice
        currency: Currency code for the invoice amount (default: USD)
        due_date: Date by which payment is expected
        paid_at: Timestamp when the invoice was paid (if applicable)
        created_at: Timestamp when the invoice was generated
    """
    invoice_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    company_id: str
    plan_id: Optional[str]
    status: InvoiceStatusEnum = InvoiceStatusEnum.PENDING
    amount: float
    currency: str = "ZAR"
    due_date: date
    paid_at: Optional[datetime]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PaymentMethod(BaseModel):
    """
    Stores payment method metadata specific to PayFast and manual processing.

    Since PayFast does not offer tokenized card storage, we use billing tokens
    and references for recurring payments.

    Attributes:
        method_id: Unique identifier for the payment method record
        company_id: Reference to the company that owns this payment method
        provider: Payment processor used ('payfast' or 'manual')
        payfast_token: Billing token from PayFast for recurring payments
        payfast_sub_reference: PayFast-generated subscription reference
        is_active: Whether this payment method is active and usable
        is_default: If this is the primary payment method for the company
        added_on: When this payment method was registered
    """
    method_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    company_id: str
    provider: Literal['payfast', 'manual'] = 'payfast'

    payfast_token: Optional[str] = None
    payfast_sub_reference: Optional[str] = None

    is_active: bool = True
    is_default: bool = True
    added_on: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BillingEvent(BaseModel):
    """
    Records billing-related lifecycle events for auditing and tracking.

    Useful for customer support, debugging payment issues, and showing
    billing history in dashboards or admin panels.

    Attributes:
        event_id: Unique ID for this billing event
        company_id: Associated company
        type: Type of billing event
        metadata: Contextual metadata (e.g., PayFast payment_id, plan_id)
        created_at: When this event was recorded
    """
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    company_id: str

    type: Literal[
        'plan_upgrade',
        'plan_downgrade',
        'trial_started',
        'trial_ended',
        'cancelled',
        'payment_failed',
        'payment_success',
        'subscription_created',
        'subscription_cancelled',
        'invoice_generated',
        'manual_payment_received'
    ]

    metadata: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

