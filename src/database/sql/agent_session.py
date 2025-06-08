# models/agent_session.py
from sqlalchemy import Column, String, JSON

from src.database.constants import NAME_LEN, ID_LEN
from src.database.sql import Base


class AgentSessionORM(Base):
    __tablename__ = "agent_sessions"
    session_id = Column(String(ID_LEN), primary_key=True)
    agent_name = Column(String(NAME_LEN), index=True)
    context_data = Column(JSON)
