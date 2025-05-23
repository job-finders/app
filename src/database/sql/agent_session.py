# models/agent_session.py
from sqlalchemy import Column, String, JSON

from database.sql import Base


class AgentSessionORM(Base):
    __tablename__ = "agent_sessions"
    session_id = Column(String, primary_key=True)
    agent_name = Column(String, index=True)
    context_data = Column(JSON)
