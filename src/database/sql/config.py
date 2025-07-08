from sqlalchemy import Column, Integer, String, inspect

from src.database.sql import Base, engine


class ConfigurationORM(Base):
    """sumary_line
        This is a database table model for storing configurations for system administration.
    Keyword arguments:
    argument -- description
    Return: return_description
    """
    
    __tablename__ = 'configurations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(50), nullable=False)  # e.g., "location", "industry"
    value = Column(String(100), nullable=False)  # stored as string but cast based on data_type
    data_type = Column(String(50), nullable=False, default="string")  # e.g., "string", "int", "bool", "list"
    description = Column(String(255), nullable=True)

    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    # noinspection PyUnresolvedReferences
    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)

    def to_dict(self) -> dict:
        """
        Convert the ConfigurationORM instance to a dictionary,
        casting `value` based on `data_type` to ensure compatibility
        with the Pydantic Configuration model.
        """
        casted_value = self._cast_value(self.value, self.data_type)

        return {
            "id": self.id,
            "event_type": self.type,
            "value": casted_value,
            "data_type": self.data_type,
            "description": self.description,
        }

    # noinspection PyBroadException
    @staticmethod
    def _cast_value(value: str, data_type: str):
        try:
            if data_type == "int":
                return int(value)
            elif data_type == "bool":
                return value.lower() in ("true", "1", "yes")
            elif data_type == "list":
                return [item.strip() for item in value.split(",")]
            return value  # default: string
        except Exception:
            return value
