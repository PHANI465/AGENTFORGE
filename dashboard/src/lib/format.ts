export function formatUsd(value: number): string {
  if (value === 0) return "$0.00"
  if (value < 0.01) return `$${value.toFixed(6)}`
  return `$${value.toFixed(4)}`
}

export function formatTokens(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`
  return String(value)
}

export function formatMs(value: number | null | undefined): string {
  if (value == null) return "—"
  if (value >= 1000) return `${(value / 1000).toFixed(2)}s`
  return `${value}ms`
}

export function formatRelativeTime(iso: string | null): string {
  if (!iso) return "—"
  const date = new Date(iso)
  const diffMs = Date.now() - date.getTime()
  const diffSec = Math.round(diffMs / 1000)
  if (diffSec < 60) return `${diffSec}s ago`
  const diffMin = Math.round(diffSec / 60)
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHr = Math.round(diffMin / 60)
  if (diffHr < 24) return `${diffHr}h ago`
  const diffDay = Math.round(diffHr / 24)
  return `${diffDay}d ago`
}

export function formatDateTime(iso: string | null): string {
  if (!iso) return "—"
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

export const STATUS_COLORS: Record<string, string> = {
  active: "text-lime bg-lime/10 border-lime/30",
  draft: "text-signal bg-signal/10 border-signal/30",
  archived: "text-deck-300 bg-deck-700/50 border-deck-600",
  completed: "text-lime bg-lime/10 border-lime/30",
  running: "text-cyan bg-cyan/10 border-cyan/30",
  pending: "text-deck-300 bg-deck-700/50 border-deck-600",
  failed: "text-danger bg-danger/10 border-danger/30",
}
