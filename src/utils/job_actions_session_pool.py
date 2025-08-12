"""
Job Actions Session Pool

Optimized database session pooling for job actions operations with
connection management, performance monitoring, and resource optimization.

This module provides efficient database session management specifically
optimized for job actions operations with proper connection pooling,
session lifecycle management, and performance monitoring.

Session Pool Features:
- Optimized connection pooling for job actions workloads
- Session lifecycle management with proper cleanup
- Connection health monitoring and recovery
- Performance metrics and optimization insights
- Resource usage tracking and optimization
"""

import threading
import time
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import weakref

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import DisconnectionError, OperationalError

from src.utils.job_actions_performance_logger import job_actions_performance_logger
from src.logger import init_logger


@dataclass
class SessionMetrics:
    """Session pool performance metrics"""
    total_sessions_created: int = 0
    active_sessions: int = 0
    peak_active_sessions: int = 0
    total_checkouts: int = 0
    total_checkins: int = 0
    connection_errors: int = 0
    session_timeouts: int = 0
    average_session_duration: float = 0.0

    def update_checkout(self):
        """Update metrics for session checkout"""
        self.total_checkouts += 1
        self.active_sessions += 1
        self.peak_active_sessions = max(self.peak_active_sessions, self.active_sessions)

    def update_checkin(self, duration: float):
        """Update metrics for session checkin"""
        self.total_checkins += 1
        self.active_sessions = max(0, self.active_sessions - 1)

        # Update average duration
        if self.total_checkins > 0:
            self.average_session_duration = (
                    (self.average_session_duration * (self.total_checkins - 1) + duration) /
                    self.total_checkins
            )


@dataclass
class SessionInfo:
    """Information about an active session"""
    session_id: str
    created_at: datetime
    last_used: datetime
    operation_count: int = 0
    user_id: Optional[str] = None
    job_id: Optional[str] = None
    operations: List[str] = field(default_factory=list)

    def touch(self, operation: str = None):
        """Update session usage information"""
        self.last_used = datetime.utcnow()
        self.operation_count += 1
        if operation:
            self.operations.append(operation)
            # Keep only last 10 operations
            if len(self.operations) > 10:
                self.operations = self.operations[-10:]


