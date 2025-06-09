from datetime import datetime, timezone
from typing import Any

from flask import render_template

from src.emailer import EmailModel
from src.services.billing.schemas_interfaces import BillingEventType, BillingServiceInterface


# --- Billing Emailer Service ---
class BillingEmailerService(BillingServiceInterface):
    """
    Responsible for composing billing-related emails and sending them via the queue.
    """

    def __init__(self, company_repo, email_queue):
        super().__init__()
        self.company_repo = company_repo
        self.email_queue = email_queue
        self.__interface_map = {
            "send": self.send
        }

    async def send(self, event_type: BillingEventType, company_id: str, metadata: dict) -> bool:
        """
        Entry point to send a billing-related email.

        Args:
            event_type (BillingEventType): Type of the billing event (e.g., BillingEventType.PAYMENT_SUCCESS).
            company_id (str): ID of the company receiving the email.
            metadata (dict): Additional event-specific info (e.g., invoice number, plan, dates).

        Returns:
            bool: True if the email was successfully composed and sent to the queue, False otherwise.
        """
        # company_controller = get_controller("company") # No longer needed, directly use company_repo
        company = await self.company_repo.get_company(company_id)
        if not company:
            self.logger.info(f"BillingEmailerService: Company not found for {company_id}. Cannot send email.")
            return False  # Indicate failure

        recipient_email = company.billing_email or company.admin_email
        if not recipient_email:
            self.logger.info(f"BillingEmailerService: No recipient email found for company {company_id}.")
            return False  # Indicate failure

        try:
            subject, html_content = self._compose_email(event_type, company, metadata)
        except ValueError as e:
            self.logger.info(f"BillingEmailerService: Failed to compose email for event {event_type.value}: {e}")
            return False  # Indicate failure

        email = EmailModel(
            to_=recipient_email,
            subject_=subject,
            html_=html_content,
        )
        self.email_queue.send_to_queue(item=email.model_dump())
        self.logger.info(f"BillingEmailerService: Email for {event_type.value} sent to queue for {company_id}.")
        return True  # Indicate success

    def _compose_email(self, event_type: BillingEventType, company: Any, metadata: dict) -> tuple[str, str]:
        """
        Composes the email subject and HTML content based on the event type.

        Args:
            event_type (BillingEventType): The type of billing event.
            company (Any): The company object with relevant details.
            metadata (dict): Additional event-specific metadata.

        Returns:
            tuple[str, str]: A tuple containing the email subject and HTML content.

        Raises:
            ValueError: If an unsupported email event type is provided.
        """
        # Use event_type.value to match against the string values defined in the Enum
        match event_type:
            case BillingEventType.PAYMENT_SUCCESS:
                subject = f"Payment Received for Invoice #{metadata.get('invoice_id')}"
                html = render_template("email/payment_success.html", **{
                    "company": company,
                    "invoice_id": metadata.get("invoice_id"),
                    "amount": metadata.get("amount"),
                    "date": metadata.get("paid_at")
                })
            case BillingEventType.SUBSCRIPTION_EXPIRING_SOON:  # Changed from "trial_expiring"
                subject = f"Your Subscription is Ending Soon"
                html = render_template("email/trial_expiring.html", **{  # Re-using template name for mock
                    "company": company,
                    "days_left": metadata.get("days_left", 3)
                })
            case BillingEventType.INVOICE_CLOSED:  # Changed from "invoice_generated" to reflect existing enum
                subject = f"Invoice {metadata.get('invoice_id')} Has Been Closed"
                html = render_template("email/invoice_generated.html", **{  # Re-using template name for mock
                    "company": company,
                    "invoice_id": metadata.get("invoice_id"),
                    "amount": metadata.get("amount"),  # Invoice close might not have amount directly
                    "date": datetime.now(timezone.utc).strftime("%Y-%m-%d")  # Use current date for closed confirmation
                })
            case BillingEventType.TRIAL_STARTED:  # Added to compose for trial start
                subject = f"Welcome! Your Trial Has Started"
                html = render_template("email/trial_started.html", **{  # New mock template
                    "company": company,
                    "duration_days": metadata.get("duration_days")
                })
            case BillingEventType.TRIAL_ENDED:  # Added to compose for trial ended
                subject = f"Your Trial Has Ended"
                html = render_template("email/trial_ended.html", **{  # New mock template
                    "company": company,
                    "reason": metadata.get("reason", "expired")
                })
            case BillingEventType.SUBSCRIPTION_CREATED:  # Added for new subscription
                subject = f"Your Subscription is Now Active!"
                html = render_template("email/subscription_created.html", **{  # New mock template
                    "company": company,
                    "plan_id": metadata.get("plan_id"),
                    "subscription_end": metadata.get("subscription_end")
                })
            case BillingEventType.SUBSCRIPTION_EXPIRED:  # Added for expired subscription (full expiry)
                subject = f"Your Subscription Has Expired"
                html = render_template("email/subscription_expired.html", **{  # New mock template
                    "company": company,
                    "reason": metadata.get("reason", "expired")
                })
            case BillingEventType.BILLING_PROFILE_MISSING:  # Added for missing profile alerts (internal or external)
                subject = f"Action Required: Billing Profile Missing for {company.company_id}"
                html = render_template("email/billing_profile_missing.html", **{  # New mock template
                    "company": company
                })
            case BillingEventType.EMAIL_SEND_FAILED:  # Added for internal alert
                subject = f"ALERT: Failed to Send Billing Email for {company.company_id}"
                html = render_template("email/email_send_failed.html", **{  # New mock template
                    "company": company,
                    "original_event_id": metadata.get("event_id"),
                    "error_message": metadata.get("error")
                })
            case _:
                raise ValueError(f"Unsupported email event type: {event_type.value}")

        return subject, html
