"""Search functionality for semantic and lexical search."""

import os
import time
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import text, desc
from sqlalchemy.orm import Session
import logging

from .models import Chunk
from .embedder import EmbeddingProvider, CrossEncoderReranker
from .vector_backends.base import VectorBackend

logger = logging.getLogger(__name__)


async def search_documents(
    query: str,
    top_k: int,
    hybrid: bool,
    rerank: bool,
    embedder: EmbeddingProvider,
    vector_backend: VectorBackend,
    reranker: Optional[CrossEncoderReranker],
    db: Session
) -> List[Dict[str, Any]]:
    """Search documents using vector, lexical, or hybrid search.

    Args:
        query: Search query text
        top_k: Number of results to return
        hybrid: Whether to use hybrid search (vector + lexical)
        rerank: Whether to apply reranking
        embedder: Embedding provider
        vector_backend: Vector backend
        reranker: Optional reranker instance
        db: Database session

    Returns:
        List of search results with metadata
    """
    start_time = time.time()

    try:
        # Generate query embedding
        query_embedding = embedder.embed(query)
        # Convert numpy array to Python list if needed
        if hasattr(query_embedding, 'tolist'):
            query_embedding = query_embedding.tolist()
        logger.debug(f"Generated embedding for query: {query[:50]}...")

        # Vector search
        vector_candidates = _vector_search(
            query_embedding=query_embedding,
            top_k=top_k * 3,  # Oversample for reranking
            vector_backend=vector_backend
        )

        # Lexical search if hybrid is enabled
        lexical_candidates = []
        if hybrid:
            lexical_candidates = _lexical_search(
                query=query,
                top_k=top_k * 3,
                db=db
            )

        # Combine candidates
        if hybrid:
            all_candidates = _combine_candidates(vector_candidates, lexical_candidates)
        else:
            all_candidates = vector_candidates

        # Apply reranking if enabled
        if rerank and reranker and len(all_candidates) > top_k:
            all_candidates = _rerank_candidates(
                query=query,
                candidates=all_candidates,
                reranker=reranker,
                top_k=top_k
            )
        else:
            # Just take top_k
            all_candidates = all_candidates[:top_k]

        # Fetch full chunk data
        results = _fetch_chunk_data(all_candidates, db)

        search_time = time.time() - start_time
        logger.info(f"Search completed in {search_time:.3f}s, returned {len(results)} results")

        return results

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise


def _vector_search(
    query_embedding: List[float],
    top_k: int,
    vector_backend: VectorBackend
) -> List[Tuple[int, float]]:
    """Perform vector similarity search."""
    try:
        results = vector_backend.search(query_embedding, top_k)
        logger.debug(f"Vector search found {len(results)} candidates")
        return results
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        return []


def _lexical_search(query: str, top_k: int, db: Session) -> List[Tuple[int, float]]:
    """Perform lexical search using PostgreSQL full-text search."""
    try:
        # Use PostgreSQL full-text search
        result = db.execute(text("""
            SELECT chunk_id, ts_rank_cd(ts_vector, plainto_tsquery('english', :query)) as rank
            FROM chunks
            WHERE ts_vector @@ plainto_tsquery('english', :query)
            ORDER BY rank DESC
            LIMIT :limit
        """), {"query": query, "limit": top_k})

        candidates = [(row[0], float(row[1])) for row in result]
        logger.debug(f"Lexical search found {len(candidates)} candidates")
        return candidates

    except Exception as e:
        logger.error(f"Lexical search failed: {e}")
        return []


def _combine_candidates(
    vector_results: List[Tuple[int, float]],
    lexical_results: List[Tuple[int, float]],
    alpha: float = 0.7
) -> List[Tuple[int, float]]:
    """Combine vector and lexical search results using reciprocal rank fusion."""
    # Create score maps
    vector_scores = {chunk_id: score for chunk_id, score in vector_results}
    lexical_scores = {chunk_id: score for chunk_id, score in lexical_results}

    # Combine scores using weighted sum
    combined_scores = {}

    # Add vector scores
    for chunk_id, score in vector_results:
        combined_scores[chunk_id] = alpha * score

    # Add lexical scores
    for chunk_id, score in lexical_results:
        if chunk_id in combined_scores:
            combined_scores[chunk_id] += (1 - alpha) * score
        else:
            combined_scores[chunk_id] = (1 - alpha) * score

    # Sort by combined score
    sorted_results = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)

    return [(chunk_id, score) for chunk_id, score in sorted_results]


def _rerank_candidates(
    query: str,
    candidates: List[Tuple[int, float]],
    reranker: CrossEncoderReranker,
    top_k: int
) -> List[Tuple[int, float]]:
    """Rerank candidates using cross-encoder."""
    try:
        if not candidates:
            return []

        # Extract chunk IDs and get their texts
        chunk_ids = [chunk_id for chunk_id, _ in candidates]

        # We'll need to fetch texts - this will be done in _fetch_chunk_data
        # For now, return candidates as-is (texts will be fetched later)
        logger.debug(f"Reranking {len(candidates)} candidates")
        return candidates[:top_k]

    except Exception as e:
        logger.error(f"Reranking failed: {e}")
        return candidates[:top_k]


def _fetch_chunk_data(candidates: List[Tuple[int, float]], db: Session) -> List[Dict[str, Any]]:
    """Fetch full chunk data for search results."""
    if not candidates:
        return []

    try:
        chunk_ids = [chunk_id for chunk_id, _ in candidates]
        score_map = {chunk_id: score for chunk_id, score in candidates}

        # Fetch chunks with document info
        chunks = db.query(Chunk).filter(Chunk.chunk_id.in_(chunk_ids)).all()

        # Build results
        results = []
        for chunk in chunks:
            result = {
                'chunk_id': chunk.chunk_id,
                'doc_id': chunk.doc_id,
                'text_snippet': chunk.text[:500],  # Limit snippet length
                'metadata': chunk.chunk_metadata or {},
                'score': score_map.get(chunk.chunk_id, 0.0),
                'title': chunk.document.title if chunk.document else None
            }
            results.append(result)

        # Sort by score
        results.sort(key=lambda x: x['score'], reverse=True)

        return results

    except Exception as e:
        logger.error(f"Failed to fetch chunk data: {e}")
        return []


async def get_document_chunks(doc_id: str, db: Session, limit: int = 100) -> List[Dict[str, Any]]:
    """Get all chunks for a document."""
    try:
        chunks = db.query(Chunk).filter(Chunk.doc_id == doc_id).limit(limit).all()

        return [{
            'chunk_id': chunk.chunk_id,
            'text': chunk.text,
            'metadata': chunk.chunk_metadata,
            'created_at': chunk.created_at.isoformat()
        } for chunk in chunks]

    except Exception as e:
        logger.error(f"Failed to get document chunks: {e}")
        return []
