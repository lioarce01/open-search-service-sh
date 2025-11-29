import { useState } from 'react'

const API_BASE = 'http://localhost:8000'

function IngestPage() {
  const [docId, setDocId] = useState('')
  const [title, setTitle] = useState('')
  const [text, setText] = useState('')
  const [file, setFile] = useState(null)
  const [metadata, setMetadata] = useState('')
  const [sync, setSync] = useState(false)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!docId.trim()) {
      setError('Document ID is required')
      return
    }

    if (!text && !file) {
      setError('Either text content or a file must be provided')
      return
    }

    setLoading(true)
    setError('')
    setMessage('')

    try {
      const formData = new FormData()
      formData.append('doc_id', docId)
      formData.append('sync', sync.toString())

      if (title) {
        formData.append('title', title)
      }

      if (text) {
        formData.append('text', text)
      }

      if (file) {
        formData.append('file', file)
      }

      if (metadata) {
        // Validate JSON
        try {
          JSON.parse(metadata)
          formData.append('metadata', metadata)
        } catch {
          setError('Invalid JSON in metadata')
          setLoading(false)
          return
        }
      }

      const response = await fetch(`${API_BASE}/ingest`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || `HTTP ${response.status}`)
      }

      const data = await response.json()

      if (sync) {
        // Synchronous mode - we have the final result immediately
        setMessage(`Document "${docId}" ingested successfully with ${data.chunk_count} chunks`)

        // Clear form
        setDocId('')
        setTitle('')
        setText('')
        setFile(null)
        setMetadata('')
      } else {
        // Asynchronous mode - poll for completion
        setMessage(`Document "${docId}" ingestion started...`)

        // Poll for completion
        let attempts = 0
        const maxAttempts = 10
        const pollInterval = 1000 // 1 second

        const pollForCompletion = async () => {
          try {
            const docResponse = await fetch(`${API_BASE}/docs/${docId}`)
            if (docResponse.ok) {
              const docData = await docResponse.json()
              setMessage(`Document "${docId}" ingested successfully with ${docData.chunk_count} chunks`)
              return true
            } else if (docResponse.status === 404) {
              // Document not found yet, continue polling
              return false
            } else {
              throw new Error(`Failed to fetch document: ${docResponse.status}`)
            }
          } catch (err) {
            console.warn('Error polling for document completion:', err)
            return false
          }
        }

        const poll = async () => {
          attempts++
          const completed = await pollForCompletion()

          if (completed || attempts >= maxAttempts) {
            // Clear form
            setDocId('')
            setTitle('')
            setText('')
            setFile(null)
            setMetadata('')
          } else {
            setTimeout(poll, pollInterval)
          }
        }

        // Start polling after a short delay
        setTimeout(poll, 500)
      }

    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile) {
      setFile(selectedFile)
      // Clear text if file is selected
      setText('')
    }
  }

  return (
    <div className="px-4 py-8">
      <div className="max-w-2xl mx-auto">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Ingest Document</h2>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Document ID */}
          <div>
            <label htmlFor="docId" className="block text-sm font-medium text-gray-700 mb-1">
              Document ID *
            </label>
            <input
              type="text"
              id="docId"
              value={docId}
              onChange={(e) => setDocId(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              placeholder="unique-document-id"
              required
              disabled={loading}
            />
          </div>

          {/* Title */}
          <div>
            <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-1">
              Title (optional)
            </label>
            <input
              type="text"
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              placeholder="Document title"
              disabled={loading}
            />
          </div>

          {/* File Upload */}
          <div>
            <label htmlFor="file" className="block text-sm font-medium text-gray-700 mb-1">
              Upload File (optional)
            </label>
            <input
              type="file"
              id="file"
              onChange={handleFileChange}
              accept=".txt,.md,.pdf"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              disabled={loading}
            />
            <p className="mt-1 text-sm text-gray-500">
              Supported formats: .txt, .md, .pdf (text will be extracted from PDFs)
            </p>
          </div>

          {/* Text Content */}
          <div>
            <label htmlFor="text" className="block text-sm font-medium text-gray-700 mb-1">
              Text Content {!file ? '*' : '(optional if file uploaded)'}
            </label>
            <textarea
              id="text"
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={8}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              placeholder="Paste your document text here..."
              disabled={loading || file}
            />
          </div>

          {/* Metadata */}
          <div>
            <label htmlFor="metadata" className="block text-sm font-medium text-gray-700 mb-1">
              Metadata (JSON, optional)
            </label>
            <textarea
              id="metadata"
              value={metadata}
              onChange={(e) => setMetadata(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 font-mono text-sm"
              placeholder='{"author": "John Doe", "category": "research"}'
              disabled={loading}
            />
            <p className="mt-1 text-sm text-gray-500">
              Valid JSON object for additional document metadata
            </p>
          </div>

          {/* Synchronous Processing Option */}
          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id="sync"
              checked={sync}
              onChange={(e) => setSync(e.target.checked)}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              disabled={loading}
            />
            <label htmlFor="sync" className="text-sm font-medium text-gray-700">
              Synchronous processing
            </label>
            <span className="text-xs text-gray-500">
              (Wait for completion vs. background processing)
            </span>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={loading}
            className="w-full px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading
              ? (sync ? 'Processing...' : 'Starting...')
              : 'Ingest Document'
            }
          </button>

          {/* Processing Mode Info */}
          <div className="text-xs text-gray-500 text-center">
            {sync ? (
              <span>⚡ Synchronous: Wait for completion before response</span>
            ) : (
              <span>🔄 Asynchronous: Start in background, poll for completion</span>
            )}
          </div>
        </form>

        {/* Success Message */}
        {message && (
          <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-md">
            <p className="text-green-800">{message}</p>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-md">
            <p className="text-red-800">{error}</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default IngestPage
