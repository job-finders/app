# Standard Library
import inspect
from datetime import datetime, timedelta, timezone
from typing import Callable, List, get_type_hints
from uuid import uuid4

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
            "get_paid_invoices": self._get_paid_invoices,  # Added for cron service usage
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

    async def _close_invoice(self, invoice_id: str):
        with self.session_factory() as session:
            invoice_orm = session.query(InvoiceORM).filter_by(invoice_id=invoice_id).first()
            if not invoice_orm:
                raise ValueError("Invoice not found")
            invoice_orm.status = InvoiceStatusEnum.CLOSED.value  # Assuming CLOSED is a valid status
            session.commit()
            session.refresh(invoice_orm)
            return Invoice(**invoice_orm.to_dict())

    async def _create_invoice(self, billing_profile: CompanyBillingProfile, plan: BillingPlan):
        """
        Creates a new invoice for a company's billing plan.

        Args:
            billing_profile (CompanyBillingProfile): The company's billing profile.
            plan (BillingPlan): The billing plan being invoiced.

        Returns:
            Invoice: The newly created invoice.
        """
        with self.session_factory() as session:
            today = datetime.now(timezone.utc)
            amount = float(
                plan.price) if not billing_profile.is_trial_valid else 0.0  # Assuming is_trial_valid from profile
            due_date = today + timedelta(days=7)

            invoice = Invoice(
                invoice_id=str(uuid4()),
                company_id=billing_profile.company_id,
                plan_id=plan.plan_id,
                amount=amount,
                currency=plan.currency or "ZAR",
                status=InvoiceStatusEnum.PENDING.value if amount > 0 else InvoiceStatusEnum.PAID.value,
                due_date=due_date.date(),
                paid_at=today if amount == 0 else None,
                created_at=today
            )

            invoice_orm = InvoiceORM(**invoice.model_dump())
            session.add(invoice_orm)

            billing_profile_orm = session.query(CompanyBillingProfileORM).filter_by(
                company_id=billing_profile.company_id
            ).first()
            if billing_profile_orm:
                billing_profile_orm.last_invoice_id = invoice.invoice_id

            session.commit()
            session.refresh(invoice_orm)

            return Invoice(**invoice_orm.to_dict())

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
            invoice = session.query(InvoiceORM).filter_by(invoice_id=invoice_id).first()
            if not invoice:
                raise ValueError("Invoice not found")

            invoice.status = InvoiceStatusEnum.PAID.value
            invoice.paid_at = datetime.now(timezone.utc)  # Use UTC now

            session.commit()
            session.refresh(invoice)
            return Invoice(**invoice.to_dict())

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
            invoice = session.query(InvoiceORM).filter_by(invoice_id=invoice_id).first()
            if not invoice:
                raise ValueError("Invoice not found")

            invoice.status = status.value
            if status == InvoiceStatusEnum.PAID:
                invoice.paid_at = datetime.now(timezone.utc)  # Use UTC now

            session.commit()
            session.refresh(invoice)
            return Invoice(**invoice.to_dict())
