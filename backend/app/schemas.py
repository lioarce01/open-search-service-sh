"""Pydantic schemas for API request/response validation."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from .config import config_manager


class IngestRequest(BaseModel):
    """Request schema for document ingestion."""

    doc_id: str = Field(..., description="Unique identifier for the document")
    title: Optional[str] = Field(None, description="Optional title for the document")
    text: str = Field(..., description="The text content to be ingested")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional metadata as JSON")


class IngestResponse(BaseModel):
    """Response schema for document ingestion."""

    doc_id: str
    chunk_count: int
    message: str


class SearchRequest(BaseModel):
    """Request schema for search queries."""

    q: str = Field(..., description="Search query text")
    top_k: int = Field(default_factory=lambda: config_manager.load_config().search.top_k, description="Number of results to return", ge=1, le=50)
    offset: int = Field(0, description="Offset for pagination", ge=0)
    limit: int = Field(default_factory=lambda: config_manager.load_config().search.top_k, description="Limit for pagination", ge=1, le=50)
    hybrid: bool = Field(True, description="Whether to use hybrid search (vector + text)")
    rerank: bool = Field(True, description="Whether to apply reranking")


class SearchResult(BaseModel):
    """Schema for individual search results."""

    chunk_id: int
    doc_id: str
    text_snippet: str
    metadata: Dict[str, Any]
    score: float
    title: Optional[str] = None


class SearchResponse(BaseModel):
    """Response schema for search queries."""

    query: str
    results: List[SearchResult]
    total_count: int
    offset: int
    limit: int
    search_time_ms: float


class StatusResponse(BaseModel):
    """Response schema for health check."""

    status: str
    database: str
    vector_backend: str
    embedding_provider: str
    reranker_enabled: bool


class DocumentResponse(BaseModel):
    """Response schema for document retrieval."""

    doc_id: str
    title: Optional[str]
    metadata: Dict[str, Any]
    created_at: str
    chunk_count: int


class MetricsResponse(BaseModel):
    """Response schema for metrics endpoint."""

    total_documents: int
    total_chunks: int
    vector_backend: str
    embedding_provider: str
    embed_model: str
    embed_version: str


class ErrorResponse(BaseModel):
    """Schema for error responses."""

    error: str
    detail: Optional[str] = None


class DatabaseConfig(BaseModel):
    """Database configuration schema."""

    url: str
    pool_size: int = 10
    max_overflow: int = 20


class VectorConfig(BaseModel):
    """Vector backend configuration schema."""

    backend: str
    faiss_index_path: str = "/data/faiss"
    faiss_m: int = 32
    faiss_ef_construction: int = 200
    faiss_ef_search: int = 64


class EmbeddingConfig(BaseModel):
    """Embedding provider configuration schema."""

    provider: str
    model: str = "all-mpnet-base-v2"
    dimension: int = 768
    openai_api_key: Optional[str] = None
    openai_model: str = "text-embedding-3-small"


class SearchConfig(BaseModel):
    """Search configuration schema."""

    chunk_tokens: int = 512
    top_k: int = Field(5, description="Default number of search results to return", ge=1, le=50)
    reranker_enabled: bool = False
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class ServiceConfig(BaseModel):
    """Complete service configuration schema."""

    database: DatabaseConfig
    vector: VectorConfig
    embedding: EmbeddingConfig
    search: SearchConfig


class ConfigUpdateRequest(BaseModel):
    """Request schema for configuration updates."""

    database: Optional[DatabaseConfig] = None
    vector: Optional[VectorConfig] = None
    embedding: Optional[EmbeddingConfig] = None
    search: Optional[SearchConfig] = None


class DatabaseValidationResponse(BaseModel):
    """Response schema for database connection validation."""

    valid: bool
    message: str
    details: Dict[str, Any] = {}
