# Open Search Service

A self-hosted semantic + lexical search service with RAG capabilities, supporting multiple vector backends (pgvector/FAISS) and embedding providers (sentence-transformers/OpenAI). Features PDF processing, configurable search results, and comprehensive web interface.

## Features

- **Semantic Search**: Vector similarity search using embeddings
- **Hybrid Search**: Combines semantic and full-text search with configurable result counts
- **Multiple Vector Backends**: PostgreSQL pgvector (recommended) or FAISS (HNSW)
- **Flexible Embeddings**: Local sentence-transformers or OpenAI API
- **Advanced Reranking**: Cross-encoder for improved result quality (enabled by default)
- **Document Ingestion**: Chunking, embedding, and indexing pipeline
- **Multi-format Support**: Text files (.txt, .md) and PDF documents with automatic text extraction
- **Synchronous/Asynchronous Processing**: Choose immediate or background ingestion
- **REST API**: FastAPI backend with comprehensive endpoints
- **Web Interface**: Clean React frontend for search, ingestion, and configuration
- **Containerized**: Docker Compose deployment with PostgreSQL and pgvector
- **Configuration Management**: Web-based settings page with real-time validation

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React UI      │    │   FastAPI       │    │  PostgreSQL     │
│   (Port 3000)   │◄──►│   Backend       │◄──►│  + pgvector     │
│                 │    │   (Port 8000)   │    │  (vectors +     │
└─────────────────┘    └─────────────────┘    │   metadata)     │
                                              └─────────────────┘
                                              │
                                              ▼
                                       ┌─────────────────┐
                                       │ Alternative:    │
                                       │ FAISS Vector    │
                                       │ Store (file)    │
                                       └─────────────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- 4GB+ RAM (for sentence-transformers models)
- Optional: OpenAI API key for cloud embeddings

### Setup and Run

1. **Clone and configure**:
   ```bash
   git clone <repository-url>
   cd open-search-service
   cp open-search-service.env.example .env
   ```

2. **Edit `.env`** (optional - defaults are optimized):
   ```bash
   # Uses pgvector (recommended) or FAISS
   VECTOR_BACKEND=pgvector

   # Uses local embeddings (recommended) or OpenAI
   EMBEDDING_PROVIDER=local
   # OPENAI_API_KEY=your_key_here  # Only if using OpenAI

   # Configure search results (default: 5)
   TOP_K=10
   ```

3. **Start services**:
   ```bash
   docker-compose up --build
   ```

4. **Access the application**:
   - Frontend: http://localhost:3000
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://...` | PostgreSQL connection string |
| `DB_POOL_SIZE` | `10` | Database connection pool size |
| `DB_MAX_OVERFLOW` | `20` | Maximum overflow connections |
| `VECTOR_BACKEND` | `pgvector` | Vector store: `pgvector` or `faiss` |
| `EMBEDDING_PROVIDER` | `local` | Embeddings: `local` or `openai` |
| `EMBED_MODEL` | `all-mpnet-base-v2` | Local embedding model |
| `EMBED_DIM` | `768` | Embedding vector dimensions |
| `OPENAI_API_KEY` | - | Required for OpenAI embeddings |
| `OPENAI_MODEL` | `text-embedding-3-small` | OpenAI embedding model |
| `TOP_K` | `5` | Number of search results to return |
| `CHUNK_TOKENS` | `512` | Maximum tokens per chunk |
| `RERANKER_ENABLED` | `true` | Enable cross-encoder reranking |
| `RERANKER_MODEL` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Reranker model |
| `LOG_LEVEL` | `INFO` | Logging level |

**FAISS-specific variables** (only when `VECTOR_BACKEND=faiss`):
- `FAISS_INDEX_PATH=/data/faiss`
- `FAISS_M=32`, `FAISS_EF_CONSTRUCTION=200`, `FAISS_EF_SEARCH=64`

### Switching Vector Backends

**pgvector (recommended default)**:
- Integrated with PostgreSQL for ACID compliance
- Better for concurrent access and large datasets
- Automatic backup/restore with database
- Requires PostgreSQL with pgvector extension

**FAISS (alternative)**:
- Faster searches for read-heavy workloads
- Persistent index on disk
- No PostgreSQL extensions required
- Single-writer architecture

To switch to FAISS:
```bash
# In .env
VECTOR_BACKEND=faiss

# Rebuild and restart
docker-compose down
docker-compose up --build
```

