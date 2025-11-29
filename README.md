# Semantic Search Service

A self-hosted semantic + lexical search service with RAG capabilities, supporting multiple vector backends (FAISS/pgvector) and embedding providers (sentence-transformers/OpenAI).

## Features

- **Semantic Search**: Vector similarity search using embeddings
- **Hybrid Search**: Combines semantic and full-text search
- **Multiple Vector Backends**: FAISS (HNSW) or PostgreSQL pgvector
- **Flexible Embeddings**: Local sentence-transformers or OpenAI API
- **Optional Reranking**: Cross-encoder for improved result quality
- **Document Ingestion**: Chunking, embedding, and indexing pipeline
- **REST API**: FastAPI backend with comprehensive endpoints
- **Web Interface**: Clean React frontend for search and ingestion
- **Containerized**: Docker Compose deployment with PostgreSQL

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React UI      │    │   FastAPI       │    │  PostgreSQL     │
│   (Port 3000)   │◄──►│   Backend       │◄──►│  + pgvector     │
│                 │    │   (Port 8000)   │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   Vector Store   │
                       │   (FAISS or     │
                       │    pgvector)    │
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
   cd semantic-search-service
   cp .env.example .env
   ```

2. **Edit `.env`** (optional - defaults should work):
   ```bash
   # Use FAISS (default) or pgvector
   VECTOR_BACKEND=faiss

   # Use local embeddings (default) or OpenAI
   EMBEDDING_PROVIDER=local
   # OPENAI_API_KEY=your_key_here  # Only if using OpenAI
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
| `VECTOR_BACKEND` | `faiss` | Vector store: `faiss` or `pgvector` |
| `EMBEDDING_PROVIDER` | `local` | Embeddings: `local` or `openai` |
| `OPENAI_API_KEY` | - | Required for OpenAI embeddings |
| `RERANKER_ENABLED` | `false` | Enable cross-encoder reranking |
| `EMBED_MODEL` | `all-mpnet-base-v2` | Local embedding model |
| `CHUNK_TOKENS` | `512` | Maximum tokens per chunk |
| `LOG_LEVEL` | `INFO` | Logging level |

### Switching Vector Backends

**FAISS (default)**:
- Faster searches
- Persistent index on disk
- No PostgreSQL extensions required

**pgvector**:
- Integrated with PostgreSQL
- Better for large datasets
- Requires pgvector extension

To switch to pgvector:
```bash
# In .env
VECTOR_BACKEND=pgvector

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

# Form fields: doc_id, title?, text?, file?, metadata?
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
curl -X POST http://localhost:8000/ingest \
  -F "doc_id=doc1" \
  -F "title=My Document" \
  -F "text=This is the content of my document..."
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

#### Basic Local Setup (Default)
```bash
# Uses FAISS + local embeddings
VECTOR_BACKEND=faiss
EMBEDDING_PROVIDER=local
DATABASE_URL=postgresql://user:pass@localhost:5432/search_db
```

#### Production pgvector Setup
```bash
# Uses PostgreSQL for both metadata and vectors
VECTOR_BACKEND=pgvector
EMBEDDING_PROVIDER=local
DATABASE_URL=postgresql://prod_user:secure_pass@prod-db.company.com:5432/search_prod
```

#### Cloud Embeddings Setup
```bash
# Uses OpenAI for embeddings, local vectors
VECTOR_BACKEND=faiss
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
DATABASE_URL=postgresql://user:pass@localhost:5432/search_db
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
EMBED_MODEL=all-MiniLM-L6-v2  # Smaller, faster
# or
EMBED_MODEL=all-mpnet-base-v2  # Default, better quality
```

**OpenAI models**:
```bash
# In .env
OPENAI_MODEL=text-embedding-3-small   # 1536 dims, cheaper
OPENAI_MODEL=text-embedding-3-large   # 3072 dims, better
OPENAI_MODEL=text-embedding-ada-002   # Legacy
```

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
- Ensure PostgreSQL 15+ is used
- Run `init_db.py` after container starts

**"CUDA out of memory"**
- Reduce batch sizes or use CPU-only mode
- Use smaller embedding models

**"Connection refused"**
- Check service health: `docker-compose ps`
- Wait for PostgreSQL to be ready

**Slow ingestion**
- Reduce `CHUNK_TOKENS` for more chunks
- Use CPU-optimized models
- Increase container resources

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
