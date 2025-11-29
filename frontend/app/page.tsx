"use client"

import { useState } from "react"
import { Navigation } from "@/components/navigation"
import { SearchPage } from "@/components/search-page"
import { IngestPage } from "@/components/ingest-page"
import { SettingsPage } from "@/components/settings-page"
import { BookOpen, Feather, ScrollText } from "lucide-react"

export default function Home() {
  const [currentPage, setCurrentPage] = useState<"search" | "ingest" | "settings">("search")

  return (
    <div className="min-h-screen bg-background">
      {/* Decorative paper texture overlay */}
      <div className="fixed inset-0 pointer-events-none opacity-[0.03] bg-[url('/paper-grain-texture.jpg')] bg-repeat" />

      {/* Header with vintage styling */}
      <header className="relative border-b-2 border-border bg-card/80 backdrop-blur-sm">
        <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-transparent via-primary/30 to-transparent" />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-20">
            <div className="flex items-center gap-3">
              <div className="relative">
                <div className="absolute inset-0 bg-primary/20 blur-xl rounded-full" />
                <div className="relative p-2.5 bg-gradient-to-br from-primary/10 to-primary/5 border border-primary/20 rounded-sm">
                  <ScrollText className="h-6 w-6 text-primary" strokeWidth={1.5} />
                </div>
              </div>
              <div>
                <h1 className="text-xl font-bold text-foreground tracking-tight">The Archive</h1>
                <p className="text-xs text-muted-foreground tracking-widest uppercase">Semantic Search Service</p>
              </div>
            </div>

            <Navigation currentPage={currentPage} onNavigate={setCurrentPage} />
          </div>
        </div>
        <div className="absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-border to-transparent" />
      </header>

      {/* Main content */}
      <main className="relative max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        {/* Decorative corner flourishes */}
        <div className="absolute top-4 left-4 w-8 h-8 border-l-2 border-t-2 border-primary/20 rounded-tl-sm" />
        <div className="absolute top-4 right-4 w-8 h-8 border-r-2 border-t-2 border-primary/20 rounded-tr-sm" />

        {currentPage === "search" && <SearchPage />}
        {currentPage === "ingest" && <IngestPage />}
        {currentPage === "settings" && <SettingsPage />}

        <div className="absolute bottom-4 left-4 w-8 h-8 border-l-2 border-b-2 border-primary/20 rounded-bl-sm" />
        <div className="absolute bottom-4 right-4 w-8 h-8 border-r-2 border-b-2 border-primary/20 rounded-br-sm" />
      </main>

      {/* Footer */}
      <footer className="relative border-t border-border py-6 mt-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-center gap-6 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <BookOpen className="h-4 w-4" />
              <span>Documents preserved with care</span>
            </div>
            <span className="text-border">✦</span>
            <div className="flex items-center gap-2">
              <Feather className="h-4 w-4" />
              <span>Lionel Arce - 2025</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
