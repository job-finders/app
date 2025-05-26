from src.controllers.controller import Controllers, error_handler
from src.logger import init_logger
from src.database.sql.agent_session import AgentSessionORM
from typing import Optional


class AgentController(Controllers):
    def __init__(self):
        super().__init__()
        self.logger = init_logger("AgentController")

    @error_handler
    async def get_agent_session(self, user_uid: str, agent_name: str) -> Optional[dict]:
        """
        Retrieve the session data for a given user and agent.

        :param user_uid: Unique user identifier
        :param agent_name: Name of the agent
        :return: Session data dict or None if not found
        """
        with self.get_session() as session:
            agent_session = (
                session.query(AgentSessionORM)
                .filter_by(user_uid=user_uid, agent_name=agent_name)
                .first()
            )
            if agent_session:
                self.logger.debug(f"Found session for user {user_uid}, agent {agent_name}")
                return agent_session.session_data
            self.logger.debug(f"No session found for user {user_uid}, agent {agent_name}")
            return None

    @error_handler
    async def save_agent_session(self, user_uid: str, agent_name: str, session_data: dict):
        """
        Save or update the session data for a given user and agent.

        :param user_uid: Unique user identifier
        :param agent_name: Name of the agent
        :param session_data: Session data to save
        """
        with self.get_session() as session:
            agent_session = (
                session.query(AgentSessionORM)
                .filter_by(user_uid=user_uid, agent_name=agent_name)
                .first()
            )
            if not agent_session:
                self.logger.debug(f"Creating new session for user {user_uid}, agent {agent_name}")
                agent_session = AgentSessionORM(user_uid=user_uid, agent_name=agent_name)
                session.add(agent_session)

            agent_session.session_data = session_data
            self.logger.debug(f"Session data updated for user {user_uid}, agent {agent_name}")
