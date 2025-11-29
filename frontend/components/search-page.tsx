"use client"

import type React from "react"

import { useState, useEffect } from "react"
import { Search, Clock, FileText, Sparkles, ToggleLeft, ToggleRight, BookMarked } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import { toast } from "sonner"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

interface SearchResult {
  chunk_id: string
  doc_id: string
  title?: string
  score: number
  text_snippet: string
  metadata?: Record<string, unknown>
}

export function SearchPage() {
  const [query, setQuery] = useState("")
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [searchTime, setSearchTime] = useState(0)
  const [hybrid, setHybrid] = useState(true)
  const [rerank, setRerank] = useState(true)
  const [topK, setTopK] = useState(5)
  const [hasSearched, setHasSearched] = useState(false)

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
        console.warn("Could not load config, using defaults:", err)
      }
    }
    loadConfig()
  }, [])

  const loadConfig = async () => {
    try {
      const response = await fetch(`${API_BASE}/config`)
      if (response.ok) {
        const config = await response.json()
        setTopK(config.search.top_k)
        setRerank(config.search.reranker_enabled)
      }
    } catch (err) {
      console.warn("Could not reload config, using current values:", err)
    }
  }

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    setResults([])
    setHasSearched(true)

    try {
      // Reload config before search to ensure latest settings
      await loadConfig()

      const response = await fetch(`${API_BASE}/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ q: query, top_k: topK, hybrid, rerank }),
      })

      if (!response.ok) {
        throw new Error(`Search failed: ${response.statusText}`)
      }

      const data = await response.json()
      setResults(data.results)
      setSearchTime(data.search_time_ms)
    } catch (err) {
      toast.error("Search failed", {
        description: err instanceof Error ? err.message : "Unknown error occurred",
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="text-center space-y-2">
        <div className="flex items-center justify-center gap-3">
          <div className="h-px w-12 bg-gradient-to-r from-transparent to-border" />
          <BookMarked className="h-8 w-8 text-primary" strokeWidth={1.5} />
          <div className="h-px w-12 bg-gradient-to-l from-transparent to-border" />
        </div>
        <h2 className="text-3xl font-bold text-foreground tracking-tight">Search the Archives</h2>
        <p className="text-muted-foreground max-w-md mx-auto">
          Query your document collection using advanced semantic search
        </p>
      </div>

      {/* Search Form */}
      <Card className="max-w-4xl mx-auto border-2 shadow-lg">
        <CardContent className="pt-6">
          <form onSubmit={handleSearch} className="space-y-6">
            {/* Search Input */}
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
              <Input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Enter your search query..."
                className="pl-12 pr-4 py-6 text-lg bg-muted/30 border-2 focus:border-primary/50"
                disabled={loading}
              />
            </div>

            {/* Search Options */}
            <div className="flex flex-wrap items-center gap-6 p-4 bg-muted/30 rounded-sm border border-border">
              <div className="flex items-center gap-2">
                <Label htmlFor="topK" className="text-sm text-muted-foreground whitespace-nowrap">
                  Results:
                </Label>
                <Input
                  id="topK"
                  type="number"
                  value={topK}
                  onChange={(e) => setTopK(Number.parseInt(e.target.value) || 5)}
                  className="w-16 h-8 text-center bg-card"
                  min={1}
                  max={50}
                />
              </div>

              <div className="h-6 w-px bg-border" />

              <div className="flex items-center gap-2">
                <Checkbox id="hybrid" checked={hybrid} onCheckedChange={(checked) => setHybrid(checked as boolean)} />
                <Label htmlFor="hybrid" className="text-sm cursor-pointer flex items-center gap-1.5">
                  <Sparkles className="h-4 w-4 text-primary" />
                  Hybrid Search
                </Label>
              </div>

              <div className="flex items-center gap-2">
                <Checkbox id="rerank" checked={rerank} onCheckedChange={(checked) => setRerank(checked as boolean)} />
                <Label htmlFor="rerank" className="text-sm cursor-pointer flex items-center gap-1.5">
                  {rerank ? (
                    <ToggleRight className="h-4 w-4 text-primary" />
                  ) : (
                    <ToggleLeft className="h-4 w-4 text-muted-foreground" />
                  )}
                  Reranking
                </Label>
              </div>

              <div className="flex-1" />

              <Button type="submit" disabled={loading || !query.trim()} className="px-8">
                {loading ? (
                  <>
                    <span className="animate-pulse">Searching</span>
                    <span className="animate-bounce">...</span>
                  </>
                ) : (
                  <>
                    <Search className="h-4 w-4 mr-2" />
                    Search
                  </>
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Results */}
      {results.length > 0 && (
        <div className="max-w-4xl mx-auto space-y-4">
          <div className="flex items-center justify-between px-2">
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-primary" />
              <span className="font-medium">
                Found {results.length} {results.length === 1 ? "result" : "results"}
              </span>
            </div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Clock className="h-4 w-4" />
              <span>{searchTime.toFixed(1)}ms</span>
            </div>
          </div>

          <div className="space-y-4">
            {results.map((result, index) => (
              <Card
                key={result.chunk_id}
                className="group border-2 hover:border-primary/30 transition-colors duration-300 overflow-hidden"
              >
                <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-primary/50 to-primary/10 opacity-0 group-hover:opacity-100 transition-opacity" />
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary" className="font-mono text-xs">
                          Doc: {result.doc_id}
                        </Badge>
                        {result.title && <span className="text-sm font-medium text-foreground">{result.title}</span>}
                      </div>
                    </div>
                    <Badge variant="outline" className="shrink-0">
                      Score: {result.score.toFixed(3)}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="pt-0">
                  <p className="text-foreground/90 leading-relaxed">{result.text_snippet}</p>
                  {result.metadata && Object.keys(result.metadata).length > 0 && (
                    <div className="mt-4 pt-4 border-t border-border">
                      <p className="text-xs text-muted-foreground font-mono">
                        <strong>Metadata:</strong> {JSON.stringify(result.metadata, null, 2)}
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* No Results */}
      {!loading && hasSearched && results.length === 0 && (
        <div className="text-center py-16">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-muted mb-4">
            <Search className="h-8 w-8 text-muted-foreground" />
          </div>
          <p className="text-lg text-muted-foreground">
            No results found for "<span className="font-medium text-foreground">{query}</span>"
          </p>
          <p className="text-sm text-muted-foreground mt-1">Try adjusting your search terms or options</p>
        </div>
      )}

      {/* Empty State */}
      {!hasSearched && (
        <div className="text-center py-16">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-gradient-to-br from-primary/10 to-primary/5 border border-primary/20 mb-4">
            <BookMarked className="h-10 w-10 text-primary" strokeWidth={1.5} />
          </div>
          <p className="text-lg text-muted-foreground">Enter a query above to begin searching</p>
        </div>
      )}
    </div>
  )
}
