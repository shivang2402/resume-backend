import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class OutreachMessage(Base):
    __tablename__ = "outreach_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id = Column(UUID(as_uuid=True), ForeignKey("outreach_threads.id", ondelete="CASCADE"), nullable=False)

    direction = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)

    message_at = Column(DateTime(timezone=True))
    is_raw_dump = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    thread = relationship("OutreachThread", back_populates="messages")
