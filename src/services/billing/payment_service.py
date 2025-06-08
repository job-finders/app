from src.database.sql.billing_sql import InvoiceORM
from src.services.billing.schemas_interfaces import BillingServiceInterface


class PaymentService(BillingServiceInterface):
    """
    Handles all payment processing integrations (PayFast, manual) and payment status updates.
    """

    def __init__(self, session_factory, payment_client):
        super().__init__()
        self.session_factory = session_factory
        self.payfast_client = payment_client  # Could be a requests wrapper or webhook listener
        self.__interface_map = {
            "interface_schema": self._interface_schema,
            "describe_actions": self._describe_actions,
            "generate_payfast_form": self._generate_payfast_form,
            "process_itn": self._process_itn,
            "process_payment": self._process_payment
        }

    async def _process_payment(self, invoice_id: str) -> dict:
        """
        Initiates the payment process for a given invoice by generating a PayFast payment URL.

        Args:
            invoice_id (str): The ID of the invoice to process payment for.

        Returns:
            dict: A dictionary containing invoice info and a redirect URL to PayFast.

        Raises:
            ValueError: If the invoice doesn't exist.
        """
        with self.session_factory() as session:
            invoice = session.query(InvoiceORM).filter_by(invoice_id=invoice_id).first()

            if not invoice:
                raise ValueError("Invoice not found")

            # Use the PayFast client to generate the payment URL
            payment_url = self.payfast_client.get_payment_url(invoice)

            return {
                "invoice_id": invoice.invoice_id,
                "status": invoice.status,
                "amount": float(invoice.amount),
                "currency": invoice.currency,
                "redirect_url": payment_url
            }

    async def _generate_payfast_form(self, invoice: InvoiceORM, company):
        """
        Generates the PayFast payment form for the given invoice and company.

        Args:
            invoice (InvoiceORM): The invoice to generate the form for.
            company (Company): The company making the payment.

        Returns:
            dict: A dictionary containing the PayFast form data.
        """
        return await self.payfast_client.generate_payment_form(invoice, company)

    async def _process_itn(self, data: dict):
        """
        Processes the Instant Transaction Notification (ITN) from PayFast.

        Args:
            data (dict): The ITN data received from PayFast.

        Returns:
            dict: Result of the ITN processing, including payment status and invoice details.
        """
        return await self.payfast_client.verify_ipn(data=data)
