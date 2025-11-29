#!/usr/bin/env python3
"""Database initialization script for the semantic search service."""

import os
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from sqlalchemy import text
from app.db import get_db
from app.utils import (
    create_pgvector_extension, create_tables, create_indexes,
    create_vector_index, add_embedding_column_if_missing,
    create_vector_index_separate_connection, create_composite_indexes_separate_connection
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Initialize the database with tables, extensions, and indexes."""
    print("=== DATABASE INITIALIZATION STARTED ===")
    try:
        logger.info("Starting database initialization...")
        print("Connecting to database...")

        # Get vector backend configuration
        vector_backend = os.getenv("VECTOR_BACKEND", "faiss")
        print(f"Using vector backend: {vector_backend}")

        with get_db() as db:
            # Create pgvector extension if using pgvector
            if vector_backend == "pgvector":
                print("Setting up pgvector...")
                logger.info("Creating pgvector extension...")
                if not create_pgvector_extension(db):
                    logger.error("Failed to create pgvector extension")
                    sys.exit(1)

            # Create tables FIRST (before trying to modify them)
            print("Creating tables...")
            logger.info("Creating database tables...")
            if not create_tables(db):
                logger.error("Failed to create tables")
                sys.exit(1)

            # Now add embedding column to existing chunks table if using pgvector
            if vector_backend == "pgvector":
                print("Checking embedding column...")
                logger.info("Checking for embedding column migration...")
                if not add_embedding_column_if_missing(db):
                    logger.warning("Failed to add embedding column (table might already be up to date)")

            # Create indexes
            print("Creating indexes...")
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

            # Commit any pending changes before creating indexes
            print("Committing changes...")
            db.commit()

            # Create vector index if using pgvector (must be done outside transaction)
            if vector_backend == "pgvector":
                print("Creating vector index...")
                logger.info("Creating vector index...")
                # Create index in a separate connection (not in transaction)
                if not create_vector_index_separate_connection():
                    logger.warning("Failed to create vector index (this may be OK if extension is missing)")
                else:
                    print("Vector index created successfully!")

            # Create composite indexes (also outside transaction to avoid conflicts)
            print("Creating composite indexes...")
            logger.info("Creating composite indexes...")
            if not create_composite_indexes_separate_connection():
                logger.warning("Failed to create composite indexes")
            else:
                print("Composite indexes created successfully!")

            # Optimize PostgreSQL settings (these work per-session, not globally)
            logger.info("Note: PostgreSQL settings optimization requires database superuser access")
            logger.info("Consider running: ALTER SYSTEM SET work_mem = '256MB'; etc.")

        print("=== DATABASE INITIALIZATION COMPLETED SUCCESSFULLY ===")
        logger.info("Database initialization and optimization completed successfully")

    except Exception as e:
        print(f"=== DATABASE INITIALIZATION FAILED: {e} ===")
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
