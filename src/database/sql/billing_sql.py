import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Boolean, Integer, Numeric, Text, DateTime, func, JSON, Date, inspect
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

from src.database.constants import ID_LEN
from src.database.constants import utc_time
from src.database.sql import Base, engine


class BillingPlanORM(Base):
    __tablename__ = "billing_plan"

    plan_id = Column(String(ID_LEN), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    price = Column(Numeric(10, 2), nullable=False, default=0.00)  # Price in ZAR
    currency = Column(String(10), default="ZAR")  # Defaulted for PayFast usage
    duration_days = Column(Integer, default=30)  # Default duration for the plan in days

    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    is_trial = Column(Boolean, default=False)

    max_open_jobs = Column(Integer, nullable=True)       # None = unlimited
    max_users = Column(Integer, nullable=True)
    max_applicants_per_job = Column(Integer, nullable=True)

    allow_priority_support = Column(Boolean, default=False)
    show_branding = Column(Boolean, default=True)

    sort_order = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    invoices = relationship("InvoiceORM", back_populates="billing_plan")
    billing_profiles = relationship("CompanyBillingProfileORM", back_populates="billing_plan")

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            # noinspection PyUnresolvedReferences
            cls.__table__.create(bind=engine)

    # noinspection PyUnresolvedReferences
    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)


    def to_dict(self, include_relationships: bool = False) -> dict:
        return {
            "plan_id": self.plan_id,
            "name": self.name,
            "description": self.description,
            "price": float(self.price),
            "currency": self.currency,
            "is_active": self.is_active,
            "is_featured": self.is_featured,
            "is_trial": self.is_trial,
            "max_open_jobs": self.max_open_jobs,
            "max_users": self.max_users,
            "max_applicants_per_job": self.max_applicants_per_job,
            "allow_priority_support": self.allow_priority_support,
            "show_branding": self.show_branding,
            "sort_order": self.sort_order,
            "created_at": self.created_at.replace(tzinfo=timezone.utc).isoformat() if self.created_at else None,
            "updated_at": self.updated_at.replace(tzinfo=timezone.utc).isoformat() if self.updated_at else None,
            "invoices": [invoice.to_dict() for invoice in
                         self.invoices] if include_relationships and self.invoices else [],
            "billing_profiles": [profile.to_dict() for profile in self.billing_profiles
                                 if profile] if include_relationships and self.billing_profiles else [],
        }

class CompanyBillingProfileORM(Base):
    __tablename__ = "company_billing"
    subscription_id = Column(String(ID_LEN), primary_key=True, index=True)
    company_id = Column(String(ID_LEN), ForeignKey('companies.company_id'), index=True)
    current_plan_id = Column(String(ID_LEN), ForeignKey('billing_plan.plan_id') , index=True)
    subscription_start = Column(Date, nullable=True, default=None)
    subscription_end = Column(Date, nullable=True, default=None)
    trial_active = Column(Boolean, default=True)
    trial_end_date = Column(Date, nullable=True)
    is_payment_overdue = Column(Boolean, default=False)

    auto_renew = Column(Boolean, default=True)
    last_invoice_id = Column(String(ID_LEN), nullable=True)
    invoices = relationship("InvoiceORM", back_populates="billing_profile")
    billing_plan = relationship("BillingPlanORM", back_populates="billing_profiles")

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            # noinspection PyUnresolvedReferences
            cls.__table__.create(bind=engine)

    # noinspection PyUnresolvedReferences
    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

    def to_dict(self, include_relationships: bool = False) -> dict:
        return {
            "subscription_id": self.subscription_id,
            "company_id": self.company_id,
            "current_plan_id": self.current_plan_id,
            "subscription_start": self.subscription_start if self.subscription_start else None,
            "subscription_end": self.subscription_end if self.subscription_end else None,
            "trial_active": self.trial_active,
            "trial_end_date": self.trial_end_date if self.trial_end_date else None,
            "is_payment_overdue": self.is_payment_overdue,
            "auto_renew": self.auto_renew,
            "last_invoice_id": self.last_invoice_id,
            "invoices": [invoice.to_dict() for invoice in
                         self.invoices] if include_relationships and self.invoices else [],
            "billing_plan": self.billing_plan.to_dict() if include_relationships else None
        }

