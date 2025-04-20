
import uuid
from datetime import date
from sqlalchemy import Column, String, Date, Text, inspect, Boolean, DateTime

from src.database.constants import NAME_LEN, ID_LEN
from src.database.sql import Base, engine


class UserORM(Base):
    __tablename__ = 'users'
    uid = Column(String(ID_LEN), primary_key=True, unique=True, index=True)
    name = Column(String(NAME_LEN), nullable=False, index=True)
    email = Column(String(255))
    password_hash = Column(String(255))
    role = Column(String(12),default="seeker")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime)


    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            cls.__table__.create(bind=engine)

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
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
