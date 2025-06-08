import logging, json
from datetime import datetime, timezone
from typing import Optional, List

from src.services.billing.event_realtime_queue import enqueue_realtime_event, redis_client
from src.services.billing.schemas_interfaces import BillingServiceInterface
from src.database.sql.billing_sql import BillingEventORM
from src.database.models.billing import BillingEvent



class BillingEventService(BillingServiceInterface):
    """
    Manages billing-related events such as trial changes, payments, cancellations, etc.
    """

    def __init__(self, session_factory):
        super().__init__()
        self.session_factory = session_factory
        self.logger = logging.getLogger(__name__)
        self._realtime_event_count = 10
        self.__notify_email_events = {
            "payment_success",
            "subscription_applied",
            "subscription_expiring_soon",
            "subscription_expired"
        }
        self.__realtime_event_types = {
            "payment_success",
            "payment_failed",
            "subscription_expired",
            "subscription_started",
            "trial_started",
            "billing_profile_created",
            "subscription_applied"
        }

        self.__interface_map = {
            "interface_schema": self._interface_schema,
            "describe_actions": self._describe_actions,
            "record_event": self._record_event,
            "list_events": self._list_events,
            "list_realtime_events": self._list_realtime_events,
            "get_event_by_id": self._get_event_by_id,
            "mark_email_sent": self._mark_email_sent,
            "list_unsent_email_events": self._list_unsent_email_events
        }

    async def _record_event(self, company_id: str, type: str, event_metadata: Optional[dict] = None) -> BillingEvent:
        """
        Records a new billing event.

        Args:
            company_id (str): The ID of the company.
            type (str): Type of the event (e.g., 'trial_started', 'payment_success').
            event_metadata (dict, optional): Additional data about the event.

        Returns:
            BillingEvent: The created billing event.
        """
        if not company_id or not type:
            raise ValueError("company_id and type are required.")

        event_metadata = event_metadata or {}

        with self.session_factory() as session:
            event_orm = BillingEventORM(
                company_id=company_id,
                type=type,
                event_metadata=event_metadata,
                created_at=datetime.now(timezone.utc),
            )

            if type in self.__realtime_event_types:
                # event is realtime store it in the queue
                enqueue_realtime_event(event_orm.to_dict())

            session.add(event_orm)
            session.commit()
            session.refresh(event_orm)

            self.logger.info(f"BillingEvent recorded: {event_orm.event_id} - {type}")

            return BillingEvent(**event_orm.to_dict())

    @staticmethod
    async def _list_realtime_events() -> list[dict]:
        """
        Retrieves billing events that are considered real-time and require immediate handling,
        such as payment confirmations, failures, or subscription changes.

        Returns:
            List[dict]: List of event dictionaries sorted by creation date (ascending).
        """
        # get the events from redis queue
        entries = redis_client.xread({"billing:realtime_events": "0-0"}, count=10, block=5000)
        return [json.loads(entry[1][b'data']) for entry in entries[0][1]] if entries else []

    async def _list_events(
        self,
        company_id: str,
        type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[BillingEvent]:
        """
        Lists billing events for a company with optional filters.

        Args:
            company_id (str): Company ID to fetch events for.
            type (str, optional): Filter by event type.
            start_date (str, optional): ISO date filter from.
            end_date (str, optional): ISO date filter to.
            limit (int): Max number of events to return.
            offset (int): Number of events to skip.

        Returns:
            List[BillingEvent]: List of matching billing events.
        """
        with self.session_factory() as session:
            query = session.query(BillingEventORM).filter_by(company_id=company_id)

            if type:
                query = query.filter(BillingEventORM.type == type)

            if start_date:
                query = query.filter(BillingEventORM.created_at >= datetime.fromisoformat(start_date))
            if end_date:
                query = query.filter(BillingEventORM.created_at <= datetime.fromisoformat(end_date))

            query = query.order_by(BillingEventORM.created_at.desc()).limit(limit).offset(offset)

            events = query.all()

            return [BillingEvent(**e.to_dict()) for e in events]

    async def _get_event_by_id(self, event_id: str) -> Optional[BillingEvent]:
        """
        Fetches a single billing event by its ID.

        Args:
            event_id (str): The ID of the event.

        Returns:
            BillingEvent or None: The billing event if found.
        """
        if not event_id:
            raise ValueError("event_id is required.")

        with self.session_factory() as session:
            event = session.query(BillingEventORM).filter_by(event_id=event_id).first()

            if not event:
                self.logger.warning(f"BillingEvent not found: {event_id}")
                return None

            return BillingEvent(**event.to_dict())

    async def _mark_email_sent(self, event_id: str):
        with self.session_factory() as session:
            updated = session.query(BillingEventORM).filter_by(event_id=event_id).update({"email_sent": True})
            if updated:
                session.commit()
        return None

    async def _list_unsent_email_events(self, limit: int = 200):
        """
        Efficiently fetch up to `limit` billing events where email has not yet been sent.

        Args:
            limit (int): Max number of events to return (default 200).

        Returns:
            List[BillingEventORM]: List of unsent email events ordered by creation time.
        """
        with self.session_factory() as session:
            events = (
                session.query(BillingEventORM)
                .filter(BillingEventORM.email_sent == False,
                        BillingEventORM.type.in_(self.__notify_email_events))
                .order_by(BillingEventORM.created_at.asc())
                .limit(limit)
                .all()
            )
            return events
