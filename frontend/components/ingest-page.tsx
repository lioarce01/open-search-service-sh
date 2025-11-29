"use client"

import type React from "react"

import { useState } from "react"
import { FileUp, FileText, Upload, Check, AlertCircle, Zap, Clock, Scroll } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { toast } from "sonner"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export function IngestPage() {
  const [docId, setDocId] = useState("")
  const [title, setTitle] = useState("")
  const [text, setText] = useState("")
  const [file, setFile] = useState<File | null>(null)
  const [metadata, setMetadata] = useState("")
  const [sync, setSync] = useState(false)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState("")
  const [error, setError] = useState("")

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!docId.trim()) {
      setError("Document ID is required")
      return
    }

    if (!text && !file) {
      setError("Either text content or a file must be provided")
      return
    }

    setLoading(true)
    setError("")
    setMessage("")

    try {
      const formData = new FormData()
      formData.append("doc_id", docId)
      formData.append("sync", sync.toString())

      if (title) formData.append("title", title)
      if (text) formData.append("text", text)
      if (file) formData.append("file", file)

      if (metadata) {
        try {
          JSON.parse(metadata)
          formData.append("metadata", metadata)
        } catch {
          setError("Invalid JSON in metadata")
          setLoading(false)
          return
        }
      }

      const response = await fetch(`${API_BASE}/ingest`, {
        method: "POST",
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || `HTTP ${response.status}`)
      }

      const data = await response.json()

      if (sync) {
        setMessage(`Document "${docId}" ingested successfully with ${data.chunk_count} chunks`)
        toast.success("Document ingested!", {
          description: `${data.chunk_count} chunks created`,
        })
        clearForm()
      } else {
        setMessage(`Document "${docId}" ingestion started...`)
        pollForCompletion()
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Unknown error"
      setError(errorMessage)
      toast.error("Ingestion failed", { description: errorMessage })
    } finally {
      setLoading(false)
    }
  }

  const pollForCompletion = async () => {
    let attempts = 0
    const maxAttempts = 10
    const pollInterval = 1000

    const poll = async () => {
      attempts++
      try {
        const docResponse = await fetch(`${API_BASE}/docs/${docId}`)
        if (docResponse.ok) {
          const docData = await docResponse.json()
          setMessage(`Document "${docId}" ingested successfully with ${docData.chunk_count} chunks`)
          toast.success("Document ingested!")
          clearForm()
          return
        }
      } catch (err) {
        console.warn("Error polling:", err)
      }

      if (attempts < maxAttempts) {
        setTimeout(poll, pollInterval)
      } else {
        clearForm()
      }
    }

    setTimeout(poll, 500)
  }

  const clearForm = () => {
    setDocId("")
    setTitle("")
    setText("")
    setFile(null)
    setMetadata("")
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile) {
      setFile(selectedFile)
      setText("")
    }
  }

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="text-center space-y-2">
        <div className="flex items-center justify-center gap-3">
          <div className="h-px w-12 bg-gradient-to-r from-transparent to-border" />
          <Scroll className="h-8 w-8 text-primary" strokeWidth={1.5} />
          <div className="h-px w-12 bg-gradient-to-l from-transparent to-border" />
        </div>
        <h2 className="text-3xl font-bold text-foreground tracking-tight">Ingest Document</h2>
        <p className="text-muted-foreground max-w-md mx-auto">Add new documents to your searchable archive</p>
      </div>

      {/* Form Card */}
      <Card className="max-w-2xl mx-auto border-2 shadow-lg">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileUp className="h-5 w-5 text-primary" />
            New Document
          </CardTitle>
          <CardDescription>Provide document details and content for indexing</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Document ID */}
            <div className="space-y-2">
              <Label htmlFor="docId" className="flex items-center gap-1">
                Document ID <span className="text-destructive">*</span>
              </Label>
              <Input
                id="docId"
                value={docId}
                onChange={(e) => setDocId(e.target.value)}
                placeholder="unique-document-id"
                required
                disabled={loading}
                className="bg-muted/30 border-2"
              />
            </div>

            {/* Title */}
            <div className="space-y-2">
              <Label htmlFor="title">Title (optional)</Label>
              <Input
                id="title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Document title"
                disabled={loading}
                className="bg-muted/30 border-2"
              />
            </div>

            {/* File Upload */}
            <div className="space-y-2">
              <Label htmlFor="file">Upload File (optional)</Label>
              <div className="relative">
                <Input
                  id="file"
                  type="file"
                  onChange={handleFileChange}
                  accept=".txt,.md,.pdf"
                  disabled={loading}
                  className="bg-muted/30 border-2 border-dashed cursor-pointer file:mr-4 file:py-2 file:px-4 file:border-0 file:text-sm file:font-medium file:bg-primary/10 file:text-primary hover:file:bg-primary/20"
                />
              </div>
              {file && (
                <p className="text-sm text-primary flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  {file.name}
                </p>
              )}
              <p className="text-xs text-muted-foreground">Supported formats: .txt, .md, .pdf</p>
            </div>

            {/* Text Content */}
            <div className="space-y-2">
              <Label htmlFor="text">
                Text Content {!file ? <span className="text-destructive">*</span> : "(optional if file uploaded)"}
              </Label>
              <Textarea
                id="text"
                value={text}
                onChange={(e) => setText(e.target.value)}
                rows={8}
                placeholder="Paste your document text here..."
                disabled={loading || !!file}
                className="bg-muted/30 border-2 resize-none font-serif"
              />
            </div>

            {/* Metadata */}
            <div className="space-y-2">
              <Label htmlFor="metadata">Metadata (JSON, optional)</Label>
              <Textarea
                id="metadata"
                value={metadata}
                onChange={(e) => setMetadata(e.target.value)}
                rows={3}
                placeholder='{"author": "John Doe", "category": "research"}'
                disabled={loading}
                className="bg-muted/30 border-2 resize-none font-mono text-sm"
              />
            </div>

            {/* Sync Option */}
            <div className="flex items-start gap-3 p-4 bg-muted/30 rounded-sm border border-border">
              <Checkbox
                id="sync"
                checked={sync}
                onCheckedChange={(checked) => setSync(checked as boolean)}
                disabled={loading}
              />
              <div className="space-y-1">
                <Label htmlFor="sync" className="cursor-pointer font-medium">
                  Synchronous processing
                </Label>
                <p className="text-xs text-muted-foreground">Wait for completion vs. background processing</p>
              </div>
            </div>

            {/* Submit */}
            <Button type="submit" disabled={loading} className="w-full py-6 text-lg">
              {loading ? (
                <>
                  <Upload className="h-5 w-5 mr-2 animate-bounce" />
                  {sync ? "Processing..." : "Starting..."}
                </>
              ) : (
                <>
                  <Upload className="h-5 w-5 mr-2" />
                  Ingest Document
                </>
              )}
            </Button>

            {/* Mode Indicator */}
            <div className="text-center">
              <p className="text-xs text-muted-foreground inline-flex items-center gap-2">
                {sync ? (
                  <>
                    <Zap className="h-3.5 w-3.5 text-primary" />
                    Synchronous: Wait for completion before response
                  </>
                ) : (
                  <>
                    <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                    Asynchronous: Start in background, poll for completion
                  </>
                )}
              </p>
            </div>
          </form>

          {/* Success Message */}
          {message && (
            <Alert className="mt-6 border-2 border-green-600/30 bg-green-50/50">
              <Check className="h-4 w-4 text-green-600" />
              <AlertDescription className="text-green-800">{message}</AlertDescription>
            </Alert>
          )}

          {/* Error Message */}
          {error && (
            <Alert variant="destructive" className="mt-6 border-2">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
