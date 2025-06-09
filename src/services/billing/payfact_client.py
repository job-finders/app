import hashlib
import urllib.parse
import asyncio
import httpx

from src.utils.route_helpers import get_service


class PayFastClient:
    def __init__(self, settings):
        self.merchant_id = settings.MERCHANT_ID
        self.merchant_key = settings.MERCHANT_KEY
        self.passphrase = settings.PASS_PHRASE
        self.sandbox = settings.SANDBOX

        self.return_url = "https://yourapp.com/payment/success"  # could be dynamic
        self.cancel_url = "https://yourapp.com/payment/cancel"
        self.notify_url = "https://yourapp.com/payment/ipn"

        self.logger = get_service("logger")()(self.__class__.__name__)
        self.base_url = (
            "https://sandbox.payfast.co.za/eng/process"
            if self.sandbox else "https://www.payfast.co.za/eng/process"
        )

    def _generate_signature(self, data: dict) -> str:
        """
        Generates a PayFast signature according to their rules.
        """
        sorted_data = {k: v for k, v in sorted(data.items()) if v}
        encoded = urllib.parse.urlencode(sorted_data)
        if self.passphrase:
            encoded += f"&passphrase={urllib.parse.quote_plus(self.passphrase)}"
        return hashlib.md5(encoded.encode("utf-8")).hexdigest()

    def create_payment_data(self, invoice):
        """
        Constructs payment data for a given invoice.
        """
        data = {
            "merchant_id": self.merchant_id,
            "merchant_key": self.merchant_key,
            "return_url": self.return_url,
            "cancel_url": self.cancel_url,
            "notify_url": self.notify_url,
            "amount": f"{invoice.amount:.2f}",
            "item_name": f"Invoice #{invoice.invoice_id}",
            "custom_str1": invoice.invoice_id,
        }
        data["signature"] = self._generate_signature(data)
        return data

    def get_payment_url(self, invoice):
        """
        Returns the full redirect URL to PayFast with signed payment data.
        """
        data = self.create_payment_data(invoice)
        return f"{self.base_url}?{urllib.parse.urlencode(data)}"

    async def verify_ipn(self, ipn_data: dict) -> bool:
        """
        Verifies that the IPN came from PayFast.
        """
        # Step 1: Check signature matches
        received_signature = ipn_data.pop("signature", "")
        calculated_signature = self._generate_signature(ipn_data)
        if received_signature != calculated_signature:
            return False

        # Step 2: Confirm IPN with PayFast
        # Mocking the httpx call
        self.logger.info("Mocking PayFast IPN verification request...")
        await asyncio.sleep(0.1)  # Simulate network call
        # In a real scenario:
        async with httpx.AsyncClient() as client:
           headers = {"Content-Type": "application/x-www-form-urlencoded"}
           payload = urllib.parse.urlencode(ipn_data)
           results = await client.post("https://www.payfast.co.za/eng/query/validate", headers=headers, content=payload)
        return results.text == "VALID" # PayFast sends "VALID" or "INVALID"

    async def generate_payment_form(self, invoice, company):
        """Mock method for generating payment form data."""
        self.logger.info(f"Mock PayFast Client: Generating form for invoice {invoice.invoice_id}")
        return self.create_payment_data(invoice)  # Reuse create_payment_data
