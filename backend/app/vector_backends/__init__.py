# Vector backends package

import os
from typing import Optional
from .base import VectorBackend
from .faiss_index import FAISSBackend
from .pgvector_helper import PgVectorBackendWrapper


def get_vector_backend(dimension: int, db_session_factory=None) -> VectorBackend:
    """Factory function to get the configured vector backend."""
    from ..config import get_config
    config = get_config()

    backend_type = config.vector.backend.lower()

    if backend_type == "faiss":
        index_path = config.vector.faiss_index_path
        return FAISSBackend(
            dimension=dimension,
            index_path=index_path,
            M=config.vector.faiss_m,
            ef_construction=config.vector.faiss_ef_construction,
            ef_search=config.vector.faiss_ef_search
        )
    elif backend_type == "pgvector":
        return PgVectorBackendWrapper(dimension=dimension, db_session_factory=db_session_factory)
    else:
        raise ValueError(f"Unknown vector backend: {backend_type}")
