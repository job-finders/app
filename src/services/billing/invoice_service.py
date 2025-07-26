# Standard Library
import inspect
from datetime import datetime, timedelta, timezone
from typing import Callable, List, get_type_hints
# Domain Models
from src.database.models import CompanyBillingProfile, InvoiceStatusEnum, BillingPlan, Invoice
# SQL Models
from src.database.sql.billing_sql import InvoiceORM, CompanyBillingProfileORM
# Services
from src.services.billing.schemas_interfaces import BillingServiceInterface, MethodSchema

class InvoiceService(BillingServiceInterface):
    """
    Responsible for generating, retrieving and updating invoice records.
    """

    def __init__(self, session_factory):
        super().__init__()
        self.session_factory = session_factory
        self.__interface_map: dict[str, Callable] = {
            "interface_schema": self._interface_schema,
            "describe_actions": self._describe_actions,
            "create_invoice": self._create_invoice,
            "get_latest_invoice": self._get_latest_invoice,
            "get_invoice_by_id": self._get_invoice_by_id,
            "mark_invoice_paid": self._mark_invoice_paid,
            "list_company_invoices": self._list_company_invoices,
            "delete_invoice": self._delete_invoice,
            "update_invoice_status": self._update_invoice_status,
            "update_last_invoice_id": self._update_last_invoice_id,
            "get_paid_invoices": self._get_paid_invoices,  # Added for cron service usage
            "get_unpaid_invoices": self._get_unpaid_invoices,  # Added for cron service usage
            "close_invoice": self._close_invoice,  # Added for cron service usage
        }
        # Added _get_paid_invoices for cron service
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
            is_coroutine = inspect.iscoroutinefunction(method_to_execute)
            return await method_to_execute(*args, **kwargs) if is_coroutine else method_to_execute(*args, **kwargs)
        # Catch specific exceptions that might be raised by the lookup or the method itself.
        except (ValueError, KeyError) as e:
            # Re-raise the ValueError if it's one of the ones we explicitly raised.
            raise e
        except Exception as e:
            # Catch any other unexpected exceptions and wrap them in a RuntimeError.
            # Using 'from e' maintains the original exception's traceback, which is crucial for debugging.
            raise RuntimeError(f"Error executing action '{action}' Resultant Error : {str(e)}") from e

    async def _get_paid_invoices(self, company_id: str) -> List[Invoice]:
        with self.session_factory() as session:
            invoices_orm = (
                session.query(InvoiceORM)
                .filter_by(company_id=company_id, status=InvoiceStatusEnum.PAID.value)
                .order_by(InvoiceORM.created_at.desc())
                .all()
            )
            return [Invoice(**inv.to_dict()) for inv in invoices_orm]

        # Added _close_invoice for cron service

    async def _get_unpaid_invoices(self, company_id: str) -> List[Invoice]:
        with self.session_factory() as session:
            invoices_orm = (
                session.query(InvoiceORM)
                .filter_by(company_id=company_id, status=InvoiceStatusEnum.PENDING.value)
                .order_by(InvoiceORM.created_at.desc())
                .all()
            )
            return [Invoice(**inv.to_dict()) for inv in invoices_orm]

        # Added _close_invoice for cron service
    async def _close_invoice(self, invoice_id: str):
        with self.session_factory() as session:
            invoice_orm = session.query(InvoiceORM).filter_by(invoice_id=invoice_id).first()
            if not invoice_orm:
                raise ValueError("Invoice not found")
            invoice_orm.status = InvoiceStatusEnum.CLOSED.value  # Assuming CLOSED is a valid status
            session.commit()
            session.refresh(invoice_orm)
            return Invoice(**invoice_orm.to_dict())

    async def _create_invoice(self, billing_profile: CompanyBillingProfile, plan: BillingPlan,
                              subscription_id: str = None):
        with self.session_factory() as session:
            today = datetime.now(timezone.utc)
            amount = float(plan.price) if not billing_profile.is_trial_valid else 0.0
            due_date = today + timedelta(days=7)

            invoice_subscription_id = subscription_id or billing_profile.billing_profile_id
            if not invoice_subscription_id:
                raise ValueError("No valid subscription_id available")

            self.logger.info(f"Billing Plan ID : {plan.plan_id}, Subscription ID: {invoice_subscription_id}")
            invoice = Invoice(
                company_id=billing_profile.company_id,
                plan_id=plan.plan_id,
                subscription_id=invoice_subscription_id,
                amount=amount,
                currency=plan.currency or "ZAR",
                status=InvoiceStatusEnum.PENDING.value if amount > 0 else InvoiceStatusEnum.PAID.value,
                due_date=due_date.date(),
                paid_at=today if amount == 0 else None,
                created_at=today
            )
            invoice_orm = InvoiceORM(**invoice.model_dump(exclude={'billing_profile', 'billing_plan'}))
            self.logger.info(f"Creating invoice ORM LOG : {invoice_orm.__dict__}")
            session.add(invoice_orm)
            return invoice

    async def _update_last_invoice_id(self, subscription_id: str, last_invoice_id: str):
        """
        Updates the last invoice ID for a given subscription.

        Args:
            subscription_id (str): The ID of the subscription.
            last_invoice_id (str): The ID of the last invoice to set.

        Returns:
            bool: True if the update was successful, False otherwise.
        """
        with self.session_factory() as session:
            billing_profile = session.query(CompanyBillingProfileORM).filter_by(
                billing_profile_id=subscription_id).first()
            if not billing_profile:
                return False

            billing_profile.last_invoice_id = last_invoice_id
            session.commit()
            return True

    async def _get_latest_invoice(self, company_id: str):
        """
        Retrieves the latest invoice for the given company.

        Args:
            company_id (str): ID of the company.

        Returns:
            Invoice or None: The most recent invoice if one exists.
        """
        with self.session_factory() as session:
            invoice = (
                session.query(InvoiceORM)
                .filter_by(company_id=company_id)
                .order_by(InvoiceORM.created_at.desc())
                .first()
            )
            return Invoice(**invoice.to_dict()) if invoice else None

    async def _get_invoice_by_id(self, invoice_id: str):
        """
        Retrieves an invoice by its unique ID.

        Args:
            invoice_id (str): The ID of the invoice.

        Returns:
            Invoice or None: The invoice if found.
        """
        with self.session_factory() as session:
            invoice = session.query(InvoiceORM).filter_by(invoice_id=invoice_id).first()
            return Invoice(**invoice.to_dict()) if invoice else None

    async def _mark_invoice_paid(self, invoice_id: str):
        """
        Marks a given invoice as paid.
        Args:
            invoice_id (str): The ID of the invoice to mark as paid.
        Returns:
            Invoice: The updated invoice.
        Raises:
            ValueError: If the invoice doesn't exist.
        """
        with self.session_factory() as session:
            invoice_orm = session.query(InvoiceORM).filter_by(invoice_id=invoice_id).first()
            if not invoice_orm:
                raise ValueError("Invoice not found")

            invoice_orm.status = InvoiceStatusEnum.PAID.value
            invoice_orm.paid_at = datetime.now(timezone.utc)  # Use UTC now

            session.commit()
            session.refresh(invoice_orm)

            return Invoice(**invoice_orm.to_dict())

    async def _list_company_invoices(self, company_id: str, limit: int = 10, offset: int = 0):
        """
        Lists invoices for a given company with pagination.

        Args:
            company_id (str): The ID of the company.
            limit (int): Number of invoices to return. Default is 10.
            offset (int): Number of records to skip. Default is 0.

        Returns:
            List[Invoice]: A list of invoices for the company.
        """
        with self.session_factory() as session:
            invoices = (
                session.query(InvoiceORM)
                .filter_by(company_id=company_id)
                .order_by(InvoiceORM.created_at.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )
            return [Invoice(**inv.to_dict()) for inv in invoices]

    async def _delete_invoice(self, invoice_id: str):
        """
        Deletes an invoice by ID.

        Args:
            invoice_id (str): The ID of the invoice to delete.

        Returns:
            bool: True if deleted, False if not found.
        """
        with self.session_factory() as session:
            invoice = session.query(InvoiceORM).filter_by(invoice_id=invoice_id).first()
            if not invoice:
                return False

            session.delete(invoice)
            session.commit()
            return True

    async def _update_invoice_status(self, invoice_id: str, status: InvoiceStatusEnum):
        """
        Updates the status of a specific invoice.

        Args:
            invoice_id (str): The ID of the invoice to update.
            status (InvoiceStatusEnum): The new status to set.

        Returns:
            Invoice: The updated invoice.

        Raises:
            ValueError: If the invoice is not found.
        """
        with self.session_factory() as session:
            invoice_orm = session.query(InvoiceORM).filter_by(invoice_id=invoice_id).first()
            if not invoice_orm:
                raise ValueError("Invoice not found")

            invoice_orm.status = status.value
            if status == InvoiceStatusEnum.PAID:
                invoice_orm.paid_at = datetime.now(timezone.utc)  # Use UTC now

            invoice_orm.updated_at = datetime.now(timezone.utc)

            session.commit()
            session.refresh(invoice_orm)
            return Invoice(**invoice_orm.to_dict())
