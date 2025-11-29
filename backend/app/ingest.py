"""Document ingestion pipeline."""

import os
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import logging

from .models import Document, Chunk
from .utils import chunk_text, generate_ts_vector, estimate_token_count
from .embedder import EmbeddingProvider
from .vector_backends.base import VectorBackend

logger = logging.getLogger(__name__)


def ingest_document(
    doc_id: str,
    title: Optional[str],
    text: str,
    metadata: Dict[str, Any],
    embedder: EmbeddingProvider,
    vector_backend: VectorBackend,
    db: Session,
    chunk_size: int = 512
) -> int:
    """Ingest a document by chunking, embedding, and indexing.

    Args:
        doc_id: Unique document identifier
        title: Optional document title
        text: Document text content
        metadata: Additional metadata
        embedder: Embedding provider instance
        vector_backend: Vector backend instance
        db: Database session
        chunk_size: Maximum tokens per chunk

    Returns:
        Number of chunks created
    """
    try:
        # Create document record
        document = Document(
            doc_id=doc_id,
            title=title,
            doc_metadata=metadata
        )
        db.add(document)
        db.flush()  # Get the document ID

        # Chunk the text
        chunks = chunk_text(text, max_tokens=chunk_size)
        if not chunks:
            logger.warning(f"No chunks generated for document {doc_id}")
            return 0

        logger.info(f"Generated {len(chunks)} chunks for document {doc_id}")

        # Embed all chunks
        embeddings = embedder.embed_batch(chunks)

        # Ensure embeddings are Python lists (not numpy arrays) for pgvector
        embeddings = [list(emb) if hasattr(emb, 'tolist') else list(emb) for emb in embeddings]

        # Prepare chunk metadata
        chunk_metadata_list = []
        for i, chunk_text_content in enumerate(chunks):
            chunk_metadata_list.append({
                'chunk_id': None,  # Will be set after creation
                'doc_id': doc_id,
                'chunk_index': i,
                'text_snippet': chunk_text_content[:100]
            })

        # Add vectors to backend
        vector_ids = vector_backend.add_vectors(embeddings, chunk_metadata_list)

        # Create chunk records
        chunk_objects = []
        for i, (chunk_text_content, embedding, vector_id) in enumerate(zip(chunks, embeddings, vector_ids)):
            # Generate tsvector for full-text search
            ts_vector = generate_ts_vector(chunk_text_content)

            chunk = Chunk(
                doc_id=doc_id,
                text=chunk_text_content,
                ts_vector=ts_vector,
                chunk_metadata={
                    'chunk_index': i,
                    'token_count': estimate_token_count(chunk_text_content),
                    **metadata  # Include document-level metadata
                },
                embed_model=embedder.model_name,
                embed_version=embedder.model_version
            )

            # Set vector-specific fields
            backend_type = os.getenv("VECTOR_BACKEND", "pgvector")  # Changed default
            if backend_type == "faiss":
                chunk.vector_id = vector_id
            else:  # pgvector
                if hasattr(chunk, 'embedding'):
                    # Ensure embedding is a list of floats for pgvector
                    chunk.embedding = list(embedding) if not isinstance(embedding, list) else embedding

            chunk_objects.append(chunk)
            db.add(chunk)

        # Update metadata with actual chunk IDs
        db.flush()  # Get chunk IDs
        for i, chunk in enumerate(chunk_objects):
            chunk_metadata_list[i]['chunk_id'] = chunk.chunk_id

        # Update vector backend metadata if needed
        if hasattr(vector_backend, 'update_metadata'):
            for i, metadata_dict in enumerate(chunk_metadata_list):
                vector_backend.update_metadata(vector_ids[i], metadata_dict)

        db.commit()

        logger.info(f"Successfully ingested document {doc_id} with {len(chunks)} chunks")
        return len(chunks)

    except Exception as e:
        logger.error(f"Failed to ingest document {doc_id}: {e}")
        db.rollback()
        raise


def bulk_ingest_documents(
    documents: List[Dict[str, Any]],
    embedder: EmbeddingProvider,
    vector_backend: VectorBackend,
    db: Session
) -> Dict[str, int]:
    """Bulk ingest multiple documents.

    Args:
        documents: List of document dicts with keys: doc_id, title?, text, metadata?
        embedder: Embedding provider
        vector_backend: Vector backend
        db: Database session

    Returns:
        Dict mapping doc_id to number of chunks created
    """
    results = {}

    for doc_data in documents:
        doc_id = doc_data['doc_id']
        title = doc_data.get('title')
        text = doc_data['text']
        metadata = doc_data.get('metadata', {})

        try:
            chunk_count = ingest_document(
                doc_id=doc_id,
                title=title,
                text=text,
                metadata=metadata,
                embedder=embedder,
                vector_backend=vector_backend,
                db=db
            )
            results[doc_id] = chunk_count
        except Exception as e:
            logger.error(f"Failed to ingest document {doc_id}: {e}")
            results[doc_id] = 0

    return results
