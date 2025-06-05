from sqlalchemy import Column, Integer, String, inspect, ForeignKey, DateTime, Text
from src.database.constants import ID_LEN, utc_time
from src.database.sql import Base, engine


class AdminORM(Base):
    __tablename__ = 'admin'

    admin_id = Column(Integer, primary_key=True, autoincrement=True)
    admin_users = Column(String(ID_LEN),ForeignKey('users.uid'))
    flagged_users = Column(String(ID_LEN), ForeignKey('flagged_users.flag_id'))


    @classmethod
    def create_if_not_table(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    # noinspection PyUnresolvedReferences
    @classmethod
    def delete_table(cls):
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)



class FlaggedUserORM(Base):
    __tablename__ = 'flagged_users'

    flag_id = Column(String(ID_LEN), primary_key=True)
    # reference_id maps to either Employer or JobSeeker, depending on the context

    reference_id = Column(String(ID_LEN), nullable=False)  # Assuming user_id is a string
    reason = Column(String(255), nullable=False)
    flagged_by = Column(String(ID_LEN), ForeignKey('users.uid'), nullable=False)  # User who flagged
    date_flagged_at = Column(DateTime(timezone=True), default=utc_time)
    status = Column(String(20), nullable=False, default="flagged")  # e.g., "flagged", "resolved"

    __table_args__ = (
        UniqueConstraint("reference_id", "reason", name="uq_flaggeduser_reason_once"),
    )

    @classmethod
    def create_if_not_table(cls):
        """Creates the flagged_users table if it does not exist."""
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    # noinspection PyUnresolvedReferences
    @classmethod
    def delete_table(cls):
        """Drops the flagged_users table if it exists."""
        if inspect(engine).has_table(cls.__tablename__):
            cls.__table__.drop(bind=engine)


class AdminRecommendationORM(Base):
    """security recommendations after the recommendations are stored
    then admin can choose to apply the recommendation or not
    """
    __tablename__ = "admin_recommendations"

    recommendation_id = Column(String(ID_LEN), primary_key=True, default=lambda: str(uuid4()))
    reference_id = Column(String(ID_LEN), index=True, nullable=False)
    recommended_action = Column(String(36), nullable=False)  # Matches RiskRecommendation enum values
    recommended_by = Column(String(ID_LEN), nullable=False)
    recommended_at = Column(DateTime(timezone=True), default=utc_time)
    reason = Column(Text, nullable=True)

