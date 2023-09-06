import uuid
from datetime import date
from sqlalchemy import Column, String, Date, Text,Boolean, inspect

from src.database.constants import NAME_LEN, ID_LEN
from src.database.sql import Base, engine


class NotificationsORM(Base):
    __tablename__ = 'jobfinders_notifications'
    email: str = Column(String(255), primary_key=True, index=True)
    verification_id: str = Column(String(36))
    is_verified: bool = Column(Boolean, default=False)

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)
