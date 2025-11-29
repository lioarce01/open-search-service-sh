import { useState, useEffect } from 'react'

const API_BASE = 'http://localhost:8000'

function SearchPage() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [searchTime, setSearchTime] = useState(0)
  const [hybrid, setHybrid] = useState(true)
  const [rerank, setRerank] = useState(true)
  const [topK, setTopK] = useState(5)
  const [error, setError] = useState('')

  // Load default top_k from config
  useEffect(() => {
    const loadConfig = async () => {
      try {
        const response = await fetch(`${API_BASE}/config`)
        if (response.ok) {
          const config = await response.json()
          setTopK(config.search.top_k)
          setRerank(config.search.reranker_enabled)
        }
      } catch (err) {
        console.warn('Could not load config, using defaults:', err)
      }
    }
    loadConfig()
  }, [])

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    setError('')
    setResults([])

    try {
      const response = await fetch(`${API_BASE}/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          q: query,
          top_k: topK,
          hybrid: hybrid,
          rerank: rerank,
        }),
      })

      if (!response.ok) {
        throw new Error(`Search failed: ${response.statusText}`)
      }

      const data = await response.json()
      setResults(data.results)
      setSearchTime(data.search_time_ms)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="px-4 py-8">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Search Documents</h2>

        {/* Search Form */}
        <form onSubmit={handleSearch} className="mb-8">
          <div className="flex gap-4 mb-4">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter your search query..."
              className="flex-1 px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Searching...' : 'Search'}
            </button>
          </div>

          {/* Search Options */}
          <div className="flex flex-wrap gap-6 mb-4">
            <div className="flex items-center gap-2">
              <label className="text-sm text-gray-700">Top K:</label>
              <input
                type="number"
                value={topK}
                onChange={(e) => setTopK(parseInt(e.target.value) || 5)}
                className="w-16 px-2 py-1 border border-gray-300 rounded text-center focus:ring-blue-500 focus:border-blue-500"
                min="1"
                max="50"
              />
            </div>

            <label className="flex items-center">
              <input
                type="checkbox"
                checked={hybrid}
                onChange={(e) => setHybrid(e.target.checked)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="ml-2 text-sm text-gray-700">Hybrid Search</span>
            </label>

            <label className="flex items-center">
              <input
                type="checkbox"
                checked={rerank}
                onChange={(e) => setRerank(e.target.checked)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="ml-2 text-sm text-gray-700">Reranking</span>
            </label>
          </div>
        </form>

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-md">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {/* Search Results */}
        {results.length > 0 && (
          <div className="mb-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-gray-900">
                Found {results.length} results
              </h3>
              <span className="text-sm text-gray-500">
                Search time: {searchTime.toFixed(1)}ms
              </span>
            </div>

            <div className="space-y-4">
              {results.map((result, index) => (
                <div key={result.chunk_id} className="bg-white p-6 rounded-lg shadow-sm border">
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-500">
                        Document: {result.doc_id}
                      </span>
                      {result.title && (
                        <span className="text-sm text-gray-700">• {result.title}</span>
                      )}
                    </div>
                    <span className="text-sm text-gray-500">
                      Score: {result.score.toFixed(3)}
                    </span>
                  </div>

                  <p className="text-gray-800 mb-3 leading-relaxed">
                    {result.text_snippet}
                  </p>

                  {result.metadata && Object.keys(result.metadata).length > 0 && (
                    <div className="text-sm text-gray-600">
                      <strong>Metadata:</strong> {JSON.stringify(result.metadata, null, 2)}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* No Results */}
        {!loading && !error && query && results.length === 0 && (
          <div className="text-center py-12">
            <p className="text-gray-500">No results found for "{query}"</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default SearchPage
