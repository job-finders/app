import logging, json
from datetime import datetime, timezone
from typing import Optional, List

from src.services.billing.event_realtime_queue import enqueue_realtime_event, redis_client
from src.services.billing.schemas_interfaces import BillingServiceInterface, BillingEventType
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
        # Define which event types trigger email notifications (passive/batch)
        self.__notify_email_events = {
            BillingEventType.PAYMENT_SUCCESS,
            BillingEventType.SUBSCRIPTION_APPLIED,  # Or SUBSCRIPTION_CREATED
            BillingEventType.SUBSCRIPTION_EXPIRING_SOON,
            BillingEventType.SUBSCRIPTION_EXPIRED,
            BillingEventType.BILLING_PROFILE_MISSING,  # Consider if this needs an email or just an internal alert
            BillingEventType.EMAIL_SEND_FAILED,  # For internal alerts about failed sends
        }

        # Define which event types are pushed to a real-time queue
        self.__realtime_event_types = {
            BillingEventType.PAYMENT_SUCCESS,
            BillingEventType.PAYMENT_FAILED,
            BillingEventType.SUBSCRIPTION_EXPIRED,
            BillingEventType.SUBSCRIPTION_STARTED,
            BillingEventType.SUBSCRIPTION_APPLIED,  # Included for completeness
            BillingEventType.TRIAL_STARTED,
            BillingEventType.BILLING_PROFILE_CREATED,
            BillingEventType.TRIAL_ENDED  # A trial ending might also be real-time for immediate UI update
        }
        self.__interface_map = {
            "interface_schema": self._interface_schema,
            "describe_actions": self._describe_actions,
            "record_event": self._record_event,
            "list_events": self._list_events,
            "list_realtime_events": self._list_realtime_events,
            "get_event_by_id": self._get_event_by_id,
            "mark_email_sent": self._mark_email_sent,
            "list_unsent_email_events": self._list_unsent_email_events,
            "get_last_event": self._get_last_event,  # Added for CronService usage
        }

    async def _record_event(self, company_id: str, type: BillingEventType, event_metadata: Optional[dict] = None) -> BillingEvent:
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
            # Store the string value of the Enum
            event_orm = BillingEventORM(
                company_id=company_id,
                type=type.value,  # Store the string value of the Enum
                event_metadata=event_metadata,
                created_at=datetime.now(timezone.utc),
            )
            # Check if the event type is considered real-time
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
        # The xread mock returns [(stream_name, [(id, {field: value})])]. We need to extract the actual data.
        if entries and entries[0] and len(entries[0]) > 1 and entries[0][1]:
            # Each entry in entries[0][1] is (event_id_bytes, {b'data': b'{"key": "value"}'})
            # We need to extract the 'data' part, decode it, and then parse JSON.
            parsed_events = []
            for event_id_bytes, data_dict in entries[0][1]:
                if b'data' in data_dict:
                    parsed_events.append(json.loads(data_dict[b'data'].decode('utf-8')))
            return parsed_events
        return []

    async def _list_events(
            self,
            company_id: str,
            type: Optional[BillingEventType] = None,  # Expect Enum here
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
            # Filter by the string values of the Enums in __notify_email_events
            event_type_values = {e.value for e in self.__notify_email_events}
            events_orm = (
                session.query(BillingEventORM)
                .filter(BillingEventORM.email_sent == False,
                        BillingEventORM.type.in_(event_type_values))
                .order_by(BillingEventORM.created_at.asc())
                .limit(limit)
                .all()
            )
            return [BillingEvent(**e.to_dict()) for e in events_orm]

    async def _get_last_event(self, company_id: str, event_type: str) -> Optional[BillingEvent]:
        """
        Retrieves the last recorded event of a specific type for a company.

        Args:
            company_id (str): The ID of the company.
            event_type (str): The type of the event (string value, as stored in DB).

        Returns:
            BillingEvent or None: The last matching event if found.
        """
        with self.session_factory() as session:
            event = (
                session.query(BillingEventORM)
                .filter_by(company_id=company_id, type=event_type)
                .order_by(BillingEventORM.created_at.desc())
                .first()
            )
            return BillingEvent(**event.to_dict()) if event else None
