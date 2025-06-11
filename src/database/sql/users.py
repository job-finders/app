from datetime import timezone

from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy import inspect, Index

from src.database.constants import NAME_LEN, ID_LEN, utc_time
from src.database.sql import Base, engine


class UserORM(Base):
    __tablename__ = 'users'
    uid = Column(String(ID_LEN), primary_key=True, unique=True, index=True)
    name = Column(String(NAME_LEN), nullable=False, index=True)
    email = Column(String(255))
    password_hash = Column(String(255))
    role = Column(String(12), default="seeker")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utc_time)  # Auto-set on creation
    last_login = Column(DateTime(timezone=True), onupdate=utc_time, nullable=True)  # Auto-update on modification

    # Optional: Add an index for faster login time queries
    __table_args__ = (
        Index('ix_users_last_login', 'last_login'),
    )

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            cls.__table__.create(bind=engine)

    # noinspection PyUnresolvedReferences
    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

    def __bool__(self):
        return bool(self.uid) and bool(self.email)

    def to_dict(self) -> dict[str, str | bool]:
        return {
            "uid": self.uid,
            "name": self.name,
            "email": self.email,
            "password_hash": self.password_hash,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.replace(tzinfo=timezone.utc) if self.created_at else None,
            "last_login": self.last_login.replace(tzinfo=timezone.utc) if self.last_login else None
        }