### Using OpenAI Embeddings

For production or better performance:
```bash
# In .env
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=text-embedding-3-small  # or text-embedding-3-large
```

**Cost considerations**:
- `text-embedding-3-small`: ~$0.02 per 1M tokens
- `text-embedding-3-large`: ~$0.13 per 1M tokens

**Security notes**:
- Never commit API keys to version control
- Rotate keys regularly
- Use environment-specific keys
- Monitor API usage

## API Endpoints

### Ingestion
```bash
POST /ingest
Content-Type: multipart/form-data

# Form fields: doc_id*, title?, text?, file?, metadata?, sync?
# Supported file types: .txt, .md, .pdf (automatic text extraction)
# sync=true for immediate completion, false for background processing
```

### Search
```bash
POST /search
Content-Type: application/json

{
  "q": "search query",
  "top_k": 5,
  "hybrid": true,
  "rerank": true
}
```

### Other Endpoints
- `GET /status` - Health check
- `DELETE /document/{doc_id}` - Delete document
- `GET /docs/{doc_id}` - Get document info
- `GET /metrics` - Service metrics
- `GET /config` - Get service configuration
- `POST /config` - Update service configuration
- `POST /config/validate-db` - Validate database connection string

## Usage Examples

### Ingest Document
```bash
# Text ingestion (synchronous)
curl -X POST http://localhost:8000/ingest \
  -F "doc_id=doc1" \
  -F "title=My Document" \
  -F "text=This is the content of my document..." \
  -F "sync=true"

# File ingestion (PDF/text)
curl -X POST http://localhost:8000/ingest \
  -F "doc_id=doc2" \
  -F "file=@document.pdf" \
  -F "metadata={\"author\":\"John Doe\"}"

# Background processing
curl -X POST http://localhost:8000/ingest \
  -F "doc_id=doc3" \
  -F "text=Large document content..." \
  -F "sync=false"  # Default: background processing
```

### Search
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"q": "search query", "top_k": 5}'
```

### Configuration Management

#### Get Current Configuration
```bash
curl http://localhost:8000/config
```

#### Update Configuration
```bash
curl -X POST http://localhost:8000/config \
  -H "Content-Type: application/json" \
  -d '{
    "vector": {
      "backend": "pgvector"
    },
    "embedding": {
      "provider": "openai",
      "openai_api_key": "your-api-key"
    }
  }'
```

#### Validate Database Connection
```bash
curl -X POST http://localhost:8000/config/validate-db \
  -F "db_url=postgresql://user:pass@host:5432/db"
