from contextlib import contextmanager
from sqlalchemy.orm import Session
from models.agent_session import AgentSessionORM
from database import SessionLocal  # Adjust according to your db session import

class AgentController:
    @contextmanager
    def get_session(self) -> Session:
        session = SessionLocal()
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

    async def get_agent_session(self, user_uid: str, agent_name: str) -> dict | None:
        with self.get_session() as session:
            agent_session = (
                session.query(AgentSessionORM)
                .filter_by(user_uid=user_uid, agent_name=agent_name)
                .first()
            )
            return agent_session.session_data if agent_session else None

    async def save_agent_session(self, user_uid: str, agent_name: str, session_data: dict):
        with self.get_session() as session:
            agent_session = (
                session.query(AgentSessionORM)
                .filter_by(user_uid=user_uid, agent_name=agent_name)
                .first()
            )
            if not agent_session:
                agent_session = AgentSessionORM(user_uid=user_uid, agent_name=agent_name)
                session.add(agent_session)

            agent_session.session_data = session_data