class JobActionsSessionPool:
    """
    Optimized database session pool for job actions operations.
    
    This class provides efficient database session management with connection
    pooling, session lifecycle management, and performance monitoring specifically
    optimized for job actions workloads.
    
    Features:
        - Optimized connection pooling with proper sizing
        - Session lifecycle management with automatic cleanup
        - Connection health monitoring and recovery
        - Performance metrics and optimization insights
        - Resource usage tracking and leak detection
        - Context manager support for proper session handling
    """

    def __init__(self, database_url: str, pool_size: int = 10, max_overflow: int = 20):
        """
        Initialize the session pool.
        
        Args:
            database_url: Database connection URL
            pool_size: Base pool size for connections
            max_overflow: Maximum overflow connections allowed
        """
        self.logger = init_logger("JobActionsSessionPool")

        # Create optimized engine for job actions workloads
        self.engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,  # Verify connections before use
            pool_recycle=3600,  # Recycle connections every hour
            echo=False,  # Set to True for SQL debugging
            connect_args={
                "charset": "utf8mb4",
                "connect_timeout": 10,
                "read_timeout": 30,
                "write_timeout": 30
            }
        )

        # Create session factory
        self.SessionFactory = sessionmaker(bind=self.engine)

        # Session tracking and metrics
        self._metrics = SessionMetrics()
        self._metrics_lock = threading.RLock()
        self._active_sessions: Dict[str, SessionInfo] = {}
        self._session_history: deque = deque(maxlen=1000)  # Keep last 1000 sessions

        # Performance thresholds
        self.long_session_threshold = 30.0  # seconds
        self.max_session_age = 300.0  # 5 minutes
        self.cleanup_interval = 60.0  # 1 minute

        # Setup connection event listeners
        self._setup_event_listeners()

        # Start background cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self._cleanup_thread.start()

        self.logger.info(f"JobActionsSessionPool initialized with pool_size={pool_size}, max_overflow={max_overflow}")

    @contextmanager
    def get_session(self, user_id: Optional[str] = None, job_id: Optional[str] = None, operation: str = None):
        """
        Get a database session with proper lifecycle management.
        
        Args:
            user_id: User ID for tracking (optional)
            job_id: Job ID for tracking (optional)
            operation: Operation name for tracking (optional)
            
        Yields:
            Database session with automatic cleanup
            
        Usage:
            with session_pool.get_session(user_id="123", operation="like_job") as session:
                # Use session for database operations
                result = session.query(Model).all()
        """
        session = None
        session_id = f"session_{int(time.time() * 1000000)}"
        start_time = time.time()

        try:
            # Create new session
            session = self.SessionFactory()

            # Track session creation
            with self._metrics_lock:
                self._metrics.total_sessions_created += 1
                self._metrics.update_checkout()

            # Create session info for tracking
            session_info = SessionInfo(
                session_id=session_id,
                created_at=datetime.utcnow(),
                last_used=datetime.utcnow(),
                user_id=user_id,
                job_id=job_id
            )

            if operation:
                session_info.touch(operation)

            # Track active session
            self._active_sessions[session_id] = session_info

            # Log session creation
            self.logger.debug(
                f"Session created: {session_id}",
                extra={
                    'session_id': session_id,
                    'user_id': user_id,
                    'job_id': job_id,
                    'operation': operation
                }
            )

            # Yield session for use
            yield session

            # Commit transaction if no exceptions
            if session.is_active:
                session.commit()

        except Exception as e:
            # Rollback on any exception
            if session and session.is_active:
                try:
                    session.rollback()
                    self.logger.warning(f"Session {session_id} rolled back due to error: {e}")
                except Exception as rollback_error:
                    self.logger.error(f"Failed to rollback session {session_id}: {rollback_error}")

            # Track connection errors
            if isinstance(e, (DisconnectionError, OperationalError)):
                with self._metrics_lock:
                    self._metrics.connection_errors += 1

            raise

        finally:
            # Clean up session
            if session:
                try:
                    session.close()
                except Exception as close_error:
                    self.logger.error(f"Error closing session {session_id}: {close_error}")

            # Update metrics
            duration = time.time() - start_time
            with self._metrics_lock:
                self._metrics.update_checkin(duration)

            # Remove from active sessions
            session_info = self._active_sessions.pop(session_id, None)
            if session_info:
                session_info.touch()

                # Add to history
                self._session_history.append({
                    'session_id': session_id,
                    'duration': duration,
                    'operations': session_info.operations,
                    'operation_count': session_info.operation_count,
                    'user_id': user_id,
                    'job_id': job_id,
                    'created_at': session_info.created_at.isoformat(),
                    'completed_at': datetime.utcnow().isoformat()
                })

                # Log long-running sessions
                if duration > self.long_session_threshold:
                    self.logger.warning(
                        f"Long-running session detected: {session_id} ran for {duration:.2f}s",
                        extra={
                            'session_id': session_id,
                            'duration': duration,
                            'operations': session_info.operations,
                            'user_id': user_id,
                            'job_id': job_id
                        }
                    )

                # Record performance metrics
                job_actions_performance_logger.record_database_query(
                    query_type=f"session_{operation or 'unknown'}",
                    duration=duration,
                    success=True
                )

            self.logger.debug(
                f"Session completed: {session_id} (duration: {duration:.3f}s)",
                extra={
                    'session_id': session_id,
                    'duration': duration,
                    'user_id': user_id,
                    'job_id': job_id,
                    'operation': operation
                }
            )

    def get_metrics(self) -> SessionMetrics:
        """Get current session pool metrics"""
        with self._metrics_lock:
            return SessionMetrics(
                total_sessions_created=self._metrics.total_sessions_created,
                active_sessions=self._metrics.active_sessions,
                peak_active_sessions=self._metrics.peak_active_sessions,
                total_checkouts=self._metrics.total_checkouts,
                total_checkins=self._metrics.total_checkins,
                connection_errors=self._metrics.connection_errors,
                session_timeouts=self._metrics.session_timeouts,
                average_session_duration=self._metrics.average_session_duration
            )

    def get_pool_status(self) -> Dict[str, Any]:
        """Get detailed pool status information"""
        pool = self.engine.pool
        metrics = self.get_metrics()

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "pool_info": {
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "invalid": pool.invalid()
            },
            "session_metrics": {
                "total_created": metrics.total_sessions_created,
                "active_sessions": metrics.active_sessions,
                "peak_active": metrics.peak_active_sessions,
                "total_checkouts": metrics.total_checkouts,
                "total_checkins": metrics.total_checkins,
                "connection_errors": metrics.connection_errors,
                "session_timeouts": metrics.session_timeouts,
                "average_duration": round(metrics.average_session_duration, 3)
            },
            "active_sessions": len(self._active_sessions),
            "session_history_size": len(self._session_history),
            "health_indicators": {
                "pool_healthy": pool.checkedout() < pool.size() + pool.overflow(),
                "error_rate_low": metrics.connection_errors < metrics.total_checkouts * 0.01,
                "average_duration_reasonable": metrics.average_session_duration < self.long_session_threshold
            }
        }

    def get_active_sessions_info(self) -> List[Dict[str, Any]]:
        """Get information about currently active sessions"""
        current_time = datetime.utcnow()
        active_info = []

        for session_id, session_info in self._active_sessions.items():
            duration = (current_time - session_info.created_at).total_seconds()
            idle_time = (current_time - session_info.last_used).total_seconds()

            active_info.append({
                "session_id": session_id,
                "duration": round(duration, 2),
                "idle_time": round(idle_time, 2),
                "operation_count": session_info.operation_count,
                "recent_operations": session_info.operations[-5:],  # Last 5 operations
                "user_id": session_info.user_id,
                "job_id": session_info.job_id,
                "created_at": session_info.created_at.isoformat(),
                "last_used": session_info.last_used.isoformat(),
                "is_long_running": duration > self.long_session_threshold,
                "is_idle": idle_time > 60.0  # 1 minute idle
            })

        return sorted(active_info, key=lambda x: x["duration"], reverse=True)

    def cleanup_stale_sessions(self) -> int:
        """Clean up stale sessions and return count of cleaned sessions"""
        current_time = datetime.utcnow()
        stale_sessions = []

        # Find stale sessions
        for session_id, session_info in self._active_sessions.items():
            age = (current_time - session_info.created_at).total_seconds()
            idle_time = (current_time - session_info.last_used).total_seconds()

            if age > self.max_session_age or idle_time > self.max_session_age:
                stale_sessions.append(session_id)

        # Clean up stale sessions
        cleaned_count = 0
        for session_id in stale_sessions:
            session_info = self._active_sessions.pop(session_id, None)
            if session_info:
                cleaned_count += 1
                with self._metrics_lock:
                    self._metrics.session_timeouts += 1
                    self._metrics.active_sessions = max(0, self._metrics.active_sessions - 1)

                self.logger.warning(
                    f"Cleaned up stale session: {session_id}",
                    extra={
                        'session_id': session_id,
                        'age_seconds': (current_time - session_info.created_at).total_seconds(),
                        'idle_seconds': (current_time - session_info.last_used).total_seconds(),
                        'operation_count': session_info.operation_count
                    }
                )

        if cleaned_count > 0:
            self.logger.info(f"Cleaned up {cleaned_count} stale sessions")

        return cleaned_count

    def _setup_event_listeners(self):
        """Setup SQLAlchemy event listeners for monitoring"""

        @event.listens_for(self.engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            """Handle new database connections"""
            self.logger.debug("New database connection established")

        @event.listens_for(self.engine, "checkout")
        def on_checkout(dbapi_connection, connection_record, connection_proxy):
            """Handle connection checkout from pool"""
            self.logger.debug("Connection checked out from pool")

        @event.listens_for(self.engine, "checkin")
        def on_checkin(dbapi_connection, connection_record):
            """Handle connection checkin to pool"""
            self.logger.debug("Connection checked in to pool")

        @event.listens_for(self.engine, "invalidate")
        def on_invalidate(dbapi_connection, connection_record, exception):
            """Handle connection invalidation"""
            self.logger.warning(f"Connection invalidated: {exception}")
            with self._metrics_lock:
                self._metrics.connection_errors += 1

    def _cleanup_worker(self):
        """Background worker for cleaning up stale sessions"""
        while True:
            try:
                time.sleep(self.cleanup_interval)
                self.cleanup_stale_sessions()
            except Exception as e:
                self.logger.error(f"Error in cleanup worker: {e}", exc_info=True)

    def close(self):
        """Close the session pool and cleanup resources"""
        try:
            # Clean up all active sessions
            active_count = len(self._active_sessions)
            self._active_sessions.clear()

            # Dispose of engine
            self.engine.dispose()

            self.logger.info(f"Session pool closed. Cleaned up {active_count} active sessions.")

        except Exception as e:
            self.logger.error(f"Error closing session pool: {e}", exc_info=True)


# Global session pool instance (will be initialized by the application)
job_actions_session_pool: Optional[JobActionsSessionPool] = None


def initialize_session_pool(database_url: str, pool_size: int = 10, max_overflow: int = 20) -> JobActionsSessionPool:
    """
    Initialize the global session pool.
    
    Args:
        database_url: Database connection URL
        pool_size: Base pool size for connections
        max_overflow: Maximum overflow connections allowed
        
    Returns:
        Initialized session pool instance
    """
    global job_actions_session_pool

    if job_actions_session_pool is None:
        job_actions_session_pool = JobActionsSessionPool(database_url, pool_size, max_overflow)

    return job_actions_session_pool


def get_session_pool() -> Optional[JobActionsSessionPool]:
    """Get the global session pool instance"""
    return job_actions_session_pool
