"use client"

import { Search, FileUp, Settings } from "lucide-react"
import { cn } from "@/lib/utils"

interface NavigationProps {
  currentPage: "search" | "ingest" | "settings"
  onNavigate: (page: "search" | "ingest" | "settings") => void
}

const navItems = [
  { id: "search" as const, label: "Search", icon: Search },
  { id: "ingest" as const, label: "Ingest", icon: FileUp },
  { id: "settings" as const, label: "Settings", icon: Settings },
]

export function Navigation({ currentPage, onNavigate }: NavigationProps) {
  return (
    <nav className="flex items-center">
      <div className="flex items-center gap-1 p-1 bg-muted/50 rounded-sm border border-border">
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = currentPage === item.id

          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={cn(
                "relative flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-sm transition-all duration-200",
                isActive
                  ? "bg-card text-foreground shadow-sm border border-border"
                  : "text-muted-foreground hover:text-foreground hover:bg-card/50",
              )}
            >
              <Icon className="h-4 w-4" strokeWidth={1.5} />
              <span>{item.label}</span>
              {isActive && (
                <span className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-1 h-1 bg-primary rounded-full" />
              )}
            </button>
          )
        })}
      </div>
    </nav>
  )
}
