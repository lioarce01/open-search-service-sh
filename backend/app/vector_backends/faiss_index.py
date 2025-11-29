"""FAISS vector backend implementation with HNSW indexing."""

import os
import pickle
from typing import List, Tuple, Optional, Dict, Any
import threading
import logging

from .base import VectorBackend

logger = logging.getLogger(__name__)


class FAISSIndex:
    """FAISS-based vector index with HNSW algorithm."""

    def __init__(self, dimension: int, index_path: str = "/data/faiss.index"):
        try:
            import faiss
        except ImportError:
            raise ImportError("faiss-cpu not installed. Install with: pip install faiss-cpu")

        self.dimension = dimension
        self.index_path = index_path
        self.index_file = f"{index_path}.index"
        self.metadata_file = f"{index_path}.metadata"

        # Thread lock for concurrent access
        self.lock = threading.Lock()

        # HNSW parameters
        self.M = int(os.getenv("FAISS_M", "32"))  # Number of neighbors per layer
        self.efConstruction = int(os.getenv("FAISS_EF_CONSTRUCTION", "200"))  # Construction parameter
        self.efSearch = int(os.getenv("FAISS_EF_SEARCH", "64"))  # Search parameter

        # Initialize or load index
        self.index = None
        self.metadata: Dict[int, dict] = {}  # vector_id -> metadata
        self.next_id = 0

        self._initialize_index()

    def _initialize_index(self):
        """Initialize or load the FAISS index."""
        import faiss

        if os.path.exists(self.index_file):
            logger.info(f"Loading existing FAISS index from {self.index_file}")
            self.index = faiss.read_index(self.index_file)

            # Load metadata
            if os.path.exists(self.metadata_file):
                with open(self.metadata_file, 'rb') as f:
                    self.metadata = pickle.load(f)
                    self.next_id = max(self.metadata.keys()) + 1 if self.metadata else 0
        else:
            logger.info(f"Creating new FAISS HNSW index with dimension {self.dimension}")
            # Create HNSW index
            self.index = faiss.IndexHNSWFlat(self.dimension, self.M)
            self.index.hnsw.efConstruction = self.efConstruction
            self.index.hnsw.efSearch = self.efSearch

    def add_vectors(self, vectors: List[List[float]], metadata_list: List[dict]) -> List[int]:
        """Add vectors to the index."""
        if len(vectors) != len(metadata_list):
            raise ValueError("Number of vectors must match number of metadata entries")

        with self.lock:
            import numpy as np

            # Convert to numpy array
            vectors_array = np.array(vectors, dtype=np.float32)

            # Get IDs for new vectors
            vector_ids = list(range(self.next_id, self.next_id + len(vectors)))
            self.next_id += len(vectors)

            # Add to index
            self.index.add(vectors_array)

            # Store metadata
            for i, vid in enumerate(vector_ids):
                self.metadata[vid] = metadata_list[i]

            # Periodic save (every 100 additions)
            if len(self.metadata) % 100 == 0:
                self._save_index()

            return vector_ids

    def search(self, query_vector: List[float], top_k: int) -> List[Tuple[int, float]]:
        """Search for similar vectors."""
        with self.lock:
            import numpy as np

            # Convert query to numpy array
            query_array = np.array([query_vector], dtype=np.float32)

            # Search
            distances, indices = self.index.search(query_array, min(top_k, self.index.ntotal))

            # Convert to list of (chunk_id, score) pairs
            # FAISS returns squared L2 distances, convert to similarity scores
            results = []
            for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
                if idx != -1:  # Valid result
                    # Convert distance to similarity (higher is better)
                    score = 1.0 / (1.0 + dist)

                    # FAISS idx is the vector_id we assigned during add_vectors
                    # Get the chunk_id from metadata
                    if idx in self.metadata:
                        chunk_id = self.metadata[idx].get('chunk_id')
                        if chunk_id is not None:
                            results.append((int(chunk_id), float(score)))

            return results

    def delete_vectors(self, vector_ids: List[int]) -> bool:
        """Delete vectors by their IDs. Note: FAISS doesn't support deletion, so we mark as deleted."""
        # FAISS doesn't support deletion, so we just remove from metadata
        # The vectors stay in the index but won't be returned in searches
        with self.lock:
            for vid in vector_ids:
                if vid in self.metadata:
                    del self.metadata[vid]

            self._save_index()
            return True

    def get_vector_count(self) -> int:
        """Return the number of active vectors."""
        with self.lock:
            return len(self.metadata)

    def _save_index(self):
        """Save index and metadata to disk."""
        try:
            import faiss

            # Save FAISS index
            faiss.write_index(self.index, self.index_file)

            # Save metadata
            os.makedirs(os.path.dirname(self.metadata_file), exist_ok=True)
            with open(self.metadata_file, 'wb') as f:
                pickle.dump(self.metadata, f)

            logger.debug(f"Saved FAISS index with {len(self.metadata)} vectors")
        except Exception as e:
            logger.error(f"Failed to save FAISS index: {e}")

    def save(self) -> bool:
        """Public save method."""
        with self.lock:
            self._save_index()
            return True

    def load(self) -> bool:
        """Load index from disk."""
        with self.lock:
            try:
                self._initialize_index()
                return True
            except Exception as e:
                logger.error(f"Failed to load FAISS index: {e}")
                return False

    def is_healthy(self) -> bool:
        """Check if the index is healthy."""
        try:
            return self.index is not None and self.index.is_trained
        except:
            return False

    def remove_document(self, doc_id: str) -> bool:
        """Remove all vectors for a document."""
        with self.lock:
            # Find all vector IDs for this document
            to_remove = []
            for vid, meta in self.metadata.items():
                if meta.get('doc_id') == doc_id:
                    to_remove.append(vid)

            # Remove them
            for vid in to_remove:
                del self.metadata[vid]

            self._save_index()
            logger.info(f"Removed {len(to_remove)} vectors for document {doc_id}")
            return True


class FAISSBackend(VectorBackend):
    """FAISS vector backend implementation."""

    def __init__(self, dimension: int, index_path: str = "/data/faiss.index"):
        self.faiss_index = FAISSIndex(dimension, index_path)

    def add_vectors(self, vectors: List[List[float]], metadata: List[dict]) -> List[int]:
        return self.faiss_index.add_vectors(vectors, metadata)

    def search(self, query_vector: List[float], top_k: int) -> List[Tuple[int, float]]:
        return self.faiss_index.search(query_vector, top_k)

    def delete_vectors(self, vector_ids: List[int]) -> bool:
        return self.faiss_index.delete_vectors(vector_ids)

    def get_vector_count(self) -> int:
        return self.faiss_index.get_vector_count()

    def save(self) -> bool:
        return self.faiss_index.save()

    def load(self) -> bool:
        return self.faiss_index.load()

    def is_healthy(self) -> bool:
        return self.faiss_index.is_healthy()

    def remove_document(self, doc_id: str) -> bool:
        return self.faiss_index.remove_document(doc_id)
