"use client"

import { useState, useEffect } from "react"
import { Database, Cpu, Brain, Search, Save, CheckCircle, AlertCircle, Loader2, Cog } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { toast } from "sonner"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export function SettingsPage() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState("")
  const [error, setError] = useState("")

  // Database
  const [dbUrl, setDbUrl] = useState("")
  const [dbPoolSize, setDbPoolSize] = useState(10)
  const [dbMaxOverflow, setDbMaxOverflow] = useState(20)
  const [dbValidation, setDbValidation] = useState<{ valid: boolean; message: string } | null>(null)
  const [validatingDb, setValidatingDb] = useState(false)

  // Vector
  const [vectorBackend, setVectorBackend] = useState("faiss")
  const [faissIndexPath, setFaissIndexPath] = useState("/data/faiss")
  const [faissM, setFaissM] = useState(32)
  const [faissEfConstruction, setFaissEfConstruction] = useState(200)
  const [faissEfSearch, setFaissEfSearch] = useState(64)

  // Embedding
  const [embeddingProvider, setEmbeddingProvider] = useState("local")
  const [embeddingModel, setEmbeddingModel] = useState("all-mpnet-base-v2")
  const [embeddingDimension, setEmbeddingDimension] = useState(768)
  const [openaiApiKey, setOpenaiApiKey] = useState("")
  const [openaiModel, setOpenaiModel] = useState("text-embedding-3-small")

  // Search
  const [chunkTokens, setChunkTokens] = useState(512)
  const [topK, setTopK] = useState(5)
  const [rerankerEnabled, setRerankerEnabled] = useState(false)
  const [rerankerModel, setRerankerModel] = useState("cross-encoder/ms-marco-MiniLM-L-6-v2")

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    try {
      setLoading(true)
      const response = await fetch(`${API_BASE}/config`)
      if (!response.ok) throw new Error("Failed to load configuration")

      const config = await response.json()

      setDbUrl(config.database.url)
      setDbPoolSize(config.database.pool_size)
      setDbMaxOverflow(config.database.max_overflow)

      setVectorBackend(config.vector.backend)
      setFaissIndexPath(config.vector.faiss_index_path)
      setFaissM(config.vector.faiss_m)
      setFaissEfConstruction(config.vector.faiss_ef_construction)
      setFaissEfSearch(config.vector.faiss_ef_search)

      setEmbeddingProvider(config.embedding.provider)
      setEmbeddingModel(config.embedding.model)
      setEmbeddingDimension(config.embedding.dimension)
      setOpenaiApiKey(config.embedding.openai_api_key || "")
      setOpenaiModel(config.embedding.openai_model || "text-embedding-3-small")

      setChunkTokens(config.search.chunk_tokens)
      setTopK(config.search.top_k)
      setRerankerEnabled(config.search.reranker_enabled)
      setRerankerModel(config.search.reranker_model)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load config")
    } finally {
      setLoading(false)
    }
  }

  const validateDatabase = async () => {
    if (!dbUrl.trim()) {
      setDbValidation({ valid: false, message: "Database URL is required" })
      return
    }

    try {
      setValidatingDb(true)
      const formData = new FormData()
      formData.append("db_url", dbUrl)

      const response = await fetch(`${API_BASE}/config/validate-db`, {
        method: "POST",
        body: formData,
      })

      if (!response.ok) throw new Error("Validation failed")
      const result = await response.json()
      setDbValidation(result)
    } catch (err) {
      setDbValidation({ valid: false, message: err instanceof Error ? err.message : "Validation failed" })
    } finally {
      setValidatingDb(false)
    }
  }

  const saveConfig = async () => {
    try {
      setSaving(true)
      setError("")
      setMessage("")

      const updates = {
        database: { url: dbUrl, pool_size: dbPoolSize, max_overflow: dbMaxOverflow },
        vector: {
          backend: vectorBackend,
          faiss_index_path: faissIndexPath,
          faiss_m: faissM,
          faiss_ef_construction: faissEfConstruction,
          faiss_ef_search: faissEfSearch,
        },
        embedding: {
          provider: embeddingProvider,
          model: embeddingModel,
          dimension: embeddingDimension,
          openai_api_key: openaiApiKey || null,
          openai_model: openaiModel,
        },
        search: {
          chunk_tokens: chunkTokens,
          top_k: topK,
          reranker_enabled: rerankerEnabled,
          reranker_model: rerankerModel,
        },
      }

      const response = await fetch(`${API_BASE}/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updates),
      })

      if (!response.ok) throw new Error("Failed to save configuration")

      // Try to reload configuration on the server
      try {
        await fetch(`${API_BASE}/config/reload`, { method: "POST" })
      } catch (reloadErr) {
        console.warn("Could not reload configuration on server:", reloadErr)
      }

      setMessage("Configuration saved successfully!")
      toast.success("Configuration saved!")
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Save failed"
      setError(errorMessage)
      toast.error("Save failed", { description: errorMessage })
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-4">
        <Loader2 className="h-12 w-12 text-primary animate-spin" />
        <p className="text-muted-foreground">Loading configuration...</p>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="text-center space-y-2">
        <div className="flex items-center justify-center gap-3">
          <div className="h-px w-12 bg-gradient-to-r from-transparent to-border" />
          <Cog className="h-8 w-8 text-primary" strokeWidth={1.5} />
          <div className="h-px w-12 bg-gradient-to-l from-transparent to-border" />
        </div>
        <h2 className="text-3xl font-bold text-foreground tracking-tight">Service Configuration</h2>
        <p className="text-muted-foreground max-w-md mx-auto">
          Configure database, embeddings, and search settings
        </p>
        <div className="text-sm text-muted-foreground mt-2 max-w-lg mx-auto">
          <div className="grid grid-cols-2 gap-2">
            <div className="text-green-600">✓ Dynamic: Search settings, Reranker</div>
            <div className="text-orange-600">⟳ Restart needed: Embeddings, Vector backend</div>
          </div>
        </div>
      </div>

      {/* Messages */}
      {message && (
        <Alert className="max-w-4xl mx-auto border-2 border-green-600/30 bg-green-50/50">
          <CheckCircle className="h-4 w-4 text-green-600" />
          <AlertDescription className="text-green-800">
            {message}
            {message.includes("saved") && (
              <div className="mt-2 text-sm">
                <strong>Note:</strong> Some changes (embedding models, vector backends) require server restart to take effect.
              </div>
            )}
          </AlertDescription>
        </Alert>
      )}

      {error && (
        <Alert variant="destructive" className="max-w-4xl mx-auto border-2">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="max-w-4xl mx-auto space-y-6">
        {/* Database Configuration */}
        <Card className="border-2 shadow-lg">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5 text-primary" />
              Database Configuration
            </CardTitle>
            <CardDescription>PostgreSQL connection settings</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>PostgreSQL Connection String</Label>
              <Input
                value={dbUrl}
                onChange={(e) => setDbUrl(e.target.value)}
                placeholder="postgresql://user:password@host:port/database"
                className="font-mono text-sm bg-muted/30 border-2"
              />
              <div className="flex items-center gap-3">
                <Button type="button" variant="outline" size="sm" onClick={validateDatabase} disabled={validatingDb}>
                  {validatingDb ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <CheckCircle className="h-4 w-4 mr-2" />
                  )}
                  Validate
                </Button>
                {dbValidation && (
                  <span className={`text-sm ${dbValidation.valid ? "text-green-600" : "text-destructive"}`}>
                    {dbValidation.message}
                  </span>
                )}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Pool Size</Label>
                <Input
                  type="number"
                  value={dbPoolSize}
                  onChange={(e) => setDbPoolSize(Number.parseInt(e.target.value))}
                  min={1}
                  max={100}
                  className="bg-muted/30 border-2"
                />
              </div>
              <div className="space-y-2">
                <Label>Max Overflow</Label>
                <Input
                  type="number"
                  value={dbMaxOverflow}
                  onChange={(e) => setDbMaxOverflow(Number.parseInt(e.target.value))}
                  min={0}
                  max={100}
                  className="bg-muted/30 border-2"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Vector Backend */}
        <Card className="border-2 shadow-lg">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Cpu className="h-5 w-5 text-primary" />
              Vector Backend
            </CardTitle>
            <CardDescription>Vector index storage settings</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Backend Type</Label>
              <Select value={vectorBackend} onValueChange={setVectorBackend}>
                <SelectTrigger className="bg-muted/30 border-2">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="faiss">FAISS (Local File-based)</SelectItem>
                  <SelectItem value="pgvector">pgvector (PostgreSQL)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {vectorBackend === "faiss" && (
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Index Path</Label>
                  <Input
                    value={faissIndexPath}
                    onChange={(e) => setFaissIndexPath(e.target.value)}
                    className="font-mono text-sm bg-muted/30 border-2"
                  />
                </div>
                <div className="space-y-2">
                  <Label>HNSW M Parameter</Label>
                  <Input
                    type="number"
                    value={faissM}
                    onChange={(e) => setFaissM(Number.parseInt(e.target.value))}
                    min={4}
                    max={128}
                    className="bg-muted/30 border-2"
                  />
                </div>
                <div className="space-y-2">
                  <Label>efConstruction</Label>
                  <Input
                    type="number"
                    value={faissEfConstruction}
                    onChange={(e) => setFaissEfConstruction(Number.parseInt(e.target.value))}
                    min={8}
                    max={1024}
                    className="bg-muted/30 border-2"
                  />
                </div>
                <div className="space-y-2">
                  <Label>efSearch</Label>
                  <Input
                    type="number"
                    value={faissEfSearch}
                    onChange={(e) => setFaissEfSearch(Number.parseInt(e.target.value))}
                    min={1}
                    max={1024}
                    className="bg-muted/30 border-2"
                  />
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Embeddings */}
        <Card className="border-2 shadow-lg">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5 text-primary" />
              Embeddings
            </CardTitle>
            <CardDescription>Text embedding model configuration</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Provider</Label>
              <Select value={embeddingProvider} onValueChange={setEmbeddingProvider}>
                <SelectTrigger className="bg-muted/30 border-2">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="local">Local (sentence-transformers)</SelectItem>
                  <SelectItem value="openai">OpenAI API</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {embeddingProvider === "local" && (
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Model</Label>
                  <Select value={embeddingModel} onValueChange={setEmbeddingModel}>
                    <SelectTrigger className="bg-muted/30 border-2">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all-MiniLM-L6-v2">all-MiniLM-L6-v2 (faster)</SelectItem>
                      <SelectItem value="all-mpnet-base-v2">all-mpnet-base-v2 (better)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Dimension</Label>
                  <Input
                    type="number"
                    value={embeddingDimension}
                    onChange={(e) => setEmbeddingDimension(Number.parseInt(e.target.value))}
                    min={128}
                    max={1024}
                    className="bg-muted/30 border-2"
                  />
                </div>
              </div>
            )}

            {embeddingProvider === "openai" && (
              <>
                <div className="space-y-2">
                  <Label>OpenAI Model</Label>
                  <Select value={openaiModel} onValueChange={setOpenaiModel}>
                    <SelectTrigger className="bg-muted/30 border-2">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="text-embedding-3-small">text-embedding-3-small</SelectItem>
                      <SelectItem value="text-embedding-3-large">text-embedding-3-large</SelectItem>
                      <SelectItem value="text-embedding-ada-002">text-embedding-ada-002</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>OpenAI API Key</Label>
                  <Input
                    type="password"
                    value={openaiApiKey}
                    onChange={(e) => setOpenaiApiKey(e.target.value)}
                    placeholder="sk-..."
                    className="font-mono bg-muted/30 border-2"
                  />
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Search Settings */}
        <Card className="border-2 shadow-lg">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Search className="h-5 w-5 text-primary" />
              Search Settings
            </CardTitle>
            <CardDescription>Search behavior and reranking options</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>Default Top K Results</Label>
                <Input
                  type="number"
                  value={topK}
                  onChange={(e) => setTopK(Number.parseInt(e.target.value))}
                  min={1}
                  max={50}
                  className="bg-muted/30 border-2"
                />
                <p className="text-xs text-muted-foreground">Number of results to return</p>
              </div>
              <div className="space-y-2">
                <Label>Chunk Token Limit</Label>
                <Input
                  type="number"
                  value={chunkTokens}
                  onChange={(e) => setChunkTokens(Number.parseInt(e.target.value))}
                  min={128}
                  max={2048}
                  className="bg-muted/30 border-2"
                />
                <p className="text-xs text-muted-foreground">Tokens per text chunk</p>
              </div>
              <div className="space-y-2">
                <Label>Reranker Model</Label>
                <Input
                  value={rerankerModel}
                  onChange={(e) => setRerankerModel(e.target.value)}
                  disabled={!rerankerEnabled}
                  className="font-mono text-xs bg-muted/30 border-2"
                />
                <p className="text-xs text-muted-foreground">Cross-encoder for reranking</p>
              </div>
            </div>

            <div className="flex items-center gap-3 p-4 bg-muted/30 rounded-sm border border-border">
              <Checkbox
                id="reranker"
                checked={rerankerEnabled}
                onCheckedChange={(checked) => setRerankerEnabled(checked as boolean)}
              />
              <Label htmlFor="reranker" className="cursor-pointer">
                Enable cross-encoder reranking
              </Label>
            </div>
          </CardContent>
        </Card>

        {/* Save Button */}
        <div className="flex justify-end">
          <Button onClick={saveConfig} disabled={saving} size="lg" className="px-8">
            {saving ? (
              <>
                <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="h-5 w-5 mr-2" />
                Save Configuration
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}
