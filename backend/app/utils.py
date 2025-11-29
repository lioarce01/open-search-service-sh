"""Utility functions for text processing and chunking."""

import re
import os
from typing import List, Dict, Any
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


def chunk_text(text: str, max_tokens: int = 512, overlap: int = 50) -> List[str]:
    """Chunk text into smaller pieces using sentence and paragraph boundaries.

    Args:
        text: The text to chunk
        max_tokens: Maximum number of tokens per chunk (approximate)
        overlap: Number of tokens to overlap between chunks

    Returns:
        List of text chunks
    """
    if not text.strip():
        return []

    # Simple tokenization (split on whitespace and punctuation)
    # This is approximate - a proper tokenizer would be better
    words = re.findall(r'\b\w+\b', text)

    if not words:
        return []

    chunks = []
    current_chunk = []
    current_length = 0

    for word in words:
        word_length = len(word) + 1  # +1 for space

        # If adding this word would exceed max_tokens
        if current_length + word_length > max_tokens and current_chunk:
            # Save current chunk
            chunk_text = ' '.join(current_chunk)
            chunks.append(chunk_text)

            # Start new chunk with overlap
            overlap_words = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
            current_chunk = overlap_words + [word]
            current_length = sum(len(w) + 1 for w in current_chunk)
        else:
            current_chunk.append(word)
            current_length += word_length

    # Add the last chunk
    if current_chunk:
        chunks.append(' '.join(current_chunk))

    return chunks


def generate_ts_vector(text: str) -> str:
    """Generate PostgreSQL tsvector from text for full-text search."""
    # Remove extra whitespace and normalize
    cleaned = re.sub(r'\s+', ' ', text.strip())

    # PostgreSQL will handle the tsvector creation, but we can preprocess
    # For now, just return the cleaned text - PostgreSQL will create the tsvector
    return cleaned


def estimate_token_count(text: str) -> int:
    """Estimate the number of tokens in text (rough approximation)."""
    # Simple approximation: 1 token ≈ 4 characters for English text
    return len(text) // 4


def create_pgvector_extension(db_session):
    """Create pgvector extension if it doesn't exist."""
    try:
        db_session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        db_session.commit()
        logger.info("pgvector extension created/enabled")
        return True
    except Exception as e:
        logger.error(f"Failed to create pgvector extension: {e}")
        return False


def add_embedding_column_if_missing(db_session):
    """Add embedding column to chunks table if it doesn't exist."""
    try:
        # Check if embedding column exists
        result = db_session.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'chunks' AND column_name = 'embedding'
        """))

        if result.fetchone():
            logger.info("Embedding column already exists")
            return True

        # Add embedding column
        logger.info("Adding embedding column to chunks table...")
        db_session.execute(text("""
            ALTER TABLE chunks ADD COLUMN embedding vector(768)
        """))
        db_session.commit()
        logger.info("Embedding column added successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to add embedding column: {e}")
        return False


def create_tables(db_session):
    """Create database tables."""
    from .models import Base

    try:
        Base.metadata.create_all(bind=db_session.get_bind())
        logger.info("Database tables created")
        return True
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        return False


def create_indexes(db_session):
    """Create database indexes."""
    try:
        # GIN index for tsvector
        db_session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_chunks_ts_vector
            ON chunks USING gin(ts_vector)
        """))

        # GIN index for chunk metadata JSONB
        db_session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_chunks_metadata
            ON chunks USING gin(chunk_metadata)
        """))

        # GIN index for documents metadata
        db_session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_documents_metadata
            ON documents USING gin(doc_metadata)
        """))

        db_session.commit()
        logger.info("Database indexes created")
        return True
    except Exception as e:
        logger.error(f"Failed to create indexes: {e}")
        return False


def create_vector_index(db_session, table_name: str = "chunks"):
    """Create vector index for pgvector."""
    try:
        # Check if pgvector extension exists
        result = db_session.execute(text("SELECT * FROM pg_extension WHERE extname = 'vector'"))
        if not result.fetchone():
            logger.warning("pgvector extension not found, skipping vector index creation")
            return False

        # Create IVFFlat index on embedding column
        db_session.execute(text(f"""
            CREATE INDEX IF NOT EXISTS {table_name}_embedding_idx
            ON {table_name}
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """))

        db_session.commit()
        logger.info("Vector index created")
        return True
    except Exception as e:
        logger.error(f"Failed to create vector index: {e}")
        return False


def reindex_document(db_session, doc_id: str, embedder, vector_backend):
    """Reindex all chunks for a document with new embeddings."""
    from .models import Chunk

    try:
        # Get all chunks for the document
        chunks = db_session.query(Chunk).filter(Chunk.doc_id == doc_id).all()

        if not chunks:
            logger.warning(f"No chunks found for document {doc_id}")
            return 0

        # Delete existing vectors
        if hasattr(vector_backend, 'remove_document'):
            vector_backend.remove_document(doc_id)

        # Clear embeddings from database
        for chunk in chunks:
            if hasattr(chunk, 'embedding'):
                chunk.embedding = None
            chunk.vector_id = None

        # Re-embed and re-index
        texts = [chunk.text for chunk in chunks]
        embeddings = embedder.embed_batch(texts)

        # Ensure embeddings are Python lists (not numpy arrays) for pgvector
        embeddings = [list(emb) if hasattr(emb, 'tolist') else list(emb) for emb in embeddings]

        # Add to vector backend
        metadata_list = [
            {
                'chunk_id': chunk.chunk_id,
                'doc_id': chunk.doc_id,
                'text_snippet': chunk.text[:100]
            }
            for chunk in chunks
        ]

        vector_ids = vector_backend.add_vectors(embeddings, metadata_list)

        # Update database
        for i, chunk in enumerate(chunks):
            if os.getenv("VECTOR_BACKEND", "faiss") == "faiss":
                chunk.vector_id = vector_ids[i]
            else:  # pgvector
                if hasattr(chunk, 'embedding'):
                    chunk.embedding = embeddings[i]

            chunk.embed_model = embedder.model_name
            chunk.embed_version = embedder.model_version

        db_session.commit()

        logger.info(f"Reindexed {len(chunks)} chunks for document {doc_id}")
        return len(chunks)

    except Exception as e:
        logger.error(f"Failed to reindex document {doc_id}: {e}")
        db_session.rollback()
        return 0
