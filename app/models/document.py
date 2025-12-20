import uuid
import enum
from sqlalchemy import Column, String, ForeignKey, DateTime, func, Text, Integer, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, mapped_column
from pgvector.sqlalchemy import Vector
from app.db.base import Base

class DocStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    display_name = Column(String, nullable=True) 
    source_url = Column(String, nullable=True)
    file_path = Column(String, nullable=True)
    
    status = Column(SQLEnum(DocStatus), default=DocStatus.PENDING, nullable=False)
    error = Column(Text, nullable=True)
    
    school_name = Column(String, nullable=False, index=True) 
    syllabus = Column(String, nullable=False, index=True)
    class_name = Column(String, nullable=False, index=True)
    subject = Column(String, nullable=False, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")

    def __str__(self):
        return self.display_name or str(self.id)


class Chunk(Base):
    __tablename__ = "chunks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"))
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    embedding = mapped_column(Vector(768)) 
    
    document = relationship("Document", back_populates="chunks")