import { useState, useEffect } from 'react'

const API_BASE = 'http://localhost:8000'

function SettingsPage() {
  const [config, setConfig] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  // Form states
  const [dbUrl, setDbUrl] = useState('')
  const [dbPoolSize, setDbPoolSize] = useState(10)
  const [dbMaxOverflow, setDbMaxOverflow] = useState(20)

  const [vectorBackend, setVectorBackend] = useState('faiss')
  const [faissIndexPath, setFaissIndexPath] = useState('/data/faiss')
  const [faissM, setFaissM] = useState(32)
  const [faissEfConstruction, setFaissEfConstruction] = useState(200)
  const [faissEfSearch, setFaissEfSearch] = useState(64)

  const [embeddingProvider, setEmbeddingProvider] = useState('local')
  const [embeddingModel, setEmbeddingModel] = useState('all-mpnet-base-v2')
  const [embeddingDimension, setEmbeddingDimension] = useState(768)
  const [openaiApiKey, setOpenaiApiKey] = useState('')

  const [chunkTokens, setChunkTokens] = useState(512)
  const [topK, setTopK] = useState(5)
  const [rerankerEnabled, setRerankerEnabled] = useState(false)
  const [rerankerModel, setRerankerModel] = useState('cross-encoder/ms-marco-MiniLM-L-6-v2')

  // Database validation
  const [dbValidation, setDbValidation] = useState(null)
  const [validatingDb, setValidatingDb] = useState(false)

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    try {
      setLoading(true)
      const response = await fetch(`${API_BASE}/config`)
      if (!response.ok) throw new Error('Failed to load configuration')

      const configData = await response.json()
      setConfig(configData)

      // Populate form fields
      setDbUrl(configData.database.url)
      setDbPoolSize(configData.database.pool_size)
      setDbMaxOverflow(configData.database.max_overflow)

      setVectorBackend(configData.vector.backend)
      setFaissIndexPath(configData.vector.faiss_index_path)
      setFaissM(configData.vector.faiss_m)
      setFaissEfConstruction(configData.vector.faiss_ef_construction)
      setFaissEfSearch(configData.vector.faiss_ef_search)

      setEmbeddingProvider(configData.embedding.provider)
      setEmbeddingModel(configData.embedding.model)
      setEmbeddingDimension(configData.embedding.dimension)
      setOpenaiApiKey(configData.embedding.openai_api_key || '')

      setChunkTokens(configData.search.chunk_tokens)
      setTopK(configData.search.top_k)
      setRerankerEnabled(configData.search.reranker_enabled)
      setRerankerModel(configData.search.reranker_model)

    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const validateDatabase = async () => {
    if (!dbUrl.trim()) {
      setDbValidation({ valid: false, message: 'Database URL is required' })
      return
    }

    try {
      setValidatingDb(true)
      const formData = new FormData()
      formData.append('db_url', dbUrl)

      const response = await fetch(`${API_BASE}/config/validate-db`, {
        method: 'POST',
        body: formData
      })

      if (!response.ok) throw new Error('Validation failed')

      const result = await response.json()
      setDbValidation(result)

    } catch (err) {
      setDbValidation({ valid: false, message: err.message })
    } finally {
      setValidatingDb(false)
    }
  }

  const saveConfig = async () => {
    try {
      setSaving(true)
      setError('')
      setMessage('')

      const updates = {
        database: {
          url: dbUrl,
          pool_size: dbPoolSize,
          max_overflow: dbMaxOverflow
        },
        vector: {
          backend: vectorBackend,
          faiss_index_path: faissIndexPath,
          faiss_m: faissM,
          faiss_ef_construction: faissEfConstruction,
          faiss_ef_search: faissEfSearch
        },
        embedding: {
          provider: embeddingProvider,
          model: embeddingModel,
          dimension: embeddingDimension,
          openai_api_key: openaiApiKey || null
        },
        search: {
          chunk_tokens: chunkTokens,
          top_k: topK,
          reranker_enabled: rerankerEnabled,
          reranker_model: rerankerModel
        }
      }

      const response = await fetch(`${API_BASE}/config`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updates)
      })

      if (!response.ok) throw new Error('Failed to save configuration')

      const newConfig = await response.json()
      setConfig(newConfig)
      setMessage('Configuration saved successfully! Restart the service to apply changes.')

    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="px-4 py-8">
        <div className="max-w-4xl mx-auto">
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading configuration...</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="px-4 py-8">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Service Configuration</h2>

        {message && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-md">
            <p className="text-green-800">{message}</p>
          </div>
        )}

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-md">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        <div className="space-y-8">
          {/* Database Configuration */}
          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Database Configuration</h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  PostgreSQL Connection String
                </label>
                <input
                  type="text"
                  value={dbUrl}
                  onChange={(e) => setDbUrl(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 font-mono text-sm"
                  placeholder="postgresql://user:password@host:port/database"
                />
                <div className="mt-2 flex gap-2">
                  <button
                    onClick={validateDatabase}
                    disabled={validatingDb}
                    className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
                  >
                    {validatingDb ? 'Validating...' : 'Validate'}
                  </button>
                  {dbValidation && (
                    <span className={`text-sm ${dbValidation.valid ? 'text-green-600' : 'text-red-600'}`}>
                      {dbValidation.message}
                    </span>
                  )}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Pool Size
                </label>
                <input
                  type="number"
                  value={dbPoolSize}
                  onChange={(e) => setDbPoolSize(parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  min="1"
                  max="100"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Max Overflow
                </label>
                <input
                  type="number"
                  value={dbMaxOverflow}
                  onChange={(e) => setDbMaxOverflow(parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  min="0"
                  max="100"
                />
              </div>
            </div>
          </div>

          {/* Vector Backend Configuration */}
          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Vector Backend</h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Backend Type
                </label>
                <select
                  value={vectorBackend}
                  onChange={(e) => setVectorBackend(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="faiss">FAISS (Local File-based)</option>
                  <option value="pgvector">pgvector (PostgreSQL)</option>
                </select>
              </div>

              {vectorBackend === 'faiss' && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Index Path
                    </label>
                    <input
                      type="text"
                      value={faissIndexPath}
                      onChange={(e) => setFaissIndexPath(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 font-mono text-sm"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      HNSW M Parameter
                    </label>
                    <input
                      type="number"
                      value={faissM}
                      onChange={(e) => setFaissM(parseInt(e.target.value))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                      min="4"
                      max="128"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      efConstruction
                    </label>
                    <input
                      type="number"
                      value={faissEfConstruction}
                      onChange={(e) => setFaissEfConstruction(parseInt(e.target.value))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                      min="8"
                      max="1024"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      efSearch
                    </label>
                    <input
                      type="number"
                      value={faissEfSearch}
                      onChange={(e) => setFaissEfSearch(parseInt(e.target.value))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                      min="1"
                      max="1024"
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Embedding Configuration */}
          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Embeddings</h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Provider
                </label>
                <select
                  value={embeddingProvider}
                  onChange={(e) => setEmbeddingProvider(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="local">Local (sentence-transformers)</option>
                  <option value="openai">OpenAI API</option>
                </select>
              </div>

              {embeddingProvider === 'local' && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Model
                    </label>
                    <select
                      value={embeddingModel}
                      onChange={(e) => setEmbeddingModel(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="all-MiniLM-L6-v2">all-MiniLM-L6-v2 (faster)</option>
                      <option value="all-mpnet-base-v2">all-mpnet-base-v2 (better)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Dimension
                    </label>
                    <input
                      type="number"
                      value={embeddingDimension}
                      onChange={(e) => setEmbeddingDimension(parseInt(e.target.value))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                      min="128"
                      max="1024"
                    />
                  </div>
                </div>
              )}

              {embeddingProvider === 'openai' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    OpenAI API Key
                  </label>
                  <input
                    type="password"
                    value={openaiApiKey}
                    onChange={(e) => setOpenaiApiKey(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 font-mono"
                    placeholder="sk-..."
                  />
                </div>
              )}
            </div>
          </div>

          {/* Search Configuration */}
          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Search Settings</h3>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Default Top K Results
                </label>
                <input
                  type="number"
                  value={topK}
                  onChange={(e) => setTopK(parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  min="1"
                  max="50"
                />
                <p className="mt-1 text-xs text-gray-500">Number of search results to return</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Chunk Token Limit
                </label>
                <input
                  type="number"
                  value={chunkTokens}
                  onChange={(e) => setChunkTokens(parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  min="128"
                  max="2048"
                />
                <p className="mt-1 text-xs text-gray-500">Tokens per text chunk</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Reranker Model
                </label>
                <input
                  type="text"
                  value={rerankerModel}
                  onChange={(e) => setRerankerModel(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 font-mono text-sm"
                  disabled={!rerankerEnabled}
                />
                <p className="mt-1 text-xs text-gray-500">Cross-encoder model for reranking</p>
              </div>
            </div>

            <div className="mt-4">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={rerankerEnabled}
                  onChange={(e) => setRerankerEnabled(e.target.checked)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="ml-2 text-sm text-gray-700">Enable cross-encoder reranking</span>
              </label>
            </div>
          </div>

          {/* Save Button */}
          <div className="flex justify-end">
            <button
              onClick={saveConfig}
              disabled={saving}
              className="px-6 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? 'Saving...' : 'Save Configuration'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SettingsPage
