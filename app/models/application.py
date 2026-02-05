import uuid

from sqlalchemy import Column, String, Date, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class Application(Base):
    __tablename__ = "applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    company = Column(String(255), nullable=False)
    role = Column(String(255), nullable=False)
    job_url = Column(Text)
    job_id = Column(String(100))
    location = Column(String(255))

    status = Column(String(50), default="applied")  # applied, phone_screen, technical, onsite, offer, rejected, ghosted, withdrawn

    resume_config = Column(JSONB, nullable=False)   # references to section versions used
    job_description = Column(Text, nullable=True)   # NEW: store JD text

    applied_at = Column(Date, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    notes = Column(Text)
    referral = Column(String(255))
    salary_range = Column(String(100))

    # Relationships
    user = relationship("User", backref="applications")
