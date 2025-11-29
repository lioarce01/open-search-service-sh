"""SQLAlchemy models for the search service."""

import os
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

# Conditionally import pgvector only if needed
Vector = None
if os.getenv("VECTOR_BACKEND", "pgvector") == "pgvector":  # Changed default to pgvector
    try:
        from pgvector.sqlalchemy import Vector
        print("pgvector Vector type imported successfully")
    except ImportError as e:
        print(f"Failed to import pgvector Vector: {e}")
        pass

Base = declarative_base()


class Document(Base):
    """Document model for storing document metadata."""

    __tablename__ = "documents"

    doc_id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=True)
    doc_metadata = Column(JSONB, nullable=True, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to chunks
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Document(doc_id='{self.doc_id}', title='{self.title}')>"


class Chunk(Base):
    """Chunk model for storing text chunks with embeddings and metadata."""

    __tablename__ = "chunks"

    chunk_id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(String, ForeignKey("documents.doc_id", ondelete="CASCADE"), nullable=False)
    text = Column(Text, nullable=False)
    vector_id = Column(Integer, nullable=True)  # For FAISS mapping
    ts_vector = Column(TSVECTOR, nullable=False)  # For full-text search
    chunk_metadata = Column(JSONB, nullable=True, default=dict)
    embed_model = Column(String, nullable=False)  # Model used for embedding
    embed_version = Column(String, nullable=False)  # Version of embedding model
    created_at = Column(DateTime, default=datetime.utcnow)

    # Conditionally add embedding column only for pgvector
    if Vector is not None:
        embedding = Column(Vector(768), nullable=True)  # For pgvector

    # Relationship to document
    document = relationship("Document", back_populates="chunks")

    def __repr__(self) -> str:
        return f"<Chunk(chunk_id={self.chunk_id}, doc_id='{self.doc_id}', text='{self.text[:50]}...')>"


# Create indexes for performance
Index("idx_chunks_doc_id", Chunk.doc_id)
Index("idx_chunks_ts_vector", Chunk.ts_vector, postgresql_using="gin")
Index("idx_chunks_metadata", Chunk.chunk_metadata, postgresql_using="gin")

# Conditionally create embedding index only for pgvector
if Vector is not None:
    Index("idx_chunks_embedding", Chunk.embedding, postgresql_using="ivfflat")  # For pgvector
