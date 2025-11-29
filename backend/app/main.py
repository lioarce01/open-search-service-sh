"""FastAPI application for semantic search service."""

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Form, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .db import check_database_health, get_table_counts, SessionLocal
from .models import Document
from .schemas import (
    IngestRequest, IngestResponse, SearchRequest, SearchResponse,
    StatusResponse, DocumentResponse, MetricsResponse, ErrorResponse,
    ServiceConfig, ConfigUpdateRequest, DatabaseValidationResponse
)
from .config import get_config, update_config

from .embedder import get_embedder, get_reranker
from .vector_backends import get_vector_backend
from .ingest import ingest_document
from .search import search_documents


def extract_text_from_file(file_data: bytes, filename: str) -> str:
    """Extract text content from various file types."""
    import os

    # Get file extension
    _, ext = os.path.splitext(filename.lower())

    if ext == '.pdf':
        try:
            from PyPDF2 import PdfReader
            from io import BytesIO

            pdf_file = BytesIO(file_data)
            pdf_reader = PdfReader(pdf_file)

            text_content = []
            for page in pdf_reader.pages:
                text_content.append(page.extract_text())

            return '\n'.join(text_content)
        except ImportError:
            raise HTTPException(status_code=500, detail="PDF processing not available. Install PyPDF2.")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to extract text from PDF: {str(e)}")

    elif ext in ['.txt', '.md']:
        # For text files, just decode as UTF-8
        try:
            return file_data.decode('utf-8')
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File encoding not supported. Please use UTF-8 encoded text files.")

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}. Supported: .txt, .md, .pdf")

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global variables for vector backend and embedder
vector_backend = None
embedder = None
reranker = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    # Startup
    logger.info("Starting semantic search service...")

    try:
        # Initialize database connection
        if not check_database_health():
            logger.error("Database connection failed during startup")
            raise RuntimeError("Database connection failed")

        # Initialize embedder
        global embedder
        embedder = get_embedder()

        # Initialize vector backend
        global vector_backend
        vector_backend = get_vector_backend(
            dimension=embedder.dimension,
            db_session_factory=lambda: SessionLocal()
        )

        # Initialize reranker if enabled
        global reranker
        if os.getenv("RERANKER_ENABLED", "false").lower() == "true":
            reranker = get_reranker()

        logger.info("Service started successfully")

    except Exception as e:
        logger.error(f"Failed to start service: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down semantic search service...")

    try:
        # Save vector backend state
        if vector_backend:
            vector_backend.save()
        logger.info("Service shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI app
app = FastAPI(
    title="Semantic Search Service",
    description="RAG-style semantic and lexical search service",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/status", response_model=StatusResponse)
async def get_status():
    """Health check endpoint."""
    try:
        db_healthy = check_database_health()

        return StatusResponse(
            status="healthy" if db_healthy else "unhealthy",
            database="connected" if db_healthy else "disconnected",
            vector_backend=os.getenv("VECTOR_BACKEND", "faiss"),
            embedding_provider=os.getenv("EMBEDDING_PROVIDER", "local"),
            reranker_enabled=os.getenv("RERANKER_ENABLED", "false").lower() == "true"
        )
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(status_code=500, detail="Status check failed")


@app.post("/ingest", response_model=IngestResponse)
async def ingest_endpoint(
    background_tasks: BackgroundTasks,
    doc_id: str = Form(...),
    title: Optional[str] = Form(None),
    text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    metadata: Optional[str] = Form(None),  # JSON string
    sync: bool = Form(False),  # New parameter to control sync/async behavior
):
    """Ingest a document for search indexing."""
    # Create database session
    from .db import SessionLocal
    db = SessionLocal()

    try:
        # Validate input
        if not text and not file:
            raise HTTPException(status_code=400, detail="Either 'text' or 'file' must be provided")

        # Parse metadata
        parsed_metadata = {}
        if metadata:
            try:
                import json
                parsed_metadata = json.loads(metadata)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON in metadata")

        # Read file content if provided
        content = text or ""
        if file:
            file_data = await file.read()
            content = extract_text_from_file(file_data, file.filename)

        if not content.strip():
            raise HTTPException(status_code=400, detail="Document content cannot be empty")

        # Check if document already exists
        existing_doc = db.query(Document).filter(Document.doc_id == doc_id).first()
        if existing_doc:
            raise HTTPException(status_code=409, detail=f"Document with doc_id '{doc_id}' already exists")

        if sync:
            # Synchronous processing
            chunk_count = process_ingestion_sync(
                doc_id=doc_id,
                title=title,
                text=content,
                metadata=parsed_metadata,
                embedder=embedder,
                vector_backend=vector_backend
            )
            return IngestResponse(
                doc_id=doc_id,
                chunk_count=chunk_count,
                message="Document ingested successfully"
            )
        else:
            # Background ingestion
            background_tasks.add_task(
                process_ingestion,
                doc_id=doc_id,
                title=title,
                text=content,
                metadata=parsed_metadata,
                embedder=embedder,
                vector_backend=vector_backend
            )

            return IngestResponse(
                doc_id=doc_id,
                chunk_count=0,  # Will be updated after processing
                message="Document ingestion started"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ingestion request failed: {e}")
        raise HTTPException(status_code=500, detail="Ingestion failed")
    finally:
        db.close()


def process_ingestion(doc_id: str, title: Optional[str], text: str, metadata: Dict[str, Any], embedder, vector_backend):
    """Background task to process document ingestion."""
    try:
        logger.info(f"Starting ingestion for document {doc_id}")

        # Create a new database session for the background task
        from .db import SessionLocal
        db = SessionLocal()
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
            db.commit()  # Commit the transaction
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()

        logger.info(f"Completed ingestion for document {doc_id} with {chunk_count} chunks")

    except Exception as e:
        logger.error(f"Ingestion failed for document {doc_id}: {e}")


def process_ingestion_sync(doc_id: str, title: Optional[str], text: str, metadata: Dict[str, Any], embedder, vector_backend) -> int:
    """Synchronous document ingestion processing."""
    try:
        logger.info(f"Starting synchronous ingestion for document {doc_id}")

        # Create a database session
        from .db import SessionLocal
        db = SessionLocal()
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
            db.commit()  # Commit the transaction
            logger.info(f"Completed synchronous ingestion for document {doc_id} with {chunk_count} chunks")
            return chunk_count
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Synchronous ingestion failed for document {doc_id}: {e}")
        raise


@app.post("/search", response_model=SearchResponse)
async def search_documents_endpoint(request: SearchRequest):
    """Search documents using semantic and/or lexical search."""
    db = SessionLocal()
    try:
        start_time = time.time()

        if not request.q.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        results = await search_documents(
            query=request.q,
            top_k=request.top_k,
            hybrid=request.hybrid,
            rerank=request.rerank,
            embedder=embedder,
            vector_backend=vector_backend,
            reranker=reranker,
            db=db
        )

        search_time = (time.time() - start_time) * 1000

        return SearchResponse(
            query=request.q,
            results=results,
            total_results=len(results),
            search_time_ms=search_time
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail="Search failed")
    finally:
        db.close()


@app.delete("/document/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document and all its chunks."""
    db = SessionLocal()
    try:
        # Check if document exists
        document = db.query(Document).filter(Document.doc_id == doc_id).first()
        if not document:
            raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found")

        # Delete document (cascade will delete chunks)
        db.delete(document)
        db.commit()

        # Remove from vector index if needed
        if vector_backend:
            vector_backend.remove_document(doc_id)

        return {"message": f"Document '{doc_id}' deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document deletion failed: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Document deletion failed")
    finally:
        db.close()


@app.get("/docs/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: str):
    """Get document metadata."""
    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.doc_id == doc_id).first()
        if not document:
            raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found")

        chunk_count = len(document.chunks)

        return DocumentResponse(
            doc_id=document.doc_id,
            title=document.title,
            metadata=document.doc_metadata or {},
            created_at=document.created_at.isoformat(),
            chunk_count=chunk_count
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="Document retrieval failed")
    finally:
        db.close()


@app.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    """Get service metrics."""
    try:
        counts = get_table_counts()

        return MetricsResponse(
            total_documents=counts["documents"],
            total_chunks=counts["chunks"],
            vector_backend=os.getenv("VECTOR_BACKEND", "faiss"),
            embedding_provider=os.getenv("EMBEDDING_PROVIDER", "local"),
            embed_model=os.getenv("EMBED_MODEL", "all-mpnet-base-v2"),
            embed_version="1.0.0"  # Will be dynamic later
        )

    except Exception as e:
        logger.error(f"Metrics retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="Metrics retrieval failed")


@app.get("/config", response_model=ServiceConfig)
async def get_service_config():
    """Get current service configuration."""
    try:
        config = get_config()
        return ServiceConfig(**config.dict())
    except Exception as e:
        logger.error(f"Failed to get configuration: {e}")
        raise HTTPException(status_code=500, detail="Failed to get configuration")


@app.post("/config", response_model=ServiceConfig)
async def update_service_config(request: ConfigUpdateRequest):
    """Update service configuration."""
    try:
        # Convert request to dict, filtering out None values
        updates = {}
        if request.database:
            updates["database"] = request.database.dict()
        if request.vector:
            updates["vector"] = request.vector.dict()
        if request.embedding:
            updates["embedding"] = request.embedding.dict()
        if request.search:
            updates["search"] = request.search.dict()

        if not updates:
            raise HTTPException(status_code=400, detail="No configuration updates provided")

        new_config = update_config(updates)
        return ServiceConfig(**new_config.dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update configuration: {e}")
        raise HTTPException(status_code=500, detail="Failed to update configuration")


@app.post("/config/validate-db", response_model=DatabaseValidationResponse)
async def validate_database_connection(db_url: str = Form(...)):
    """Validate database connection string."""
    try:
        from .config import config_manager
        result = config_manager.validate_database_connection(db_url)
        return DatabaseValidationResponse(**result)
    except Exception as e:
        logger.error(f"Failed to validate database connection: {e}")
        raise HTTPException(status_code=500, detail="Failed to validate database connection")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(error="Internal server error", detail=str(exc)).dict()
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