```

## Testing

Run the integration test:
```bash
python tests/integration_test.py
```

This will:
1. Ingest sample documents
2. Perform searches
3. Verify results

## Self-Hosting Configuration

This service is designed for easy self-hosting with flexible configuration options. Use the web interface or API to customize your deployment.

### Configuration Interface

Access the **Settings** page in the web interface (http://localhost:3000) to configure:

#### Database Configuration
- **Connection String**: PostgreSQL URL for metadata storage
- **Connection Pooling**: Pool size and overflow settings
- **Validation**: Test database connectivity before saving

#### Vector Backend Selection
- **FAISS**: Local file-based vector storage (default)
  - Index file path and HNSW parameters
  - Best for single-server deployments
- **pgvector**: PostgreSQL vector extension
  - Requires PostgreSQL with pgvector extension
  - Better for distributed/multi-server setups

#### Embedding Providers
- **Local (sentence-transformers)**: Free, offline embeddings
  - Choose between speed (MiniLM) or quality (MPNet)
  - No API costs, runs on your hardware
- **OpenAI**: Cloud embeddings with API key
  - Higher quality, faster inference
  - Pay per token usage

#### Search Configuration
- **Chunk Size**: Token limit per text chunk
- **Reranking**: Optional cross-encoder for better results
- **Performance Tuning**: Adjust based on your hardware

### Configuration Examples

#### Production pgvector Setup (Recommended)
```bash
# Optimized production configuration
VECTOR_BACKEND=pgvector
EMBEDDING_PROVIDER=local
DATABASE_URL=postgresql://prod_user:secure_pass@prod-db.company.com:5432/search_prod
TOP_K=10
RERANKER_ENABLED=true
```

#### Basic Local Setup
```bash
# Default configuration (works out of the box)
VECTOR_BACKEND=pgvector
EMBEDDING_PROVIDER=local
DATABASE_URL=postgresql://search_user:search_password@postgres:5432/search_db
TOP_K=5
RERANKER_ENABLED=true
```

#### High-Performance Cloud Setup
```bash
# OpenAI embeddings + pgvector
VECTOR_BACKEND=pgvector
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=text-embedding-3-large
DATABASE_URL=postgresql://user:pass@localhost:5432/search_db
TOP_K=15
```

#### Development FAISS Setup
```bash
# FAISS for development/testing
VECTOR_BACKEND=faiss
EMBEDDING_PROVIDER=local
DATABASE_URL=postgresql://search_user:search_password@postgres:5432/search_db
TOP_K=5
RERANKER_ENABLED=false
```

### Configuration Persistence

Configurations are automatically saved to `backend/config.json` and persist across container restarts. The web interface provides real-time validation and feedback.

### Security Considerations

- **Database Credentials**: Use strong passwords and consider connection pooling
- **API Keys**: Store OpenAI keys securely, rotate regularly
- **Network Security**: Configure firewalls and use HTTPS in production
- **Backup**: Regularly backup your vector indexes and database

### Scaling Considerations

- **FAISS**: Good for read-heavy workloads, single-writer
- **pgvector**: Better for multi-writer scenarios and complex queries
- **Embeddings**: Local providers save costs but require GPU for speed
- **Database**: Use connection pooling and monitor query performance

## Development

### Backend Development
```bash
cd backend
pip install -r requirements.txt
python init_db.py  # Initialize database
uvicorn app.main:app --reload
```

### Frontend Development
```bash
cd frontend
npm install
npm run dev
```

### Changing Embedding Models

**Local models** (sentence-transformers):
```bash
# In .env
EMBED_MODEL=all-MiniLM-L6-v2        # 384 dims, fastest (~50ms)
EMBED_MODEL=all-mpnet-base-v2       # 768 dims, balanced (default)
EMBED_MODEL=all-distilroberta-v1    # 768 dims, good quality
```

**OpenAI models**:
```bash
# In .env
OPENAI_MODEL=text-embedding-3-small   # 1536 dims, ~$0.02/1M tokens
OPENAI_MODEL=text-embedding-3-large   # 3072 dims, ~$0.13/1M tokens (best quality)
OPENAI_MODEL=text-embedding-ada-002   # 1536 dims, legacy model
```

### Configuring Search Results

Control the number of results returned by search queries:

```bash
# In .env or Settings page
TOP_K=5      # Default: balanced results
TOP_K=10     # More comprehensive results
TOP_K=3      # Quick top matches only
```

**Note**: `TOP_K` affects both API responses and web interface display.

## Security Considerations

**⚠️ Important**: This is a development/demo setup. For production:

- **Don't expose API publicly** without authentication
- **Secure database credentials** - use IAM/database secrets
- **Use HTTPS** in production
- **Network isolation** - run services in private subnets
- **API rate limiting** - add to prevent abuse
- **Input validation** - sanitize all inputs
- **Monitor resource usage** - embeddings can be expensive

## Troubleshooting

### Common Issues

**"pgvector extension not found"**
- Uses `pgvector/pgvector:pg15` image (has pgvector pre-installed)
- Run `init_db.py` after container starts
- Check PostgreSQL logs: `docker-compose logs postgres`

**"PDF processing failed"**
- Ensure PyPDF2 is installed (included in requirements.txt)
- Check PDF isn't password-protected or corrupted
- For scanned PDFs, text extraction may be limited

**"CUDA out of memory"**
- Reduce batch sizes or use CPU-only mode
- Use smaller embedding models (`all-MiniLM-L6-v2`)
- Increase container memory limits

**"Search returns 0 results"**
- Ensure documents are fully ingested (check async processing)
- Try different search terms or disable hybrid search
- Check vector backend is properly initialized

**"Connection refused"**
- Check service health: `docker-compose ps`
- Wait for PostgreSQL to be ready (may take 30-60 seconds)
- Verify port mappings: `docker-compose ps`

**Slow ingestion**
- Reduce `CHUNK_TOKENS` for more parallel processing
- Use CPU-optimized models for faster embedding
- Enable sync mode for immediate feedback
- Increase container resources (--memory, --cpus)

**"Collation version mismatch"**
- Harmless warning, can be ignored
- Fixed automatically in future deployments

### Logs

View service logs:
```bash
docker-compose logs api
docker-compose logs postgres
docker-compose logs frontend
```

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request
