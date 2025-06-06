# ----------- Database Models (MySQL) -----------
import asyncio
import uuid
from time import sleep

from flask import Flask
from sqlalchemy import JSON, Index, event, Column, String, ForeignKey, Integer, DateTime, Boolean, DDL
from datetime import datetime, timedelta, timezone

from src.config import config_instance
from src.controllers.controller import Controllers
from src.database.sql import Base
from src.database.constants import ID_LEN, utc_time
# ----------- Activity Processor -----------
from threading import Thread
from queue import Queue
# ----------- Redis Integration -----------
import redis
from src.logger import init_logger



class UserSearchActivityORM(Base):
    __tablename__ = 'user_search_activities'
    id = Column(String(ID_LEN), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(ID_LEN), ForeignKey('jobseeker_profiles.user_uid'), index=True)
    search_term = Column(String(255))
    filters = Column(JSON)
    result_count = Column(Integer)
    timestamp = Column(DateTime(timezone=True), default=utc_time(), index=True)


class JobViewActivityORM(Base):
    __tablename__ = 'job_view_activities'
    id = Column(String(ID_LEN), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(ID_LEN), ForeignKey('jobseeker_profiles.user_uid'), index=True)
    job_id = Column(String(ID_LEN), ForeignKey('jobs.job_id'), index=True)
    view_start = Column(DateTime(timezone=True))
    view_end = Column(DateTime(timezone=True))
    application_started = Column(Boolean, default=False)
    duration = Column(Integer)  # Seconds


class ApplicationStepORM(Base):
    __tablename__ = 'application_steps'
    id = Column(String(ID_LEN), primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String(ID_LEN), ForeignKey('job_applications.application_id'), index=True)
    step_name = Column(String(50))
    timestamp = Column(DateTime(timezone=True), default=utc_time(), index=True)

# ----------- Data Retention -----------
class ArchivedActivityORM(Base):
    __tablename__ = 'archived_activities'
    id = Column(String(ID_LEN), primary_key=True)
    original_id = Column(String(ID_LEN))
    user_id = Column(String(ID_LEN), index=True)
    activity_type = Column(String(20))
    data = Column(JSON)
    archived_at = Column(DateTime(timezone=True), default=utc_time())

#
# # Create indexes
# event.listen(UserSearchActivityORM.__table__, 'after_create',
#              lambda *args: DDL("CREATE INDEX ix_search_term ON user_search_activities (search_term(50))")
#              )


class RedisActivityClient:
    def __init__(self):
        config = config_instance()
        self.conn = redis.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            db=config.REDIS_DB,
            decode_responses=True
        )
        self.streams = {
            'search': 'activity:search',
            'view': 'activity:view',
            'step': 'activity:step'
        }

    def log_activity(self, activity_type: str, data: dict):
        """Log activity to Redis stream"""
        self.conn.xadd(self.streams[activity_type], data)

    def read_activities(self, activity_type: str, count=100):
        """Read activities from stream"""
        return self.conn.xread({self.streams[activity_type]: '0-0'}, count=count)

    def cache_metrics(self, user_id: str, metrics: dict, ttl=3600):
        """Store metrics in Redis hash"""
        self.conn.hset(f'metrics:{user_id}', mapping=metrics)
        self.conn.expire(f'metrics:{user_id}', ttl)

    def get_cached_metrics(self, user_id: str):
        """Retrieve cached metrics"""
        return self.conn.hgetall(f'metrics:{user_id}')



class ActivityProcessor(Thread):
    """
        activity processor redis based
    """
    def __init__(self,get_session, redis_client):
        super().__init__(daemon=True)
        self.redis = redis_client
        self.queue = Queue(maxsize=10000)
        self.batch_size = 100
        self.running = True
        self.logger = init_logger("analytics_logger-activity-processor")
        self.get_session = get_session

    def run(self):
        """Process activities from Redis to MySQL"""
        while self.running:
            self.process_batch(activity_type='search')
            self.process_batch(activity_type='view')
            self.process_batch(activity_type='step')
            sleep(5)

    def process_batch(self, activity_type: str):
        """
            needs to pass database session to use when calling this method
        :param activity_type:
        :return:
        """
        try:
            with self.get_session() as session:
                # Get activities from Redis
                activities = self.redis.read_activities(activity_type, self.batch_size)
                if not activities:
                    return

                # Convert to ORM objects
                orm_objects = []
                for activity in activities:
                    data = activity['data']
                    if activity_type == 'search':
                        orm_objects.append(UserSearchActivityORM(**data))
                    elif activity_type == 'view':
                        orm_objects.append(JobViewActivityORM(**data))
                    elif activity_type == 'step':
                        orm_objects.append(ApplicationStepORM(**data))

                # Bulk save to MySQL
                session.bulk_save_objects(orm_objects)

                # Acknowledge processed messages
                self.redis.conn.xdel(self.redis.streams[activity_type], *[a['id'] for a in activities])

        except Exception as e:
            self.logger.error(f"Activity processing failed: {str(e)}")



class RetentionManager(Controllers):
    """run this at start up
        we need to run the cleanup command at the needed interval in order to cleanup entries
    """
    def __init__(self):
        super().__init__()
        self.cleanup_days = config_instance().ACTIVITY_RETENTION_DAYS

    def init_app(self, app: Flask):
        super().init_app(app=app)
        retention = self

        @app.cli.command('cleanup-activities')
        def cleanup_command():
            with app.app_context():
                asyncio.run(retention.archive_old_activities())


    async def archive_old_activities(self):
        """Archive activities older than retention period"""
        cutoff = utc_time() - timedelta(days=self.cleanup_days)

        with self.get_session() as session:
            # Archive searches
            searches = session.query(UserSearchActivityORM).filter(UserSearchActivityORM.timestamp < cutoff)
            self._archive_records(searches, 'search', session)

            # Archive views
            views = session.query(JobViewActivityORM) \
                .filter(JobViewActivityORM.view_start < cutoff)
            self._archive_records(views, 'view', session)

            # Archive steps
            steps = session.query(ApplicationStepORM) \
                .filter(ApplicationStepORM.timestamp < cutoff)
            self._archive_records(steps, 'step', session)

    def _archive_records(self, query, activity_type: str, session):
        """Archive a query result set"""
        for record in query:
            archive = ArchivedActivityORM(
                original_id=record.id,
                user_id=record.user_id,
                activity_type=activity_type,
                data=self._serialize_record(record)
            )
            session.add(archive)
            session.delete(record)

    @staticmethod
    def _serialize_record(record):
        """Convert ORM object to JSON-serializable dict"""
        return {c.name: getattr(record, c.name) for c in record.__table__.columns}
