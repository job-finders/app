# billing.py Documentation

## Overview

This module defines Pydantic models for managing billing and subscription information for companies. It includes models for billing plans, company billing profiles, invoices, and payment methods.

## Models

### BillingPlan

Represents a billing plan/subscription tier for companies.

*   `plan_id`: Unique identifier for the billing plan (UUID).
*   `name`: Name of the plan (e.g., "Starter", "Growth").
*   `description`: Optional detailed plan description.
*   `price`: Monthly cost in ZAR (as a decimal).
*   `currency`: Currency used for the plan (default "ZAR").
*   `is_active`: Indicates whether the plan is currently available.
*   `is_featured`: Indicates whether the plan should be promoted on the pricing page.
*   `is_trial`: Indicates whether this is a free trial plan.
*   `max_open_jobs`: Limit on simultaneous job posts.
*   `max_users`: Limit on active users.
*   `max_applicants_per_job`: Applicant cap per job.
*   `allow_priority_support`: Indicates whether premium support access is allowed.
*   `show_branding`: Indicates whether platform branding should be shown or not.
*   `sort_order`: UI ordering priority.
*   `created_at`: The date and time the plan was created.
*   `updated_at`: The date and time the plan was last updated.
    *   `duration_days`: duration of the billing period

### CompanyBillingProfile

Tracks the billing and subscription status for a company.

*   `subscription_id`: Unique identifier for the subscription (UUID).
*   `company_id`: Reference to the company this billing profile belongs to.
*   `current_plan_id`: ID of the currently active billing plan.
*   `subscription_start`: Date when the current subscription began.
*   `subscription_end`: Date when the current subscription ends.
*   `trial_active`: Indicates whether the company is currently in a trial period.
*   `trial_end_date`: When the trial period expires (if applicable).
*   `is_payment_overdue`: Indicates whether there are outstanding payment issues.
*   `auto_renew`: Indicates whether the subscription should automatically renew.
*   `last_invoice_id`: Reference to the most recent invoice.

### InvoiceStatusEnum

An enumeration of possible invoice statuses:

*   `PENDING`: Invoice created but not yet paid.
*   `PAID`: Invoice successfully paid.
*   `FAILED`: Payment attempt failed.
*   `CANCELED`: Invoice was canceled before payment.
*   `CLOSED`: Invoice paid and finalized.

### Invoice

Represents a billing invoice for a company's subscription.

*   `invoice_id`: Unique identifier for the invoice (UUID).
*   `company_id`: Reference to the company being billed.
*   `subscription_id`: reference to the company's subscription
*   `plan_id`: Reference to the billing plan being invoiced.
*   `status`: Current payment status of the invoice (from `InvoiceStatusEnum`).
*   `amount`: Total amount due on the invoice.
*   `currency`: Currency code for the invoice amount (default: USD).
*   `due_date`: Date by which payment is expected.
*   `paid_at`: Timestamp when the invoice was paid (if applicable).
*   `created_at`: Timestamp when the invoice was generated.

### PaymentMethod

Stores payment method metadata specific to PayFast and manual processing.

*   `method_id`: Unique identifier for the payment method record (UUID).
*   `company_id`: Reference to the company that owns this payment method.
*   `provider`: Payment processor used ('payfast' or 'manual').
*   `payfast_token`: Billing token from PayFast for recurring payments.
*   `payfast_sub_reference`: PayFast-generated subscription reference.
*   `is_active`: Indicates whether this payment method is active and usable.
*   `is_default`: Indicates whether this is the primary payment method for the company.
*   `added_on`: When this payment method was registered.

### BillingEvent

Records billing-related lifecycle events for auditing and tracking.

*   `event_id`: Unique ID for this billing event (UUID).
*   `company_id`: Associated company.
*   `type`: Type of billing event.
*   `metadata`: Contextual metadata (e.g., PayFast payment_id, plan_id).
*   `created_at`: When this event was recorded.

## Relationships to SQL Models

This model corresponds to the following SQL models:

*   [`BillingPlanORM`](src/database/sql/billing_sql.py:14)
*   [`CompanyBillingProfileORM`](src/database/sql/billing_sql.py:81)
*   [`InvoiceORM`](src/database/sql/billing_sql.py:134)
*   [`PaymentMethodORM`](src/database/sql/billing_sql.py:182)
*   [`BillingEventORM`](src/database/sql/billing_sql.py:221)

The Pydantic models map directly to their corresponding ORM models in `src/database/sql/billing_sql.py`.