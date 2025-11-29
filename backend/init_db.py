#!/usr/bin/env python3
"""Database initialization script for the semantic search service."""

import os
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from sqlalchemy import text
from app.db import get_db
from app.utils import create_pgvector_extension, create_tables, create_indexes, create_vector_index, add_embedding_column_if_missing
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Initialize the database with tables, extensions, and indexes."""
    try:
        logger.info("Starting database initialization...")

        with get_db() as db:
            # Create pgvector extension if using pgvector
            vector_backend = os.getenv("VECTOR_BACKEND", "faiss")
            if vector_backend == "pgvector":
                logger.info("Creating pgvector extension...")
                if not create_pgvector_extension(db):
                    logger.error("Failed to create pgvector extension")
                    sys.exit(1)

                # Add embedding column to existing chunks table if it doesn't exist
                logger.info("Checking for embedding column migration...")
                if not add_embedding_column_if_missing(db):
                    logger.warning("Failed to add embedding column (table might already be up to date)")

            # Create tables
            logger.info("Creating database tables...")
            if not create_tables(db):
                logger.error("Failed to create tables")
                sys.exit(1)

            # Create indexes
            logger.info("Creating database indexes...")
            if not create_indexes(db):
                logger.error("Failed to create indexes")
                sys.exit(1)

            # Refresh collation version to fix warnings
            logger.info("Refreshing database collation version...")
            try:
                db.execute(text("ALTER DATABASE search_db REFRESH COLLATION VERSION"))
                db.commit()
                logger.info("Database collation version refreshed")
            except Exception as e:
                logger.warning(f"Could not refresh collation version (this is usually safe to ignore): {e}")

            # Create vector index if using pgvector
            if vector_backend == "pgvector":
                logger.info("Creating vector index...")
                if not create_vector_index(db):
                    logger.warning("Failed to create vector index (this may be OK if extension is missing)")

        logger.info("Database initialization completed successfully")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
