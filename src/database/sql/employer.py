import uuid

from sqlalchemy import Column, String, Boolean, DateTime, Enum, CheckConstraint, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.database.constants import ID_LEN, NAME_LEN
from src.database.sql import Base  # Assuming your Base declarative is here


class EmployerORM(Base):
    __tablename__ = "employers"

    employer_id = Column(String(ID_LEN), primary_key=True, default=lambda: str(uuid.uuid4()),
                         unique=True, index=True)
    user_uid = Column(String(ID_LEN), nullable=False, unique=True, index=True)
    company_id = Column(String(ID_LEN), ForeignKey('companies.company_id'), nullable=False, index=True)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String(NAME_LEN), nullable=True)
    verification_token_expires_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship to CompanyORM
    company = relationship("CompanyORM", back_populates="employers")

    def to_dict(self) -> dict:
        employer_dict = {
            "employer_id": self.employer_id,
            "user_uid": self.user_uid,
            "company_id": self.company_id,
            "is_verified": self.is_verified,
            "verification_token": self.verification_token,
            "verification_token_expires_at": self.verification_token_expires_at,
            "created_at": self.created_at,
        }
        # Include company details if loaded
        if self.company:
            employer_dict["company"] = self.company.to_dict()
        return employer_dict


