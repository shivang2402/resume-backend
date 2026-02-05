from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base

class SectionConfig(Base):
    __tablename__ = "section_configs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    section_type = Column(String(50), nullable=False)  # experience, project, skills
    section_key = Column(String(100), nullable=False)  # amazon, memory_allocator
    
    priority = Column(String(20), default="normal")  # always, normal, never
    fixed_flavor = Column(String(100), nullable=True)  # required when priority='always'
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    user = relationship("User", backref="section_configs")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'section_type', 'section_key', name='uq_section_config'),
    )
