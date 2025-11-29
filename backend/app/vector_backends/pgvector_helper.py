"""pgvector backend implementation for PostgreSQL vector storage."""

import os
from typing import List, Tuple, Optional, Dict, Any
from sqlalchemy import text
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


class PgVectorBackend:
    """pgvector-based vector backend using PostgreSQL."""

    def __init__(self, dimension: int, db_session_factory=None):
        self.dimension = dimension
        self.db_session_factory = db_session_factory
        self.table_name = "chunks"  # Use the chunks table directly

        # Check if pgvector is available
        self._ensure_pgvector()

    def _ensure_pgvector(self):
        """Ensure pgvector extension is available."""
        try:
            with self._get_db() as db:
                # Check if extension exists
                result = db.execute(text("SELECT * FROM pg_extension WHERE extname = 'vector'"))
                if not result.fetchone():
                    logger.warning("pgvector extension not found. Run init_db.py to create it.")
                    return

                logger.info("pgvector extension available")

        except Exception as e:
            logger.error(f"pgvector check failed: {e}")

    def _create_hnsw_index(self, db):
        """Create HNSW index if it doesn't exist."""
        try:
            # Check if HNSW index already exists
            index_check = db.execute(text("""
                SELECT 1 FROM pg_indexes
                WHERE tablename = :table_name AND indexname = :index_name
            """), {"table_name": self.table_name, "index_name": f"{self.table_name}_hnsw_idx"})

            if index_check.fetchone():
                logger.info("HNSW vector index already exists")
                return

            # Create HNSW index for optimal ANN performance
            db.execute(text(f"""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS {self.table_name}_hnsw_idx
                ON {self.table_name}
                USING hnsw (embedding vector_cosine_ops)
            """))
            db.commit()
            logger.info("HNSW vector index created for optimal ANN performance")

        except Exception as e:
            logger.warning(f"Could not create HNSW index (this may be OK if index already exists): {e}")

    def _get_db(self) -> Session:
        """Get database session."""
        if self.db_session_factory:
            return self.db_session_factory()
        else:
            from ..db import get_db
            # This is a context manager, so we need to handle it differently
            raise RuntimeError("Database session factory not provided")

    def add_vectors(self, vectors: List[List[float]], metadata: List[dict]) -> List[int]:
        """Add vectors to the database. Note: This is handled by the ingestion process."""
        # For pgvector, vectors are stored directly in the chunks table
        # So this method mainly validates and returns placeholder IDs
        # The actual insertion happens in ingest.py
        logger.warning("add_vectors called on PgVectorBackend - vectors should be inserted via ingest.py")
        return list(range(len(vectors)))

    def search(self, query_vector: List[float], top_k: int, doc_ids: Optional[List[str]] = None) -> List[Tuple[int, float]]:
        """Search for similar vectors using optimized pgvector queries."""
        try:
            with self._get_db() as db:
                # Convert numpy array to Python list if needed
                if hasattr(query_vector, 'tolist'):  # numpy array
                    query_vector = query_vector.tolist()

                # Use pgvector native array syntax for better performance
                vector_str = '[' + ','.join(f"{x:.6f}" for x in query_vector) + ']'

                # Oversample for better recall, then limit to top_k
                limit = min(top_k * 3, 1000)  # Cap at 1000 for performance

                if doc_ids:
                    # Optimized query with document filtering
                    placeholders = ", ".join(f"'{doc_id}'" for doc_id in doc_ids)
                    query = f"""
                        SELECT chunk_id, (1.0 - (embedding <=> '{vector_str}'::vector)) as similarity
                        FROM {self.table_name}
                        WHERE embedding IS NOT NULL
                          AND doc_id IN ({placeholders})
                        ORDER BY embedding <=> '{vector_str}'::vector
                        LIMIT {limit}
                    """
                else:
                    # Direct vector search - most common case
                    query = f"""
                        SELECT chunk_id, (1.0 - (embedding <=> '{vector_str}'::vector)) as similarity
                        FROM {self.table_name}
                        WHERE embedding IS NOT NULL
                        ORDER BY embedding <=> '{vector_str}'::vector
                        LIMIT {limit}
                    """

                result = db.execute(text(query))

                # Convert to (chunk_id, score) pairs - limit to top_k after oversampling
                results = []
                for row in result:
                    chunk_id, similarity = row
                    results.append((int(chunk_id), float(similarity)))

                # Return only top_k results (oversampling was for better recall)
                return results[:top_k]

        except Exception as e:
            logger.error(f"pgvector search failed: {e}")
            return []

    def delete_vectors(self, vector_ids: List[int]) -> bool:
        """Delete vectors by chunk IDs."""
        try:
            with self._get_db() as db:
                # Delete chunks by chunk_id
                placeholders = ", ".join(str(vid) for vid in vector_ids)
                query = f"DELETE FROM {self.table_name} WHERE chunk_id IN ({placeholders})"
                db.execute(text(query))
                db.commit()
                return True
        except Exception as e:
            logger.error(f"Vector deletion failed: {e}")
            return False

    def get_vector_count(self) -> int:
        """Return the number of vectors in the database."""
        try:
            with self._get_db() as db:
                result = db.execute(text(f"SELECT COUNT(*) FROM {self.table_name} WHERE embedding IS NOT NULL"))
                return result.scalar() or 0
        except Exception as e:
            logger.error(f"Vector count query failed: {e}")
            return 0

    def save(self) -> bool:
        """No-op for pgvector since data is persisted in PostgreSQL."""
        return True

    def load(self) -> bool:
        """No-op for pgvector since data is loaded from PostgreSQL."""
        return True

    def is_healthy(self) -> bool:
        """Check if pgvector is working."""
        try:
            with self._get_db() as db:
                # Try a simple vector operation
                result = db.execute(text("SELECT '[1,2,3]'::vector(3) <=> '[1,2,3]'::vector(3)"))
                return result.fetchone() is not None
        except Exception:
            return False

    def remove_document(self, doc_id: str) -> bool:
        """Remove all vectors for a document."""
        try:
            with self._get_db() as db:
                # Delete all chunks for this document
                db.execute(text(f"DELETE FROM {self.table_name} WHERE doc_id = :doc_id"), {"doc_id": doc_id})
                db.commit()
                logger.info(f"Removed vectors for document {doc_id}")
                return True
        except Exception as e:
            logger.error(f"Document removal failed: {e}")
            return False

    def create_index(self, index_name: str = "chunks_hnsw_idx", use_hnsw: bool = True):
        """Create vector index on the embedding column. Defaults to HNSW for optimal performance."""
        try:
            with self._get_db() as db:
                # Check if index already exists
                result = db.execute(text("""
                    SELECT 1 FROM pg_indexes
                    WHERE tablename = :table_name AND indexname = :index_name
                """), {"table_name": self.table_name, "index_name": index_name})

                if not result.fetchone():
                    if use_hnsw:
                        # Create HNSW index for optimal ANN performance
                        db.execute(text(f"""
                            CREATE INDEX CONCURRENTLY {index_name}
                            ON {self.table_name}
                            USING hnsw (embedding vector_cosine_ops)
                        """))
                        logger.info(f"Created HNSW vector index: {index_name}")
                    else:
                        # Create IVFFlat index (legacy)
                        db.execute(text(f"""
                            CREATE INDEX CONCURRENTLY {index_name}
                            ON {self.table_name}
                            USING ivfflat (embedding vector_cosine_ops)
                            WITH (lists = 100)
                        """))
                        logger.info(f"Created IVFFlat vector index: {index_name}")

                    db.commit()
                    return True
                else:
                    logger.info(f"Vector index {index_name} already exists")
                    return True
        except Exception as e:
            logger.error(f"Failed to create vector index: {e}")
            return False

    def get_documents_with_vectors(self) -> List[str]:
        """Get list of document IDs that have vectors."""
        try:
            with self._get_db() as db:
                result = db.execute(text(f"""
                    SELECT DISTINCT doc_id FROM {self.table_name}
                    WHERE embedding IS NOT NULL
                """))

                return [row[0] for row in result]
        except Exception as e:
            logger.error(f"Failed to get documents with vectors: {e}")
            return []


class PgVectorBackendWrapper:
    """Wrapper to match the VectorBackend interface."""

    def __init__(self, dimension: int, db_session_factory=None):
        self.backend = PgVectorBackend(dimension, db_session_factory)

    def add_vectors(self, vectors: List[List[float]], metadata: List[dict]) -> List[int]:
        return self.backend.add_vectors(vectors, metadata)

    def search(self, query_vector: List[float], top_k: int) -> List[Tuple[int, float]]:
        return self.backend.search(query_vector, top_k)

    def delete_vectors(self, vector_ids: List[int]) -> bool:
        return self.backend.delete_vectors(vector_ids)

    def get_vector_count(self) -> int:
        return self.backend.get_vector_count()

    def save(self) -> bool:
        return self.backend.save()

    def load(self) -> bool:
        return self.backend.load()

    def is_healthy(self) -> bool:
        return self.backend.is_healthy()

    def remove_document(self, doc_id: str) -> bool:
        return self.backend.remove_document(doc_id)
