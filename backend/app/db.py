"""Database connection and session management."""

import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

# Database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://search_user:search_password@localhost:5432/search_db")

# Create engine with connection pooling
engine: Engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=3600,  # Recycle connections after 1 hour
    echo=False,  # Set to True for SQL debugging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Get database session."""
    return SessionLocal()


def check_database_health() -> bool:
    """Check if database connection is healthy."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def get_table_counts() -> dict:
    """Get counts of documents and chunks for metrics."""
    db = get_db()
    try:
        # Count documents
        doc_count = db.execute(text("SELECT COUNT(*) FROM documents")).scalar()

        # Count chunks
        chunk_count = db.execute(text("SELECT COUNT(*) FROM chunks")).scalar()

        return {
            "documents": doc_count or 0,
            "chunks": chunk_count or 0,
        }
    except Exception:
        return {"documents": 0, "chunks": 0}
    finally:
        db.close()
