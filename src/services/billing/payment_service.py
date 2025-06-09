import inspect

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
    async def execute(self, action: str, *args, **kwargs):
        """
        Dynamically executes a method based on the provided action name.

        Args:
            action (str): The name of the method to execute (must be present in `_interface_schema`).
            *args: Positional arguments for the method.
            **kwargs: Keyword arguments for the method.

        Returns:
            Any: The result of the invoked method.

        Raises:
            ValueError: If the action does not exist in this service's schema
                        or if the found entry is not a callable method.
            RuntimeError: If an unexpected error occurs during the execution
                          of the target method.
        """
        try:
            method_to_execute = self.__interface_map[action]

            if method_to_execute is None:
                raise ValueError(f"Action '{action}' not found in {self.__class__.__name__}.")

            if inspect.iscoroutinefunction(method_to_execute):
                return await method_to_execute(*args, **kwargs)
            else:
                return method_to_execute(*args, **kwargs)

        # Catch specific exceptions that might be raised by the lookup or the method itself.
        except ValueError as e:
            # Re-raise the ValueError if it's one of the ones we explicitly raised.
            raise e

        except Exception as e:
            # Catch any other unexpected exceptions and wrap them in a RuntimeError.
            # Using 'from e' maintains the original exception's traceback, which is crucial for debugging.
            raise RuntimeError(f"Error executing action '{action}': {str(e)}") from e

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

    async def _generate_payfast_form(self, invoice: InvoiceORM,
                                     company):  # Removed Company type hint as it's not defined
        """
        Generates the PayFast payment form for the given invoice and company.

        Args:
            invoice (InvoiceORM): The invoice to generate the form for.
            company (Any): The company making the payment.

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
        is_verified = await self.payfast_client.verify_ipn(data=data)
        # There is a Need to verify this step i could be processing this on the route
        #
        # if is_verified:
        #     # Assuming 'custom_str1' from PayFast contains the invoice_id
        #     invoice_id = data.get('custom_str1')
        #     if invoice_id:
        #         # Mark invoice as paid
        #         invoice_service = InvoiceService(self.session_factory)  # Create an instance
        #         updated_invoice = await invoice_service.execute("mark_invoice_paid", invoice_id=invoice_id)
        #         return {"status": "success", "invoice": updated_invoice.to_dict(),
        #                 "message": "ITN processed and invoice marked paid."}
        #     else:
        #         return {"status": "error", "message": "Invoice ID not found in ITN data."}
        # else:
        #     return {"status": "error", "message": "ITN verification failed."}
        #
        #
