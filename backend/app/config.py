"""Configuration management for the search service."""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator
import logging

logger = logging.getLogger(__name__)


class DatabaseConfig(BaseModel):
    """Database configuration."""

    url: str = Field(..., description="PostgreSQL connection string")
    pool_size: int = Field(10, description="Connection pool size")
    max_overflow: int = Field(20, description="Maximum overflow connections")


class VectorConfig(BaseModel):
    """Vector backend configuration."""

    backend: str = Field("faiss", description="Vector backend: faiss or pgvector")
    faiss_index_path: str = Field("/data/faiss", description="FAISS index path")
    faiss_m: int = Field(32, description="FAISS HNSW M parameter")
    faiss_ef_construction: int = Field(200, description="FAISS HNSW efConstruction")
    faiss_ef_search: int = Field(64, description="FAISS HNSW efSearch")


class EmbeddingConfig(BaseModel):
    """Embedding provider configuration."""

    provider: str = Field("local", description="Embedding provider: local or openai")
    model: str = Field("all-mpnet-base-v2", description="Local model name")
    dimension: int = Field(768, description="Embedding dimension")
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    openai_model: str = Field("text-embedding-3-small", description="OpenAI model name")


class SearchConfig(BaseModel):
    """Search configuration."""

    chunk_tokens: int = Field(512, description="Maximum tokens per chunk")
    top_k: int = Field(5, description="Default number of search results to return", ge=1, le=50)
    reranker_enabled: bool = Field(False, description="Enable cross-encoder reranking")
    reranker_model: str = Field("cross-encoder/ms-marco-MiniLM-L-6-v2", description="Reranker model")


class ServiceConfig(BaseModel):
    """Complete service configuration."""

    database: DatabaseConfig
    vector: VectorConfig
    embedding: EmbeddingConfig
    search: SearchConfig

    @validator('vector')
    def validate_vector_config(cls, v, values):
        """Validate vector configuration based on backend type."""
        if v.backend not in ['faiss', 'pgvector']:
            raise ValueError("Vector backend must be 'faiss' or 'pgvector'")
        return v

    @validator('embedding')
    def validate_embedding_config(cls, v, values):
        """Validate embedding configuration."""
        if v.provider not in ['local', 'openai']:
            raise ValueError("Embedding provider must be 'local' or 'openai'")
        if v.provider == 'openai' and not v.openai_api_key:
            raise ValueError("OpenAI API key required when using OpenAI provider")
        return v


class ConfigManager:
    """Configuration manager with persistence."""

    def __init__(self, config_file: str = "config.json"):
        self.config_file = Path(config_file)
        self._config: Optional[ServiceConfig] = None

    def load_config(self) -> ServiceConfig:
        """Load configuration from file or create default."""
        # Always reload from file to ensure dynamic config changes are picked up
        # Try to load from file
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                config = ServiceConfig(**data)
                logger.info(f"Loaded configuration from {self.config_file}")
                return config
            except Exception as e:
                logger.warning(f"Failed to load config from {self.config_file}: {e}")

        # Create default configuration from environment
        config = self._create_default_config()
        return config

    def save_config(self, config: ServiceConfig) -> bool:
        """Save configuration to file."""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(config.dict(), f, indent=2)
            logger.info(f"Saved configuration to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save config to {self.config_file}: {e}")
            return False

    def update_config(self, updates: Dict[str, Any]) -> ServiceConfig:
        """Update configuration with partial updates."""
        current = self.load_config()

        # Convert current config to dict for merging
        config_dict = current.dict()

        # Deep merge updates
        self._deep_update(config_dict, updates)

        # Create new config and validate
        new_config = ServiceConfig(**config_dict)
        self.save_config(new_config)
        return new_config

    def _deep_update(self, base: Dict[str, Any], updates: Dict[str, Any]) -> None:
        """Deep update dictionary."""
        for key, value in updates.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                self._deep_update(base[key], value)
            else:
                base[key] = value

    def _create_default_config(self) -> ServiceConfig:
        """Create default configuration from environment variables."""
        return ServiceConfig(
            database=DatabaseConfig(
                url=os.getenv("DATABASE_URL", "postgresql://search_user:search_password@postgres:5432/search_db"),
                pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
                max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20"))
            ),
            vector=VectorConfig(
                backend=os.getenv("VECTOR_BACKEND", "faiss"),
                faiss_index_path=os.getenv("FAISS_INDEX_PATH", "/data/faiss"),
                faiss_m=int(os.getenv("FAISS_M", "32")),
                faiss_ef_construction=int(os.getenv("FAISS_EF_CONSTRUCTION", "200")),
                faiss_ef_search=int(os.getenv("FAISS_EF_SEARCH", "64"))
            ),
            embedding=EmbeddingConfig(
                provider=os.getenv("EMBEDDING_PROVIDER", "local"),
                model=os.getenv("EMBED_MODEL", "all-mpnet-base-v2"),
                dimension=int(os.getenv("EMBED_DIM", "768")),
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                openai_model=os.getenv("OPENAI_MODEL", "text-embedding-3-small")
            ),
            search=SearchConfig(
                chunk_tokens=int(os.getenv("CHUNK_TOKENS", "512")),
                top_k=int(os.getenv("TOP_K", "5")),
                reranker_enabled=os.getenv("RERANKER_ENABLED", "false").lower() == "true",
                reranker_model=os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
            )
        )

    def validate_database_connection(self, db_url: str) -> Dict[str, Any]:
        """Validate database connection string."""
        result = {
            "valid": False,
            "message": "",
            "details": {}
        }

        try:
            # Parse connection string
            if not db_url.startswith("postgresql://"):
                result["message"] = "Connection string must start with 'postgresql://'"
                return result

            # Try to extract components
            parts = db_url.replace("postgresql://", "").split("@")
            if len(parts) != 2:
                result["message"] = "Invalid connection string format"
                return result

            auth_part, host_part = parts
            auth_parts = auth_part.split(":")
            if len(auth_parts) != 2:
                result["message"] = "Invalid authentication format (user:password)"
                return result

            user, password = auth_parts
            host_db_parts = host_part.split("/")
            if len(host_db_parts) != 2:
                result["message"] = "Invalid host/database format"
                return result

            host_port, database = host_db_parts
            host_port_parts = host_port.split(":")
            host = host_port_parts[0]
            port = host_port_parts[1] if len(host_port_parts) > 1 else "5432"

            result["valid"] = True
            result["message"] = "Connection string format is valid"
            result["details"] = {
                "user": user,
                "host": host,
                "port": port,
                "database": database,
                "has_password": bool(password)
            }

        except Exception as e:
            result["message"] = f"Error parsing connection string: {str(e)}"

        return result


# Global config manager instance
config_manager = ConfigManager()


def get_config() -> ServiceConfig:
    """Get current configuration."""
    return config_manager.load_config()


def update_config(updates: Dict[str, Any]) -> ServiceConfig:
    """Update configuration."""
    return config_manager.update_config(updates)
