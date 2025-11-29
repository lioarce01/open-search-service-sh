"""Abstract base class for vector backends."""

from abc import ABC, abstractmethod
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class VectorBackend(ABC):
    """Abstract base class for vector database backends."""

    @abstractmethod
    def add_vectors(self, vectors: List[List[float]], metadata: List[dict]) -> List[int]:
        """Add vectors to the index and return their IDs."""
        pass

    @abstractmethod
    def search(self, query_vector: List[float], top_k: int) -> List[Tuple[int, float]]:
        """Search for similar vectors and return (id, score) pairs."""
        pass

    @abstractmethod
    def delete_vectors(self, vector_ids: List[int]) -> bool:
        """Delete vectors by their IDs."""
        pass

    @abstractmethod
    def get_vector_count(self) -> int:
        """Return the total number of vectors in the index."""
        pass

    @abstractmethod
    def save(self) -> bool:
        """Save the index to persistent storage."""
        pass

    @abstractmethod
    def load(self) -> bool:
        """Load the index from persistent storage."""
        pass

    @abstractmethod
    def is_healthy(self) -> bool:
        """Check if the vector backend is healthy."""
        pass

    def remove_document(self, doc_id: str) -> bool:
        """Remove all vectors for a document. Default implementation does nothing."""
        logger.warning(f"remove_document not implemented for {self.__class__.__name__}")
        return False
