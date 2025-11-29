# Vector backends package

import os
from typing import Optional
from .base import VectorBackend
from .faiss_index import FAISSBackend
from .pgvector_helper import PgVectorBackendWrapper


def get_vector_backend(dimension: int, db_session_factory=None) -> VectorBackend:
    """Factory function to get the configured vector backend."""
    backend_type = os.getenv("VECTOR_BACKEND", "faiss").lower()

    if backend_type == "faiss":
        index_path = os.getenv("FAISS_INDEX_PATH", "/data/faiss")
        return FAISSBackend(dimension=dimension, index_path=index_path)
    elif backend_type == "pgvector":
        return PgVectorBackendWrapper(dimension=dimension, db_session_factory=db_session_factory)
    else:
        raise ValueError(f"Unknown vector backend: {backend_type}")
