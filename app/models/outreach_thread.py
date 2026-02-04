import uuid

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


# Many-to-many: threads <-> applications
thread_applications = Table(
    'thread_applications',
    Base.metadata,
    Column('thread_id', UUID(as_uuid=True), ForeignKey('outreach_threads.id', ondelete='CASCADE')),
    Column('application_id', UUID(as_uuid=True), ForeignKey('applications.id', ondelete='CASCADE'))
)


class OutreachThread(Base):
    __tablename__ = "outreach_threads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Company (required)
    company = Column(String(255), nullable=False)

    # Contact info (optional)
    contact_name = Column(String(255))
    contact_method = Column(String(50))     # linkedin, email, other

    # Resume context (optional) - stores section references used
    resume_config = Column(JSONB)

    # Status - simple for MVP
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="outreach_threads")
    applications = relationship("Application", secondary=thread_applications, backref="outreach_threads")
    messages = relationship("OutreachMessage", back_populates="thread", cascade="all, delete-orphan")
