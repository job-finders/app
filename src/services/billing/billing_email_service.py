from flask import render_template

from src.emailer import EmailModel

from src.utils.route_helpers import get_controller
from src.factories.redis_factory import email_queue


class BillingEmailerService:
    """
    Responsible for composing billing-related emails and sending them via the queue.
    """

    def __init__(self):
        pass

    async def send(self, event_type: str, company_id: str, metadata: dict):
        """
        Entry point to send a billing-related email.

        :param event_type: Type of the billing event (e.g., "payment_success", "trial_expiring")
        :param company_id: ID of the company receiving the email
        :param metadata: Additional event-specific info (e.g., invoice number, plan, dates)
        """
        company_controller = get_controller("company")
        company = await self.company_repo.get_company(company_id)
        if not company:
            raise ValueError(f"Company not found: {company_id}")

        recipient_email = company.billing_email or company.admin_email
        subject, html_content = self._compose_email(event_type, company, metadata)

        email = EmailModel(
            to_=recipient_email,
            subject_=subject,
            html_=html_content,
        )
        email_queue.send_to_queue(item=email.model_dump())
        # enqueue_email(email)

    def _compose_email(self, event_type: str, company, metadata: dict) -> tuple[str, str]:
        """
        Returns (subject, html_body) for the email
        """
        match event_type:
            case "payment_success":
                subject = f"Payment Received for Invoice #{metadata.get('invoice_id')}"
                html = render_template("email/payment_success.html", **{
                    "company": company,
                    "invoice_id": metadata.get("invoice_id"),
                    "amount": metadata.get("amount"),
                    "date": metadata.get("paid_at")
                })
            case "trial_expiring":
                subject = f"Your Trial is Ending Soon"
                html = render_template("email/trial_expiring.html", **{
                    "company": company,
                    "days_left": metadata.get("days_left", 3)
                })
            case "invoice_generated":
                subject = f"New Invoice Generated"
                html = render_template("email/invoice_generated.html", **{
                    "company": company,
                    "invoice_id": metadata.get("invoice_id"),
                    "amount": metadata.get("amount"),
                    "due_date": metadata.get("due_date")
                })
            case _:
                raise ValueError(f"Unsupported email event type: {event_type}")

        return subject, html
