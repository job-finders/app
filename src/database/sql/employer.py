from sqlalchemy import Column, String, Boolean, DateTime, Enum, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from src.database.sql import Base  # Assuming your Base declarative is here

class EmployerORM(Base):
    __tablename__ = "employers"
    
    employer_id = Column(UUID(as_uuid=False), primary_key=True, 
                        default=lambda: str(uuid.uuid4()), unique=True, index=True)
    user_uid = Column(String(ID_LEN), nullable=False, unique=True, index=True)
    company_id = Column(String(ID_LEN), nullable=False, index=True)  # Assuming company relation
    company_name = Column(String(NAME_LEN), nullable=False)
    industry = Column(String(NAME_LEN), default="General")
    company_size = Column(String(20), nullable=False, 
                         default="1-10")
    website = Column(String(NAME_LEN), nullable=True)
    contact_email = Column(String(120), nullable=False)
    phone = Column(String(15), nullable=True)  # +27123456789 = 13 chars
    location = Column(String(NAME_LEN), nullable=False)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String(NAME_LEN), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        # Enforce company_size enum values
        CheckConstraint(
            company_size.in_(["1-10", "11-50", "51-200", "201-500", "500+"]),
        # Ensure unique company per user (assuming 1 company per employer account)
        CheckConstraint("company_id IS NOT NULL"),
        Index("ix_employer_company", "company_id", "user_uid", unique=True),
    )

    def to_dict(self) -> Employer:
        return dict(
            employer_id=self.employer_id,
            user_uid=self.user_uid,
            company_id=self.company_id,
            company_name=self.company_name,
            industry=self.industry,
            company_size=self.company_size,
            website=self.website,
            contact_email=self.contact_email,
            phone=self.phone,
            location=self.location,
            is_verified=self.is_verified,
            verification_token=self.verification_token,
            created_at=self.created_at
        )
