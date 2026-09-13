import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base

class DocumentStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    page_count = Column(Integer, default=0)
    status = Column(String(50), default="PENDING")
    error_message = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    markdown_content = Column(Text, nullable=True)
    metadata_json = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    extractions = relationship("ExtractionResult", back_populates="document", cascade="all, delete-orphan")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    page_number = Column(Integer, default=1)
    chunk_type = Column(String(50), default="text") # text, table, header, list
    metadata_json = Column(JSON, default=dict)
    
    # Store vector embedding (JSON list of floats) for cross-database compatibility (pgvector / sqlite)
    embedding = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="chunks")

class ExtractionResult(Base):
    __tablename__ = "extraction_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    schema_name = Column(String(100), nullable=False) # e.g. "invoice", "tax_form", "contract"
    extracted_data = Column(JSON, nullable=False)
    confidence_score = Column(String(50), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="extractions")