# Assuming this enum is already defined elsewhere
class InvoiceStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"

class InvoiceORM(Base):
    __tablename__ = "invoice"

    invoice_id = Column(String(ID_LEN), primary_key=True, index=True)
    subscription_id = Column(String(ID_LEN), ForeignKey("company_billing.subscription_id"), nullable=False)
    plan_id = Column(String(ID_LEN), ForeignKey("billing_plan.plan_id"), nullable=False)
    company_id = Column(String(ID_LEN), nullable=False)

    status = Column(String(36), default=InvoiceStatusEnum.PENDING.value, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), default="ZAR", nullable=False)

    due_date = Column(Date, nullable=False)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_time())

    # Optional relationships
    billing_profile = relationship("CompanyBillingProfileORM", back_populates="invoices")
    billing_plan = relationship("BillingPlanORM", back_populates="invoices")

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            # noinspection PyUnresolvedReferences
            cls.__table__.create(bind=engine)

    # noinspection PyUnresolvedReferences
    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

    def to_dict(self, include_relationships: bool = False) -> dict:
        return {
            "invoice_id": self.invoice_id,
            "subscription_id": self.subscription_id,
            "plan_id": self.plan_id,
            "company_id": self.company_id,
            "status": self.status if self.status else None,
            "amount": float(self.amount),
            "currency": self.currency,
            "due_date": self.due_date if self.due_date else None,
            "paid_at": self.paid_at.replace(tzinfo=timezone.utc).isoformat() if self.paid_at else None,
            "created_at": self.created_at.replace(tzinfo=timezone.utc).isoformat() if self.created_at else None,
            "billing_profile": self.billing_profile.to_dict() if include_relationships and self.billing_profile else None,
            "billing_plan": self.billing_plan.to_dict() if include_relationships and self.billing_plan else None
        }

class PaymentMethodORM(Base):
    __tablename__ = "payment_methods"

    method_id = Column(String(ID_LEN), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String(ID_LEN), ForeignKey("companies.company_id"), nullable=False)  # changed
    

    provider = Column(String(20), default="payfast")  # 'payfast' or 'manual'
    payfast_token = Column(String(255), nullable=True)
    payfast_sub_reference = Column(String(255), nullable=True)

    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=True)

    added_on = Column(DateTime(timezone=True), default=utc_time())

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            # noinspection PyUnresolvedReferences
            cls.__table__.create(bind=engine)

    # noinspection PyUnresolvedReferences
    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

    def to_dict(self):
        return {
            "method_id": self.method_id,
            "company_id": self.company_id,
            "provider": self.provider,
            "payfast_token": self.payfast_token,
            "payfast_sub_reference": self.payfast_sub_reference,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "added_on": self.added_on.replace(tzinfo=timezone.utc)
        }

class BillingEventORM(Base):
    __tablename__ = "billing_events"

    event_id = Column(String(ID_LEN), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String(ID_LEN), ForeignKey("companies.company_id"), nullable=False)
    subscription_id = Column(String(ID_LEN), ForeignKey("company_billing.subscription_id"))

    event_type = Column(String(50), nullable=False)  # Use Enum if you prefer strict validation
    event_metadata = Column(JSON, default=dict)
    email_sent = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_time(), index=True)

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            # noinspection PyUnresolvedReferences
            cls.__table__.create(bind=engine)

    # noinspection PyUnresolvedReferences
    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

    def to_dict(self):
        return {
            "event_id": self.event_id,
            "company_id": self.company_id,
            "subscription_id": self.subscription_id,
            "email_sent": self.email_sent,
            "event_type": self.event_type,
            "event_metadata": self.event_metadata,
            "created_at": self.created_at.replace(tzinfo=timezone.utc).isoformat()
        }
