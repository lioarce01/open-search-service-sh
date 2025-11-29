"""Embedding provider abstraction for different embedding models."""

import os
from abc import ABC, abstractmethod
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimension."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model name."""
        pass

    @property
    @abstractmethod
    def model_version(self) -> str:
        """Return the model version."""
        pass

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts."""
        pass


class SentenceTransformerProvider(EmbeddingProvider):
    """Embedding provider using sentence-transformers."""

    def __init__(self, model_name: str = "all-mpnet-base-v2"):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError("sentence-transformers not installed. Install with: pip install sentence-transformers")

        logger.info(f"Loading sentence-transformers model: {model_name}")
        self._model = SentenceTransformer(model_name)
        self._model_name = model_name
        self._model_version = "1.0.0"  # Could be more dynamic

    @property
    def dimension(self) -> int:
        return self._model.get_sentence_embedding_dimension()

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def model_version(self) -> str:
        return self._model_version

    def embed(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        return self._model.encode(text, convert_to_list=True)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts."""
        return self._model.encode(texts, convert_to_list=True)


class OpenAIProvider(EmbeddingProvider):
    """Embedding provider using OpenAI API."""

    def __init__(self, api_key: Optional[str] = None, model: str = "text-embedding-3-small"):
        try:
            import openai
        except ImportError:
            raise ImportError("openai not installed. Install with: pip install openai")

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable or api_key parameter required")

        self.client = openai.OpenAI(api_key=self.api_key)
        self._model = model

        # Set dimensions based on model
        if model == "text-embedding-3-small":
            self._dimension = 1536
        elif model == "text-embedding-3-large":
            self._dimension = 3072
        elif model == "text-embedding-ada-002":
            self._dimension = 1536
        else:
            # Default to 1536, will be updated on first call
            self._dimension = 1536

        self._model_version = "1.0.0"

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return f"openai/{self._model}"

    @property
    def model_version(self) -> str:
        return self._model_version

    def embed(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        try:
            response = self.client.embeddings.create(
                input=text,
                model=self._model
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"OpenAI embedding failed: {e}")
            raise

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts."""
        try:
            response = self.client.embeddings.create(
                input=texts,
                model=self._model
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error(f"OpenAI batch embedding failed: {e}")
            raise


def get_embedder() -> EmbeddingProvider:
    """Factory function to get the configured embedding provider."""
    provider = os.getenv("EMBEDDING_PROVIDER", "local").lower()

    if provider == "openai":
        model = os.getenv("OPENAI_MODEL", "text-embedding-3-small")
        return OpenAIProvider(model=model)
    elif provider == "local":
        model = os.getenv("EMBED_MODEL", "all-mpnet-base-v2")
        return SentenceTransformerProvider(model_name=model)
    else:
        raise ValueError(f"Unknown embedding provider: {provider}")


class CrossEncoderReranker:
    """Cross-encoder for reranking search results."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        try:
            from sentence_transformers import CrossEncoder
        except ImportError:
            raise ImportError("sentence-transformers not installed")

        logger.info(f"Loading cross-encoder model: {model_name}")
        self.model = CrossEncoder(model_name)

    def rerank(self, query: str, texts: List[str]) -> List[float]:
        """Rerank texts based on relevance to query."""
        pairs = [[query, text] for text in texts]
        scores = self.model.predict(pairs)
        return scores.tolist()


def get_reranker() -> CrossEncoderReranker:
    """Get the configured reranker."""
    model = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
    return CrossEncoderReranker(model_name=model)
