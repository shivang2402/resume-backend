import uuid

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class Section(Base):
    __tablename__ = "sections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    type = Column(String(50), nullable=False)       # experience, project, skills, coursework, education, heading
    key = Column(String(100), nullable=False)       # amazon, kambaz, systems_hft, default
    flavor = Column(String(100), nullable=False)    # systems, fullstack, default, ml
    version = Column(String(20), nullable=False)    # 1.0, 1.1, 2.0

    content = Column(JSONB, nullable=False)         # bullets, title, dates, tech, etc.
    is_current = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="sections")

    __table_args__ = (
        UniqueConstraint("user_id", "type", "key", "flavor", "version", name="uq_section_version"),
    )