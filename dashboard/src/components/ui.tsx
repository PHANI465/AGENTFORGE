import type { ReactNode } from "react"
import { STATUS_COLORS } from "../lib/format"

export function Card({
  children,
  className = "",
}: {
  children: ReactNode
  className?: string
}) {
  return <div className={`hud-card rounded-sm p-5 ${className}`}>{children}</div>
}

export function PageHeader({
  eyebrow,
  title,
  action,
}: {
  eyebrow: string
  title: string
  action?: ReactNode
}) {
  return (
    <div className="mb-8 flex items-end justify-between gap-4 rise-in">
      <div>
        <div className="label mb-1.5 text-signal">{eyebrow}</div>
        <h1 className="font-display text-3xl text-deck-50">{title}</h1>
      </div>
      {action}
    </div>
  )
}

export function StatusPill({ status }: { status: string }) {
  const cls = STATUS_COLORS[status] ?? "text-deck-300 bg-deck-700/50 border-deck-600"
  return (
    <span
      className={`label inline-flex items-center rounded-sm border px-2 py-0.5 !text-[10px] ${cls}`}
    >
      {status}
    </span>
  )
}

export function Button({
  children,
  variant = "primary",
  className = "",
  ...props
}: {
  children: ReactNode
  variant?: "primary" | "ghost" | "danger"
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const base =
    "label !text-[11px] !normal-case !tracking-normal !font-medium rounded-sm px-4 py-2 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
  const variants = {
    primary: "bg-signal text-deck-950 hover:bg-signal/85",
    ghost: "border border-deck-600 text-deck-100 hover:border-deck-500 hover:bg-deck-800",
    danger: "border border-danger/40 text-danger hover:bg-danger/10",
  }
  return (
    <button className={`${base} ${variants[variant]} ${className}`} {...props}>
      {children}
    </button>
  )
}

export function Input({ className = "", ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={`w-full rounded-sm border border-deck-600 bg-deck-900 px-3 py-2 text-sm text-deck-50 placeholder:text-deck-500 focus:border-signal/60 focus:outline-none ${className}`}
      {...props}
    />
  )
}

export function Textarea({
  className = "",
  ...props
}: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={`w-full rounded-sm border border-deck-600 bg-deck-900 px-3 py-2 text-sm text-deck-50 placeholder:text-deck-500 focus:border-signal/60 focus:outline-none ${className}`}
      {...props}
    />
  )
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="label mb-1.5 block text-deck-300">{label}</span>
      {children}
    </label>
  )
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-sm border border-dashed border-deck-700 px-6 py-12 text-center">
      <p className="label text-deck-500">{message}</p>
    </div>
  )
}

export function LoadingState() {
  return (
    <div className="flex items-center gap-2 px-2 py-8">
      <span className="status-dot-live h-1.5 w-1.5 rounded-full bg-signal" />
      <span className="label text-deck-400">Loading…</span>
    </div>
  )
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-sm border border-danger/30 bg-danger/5 px-4 py-3">
      <p className="label text-danger">{message}</p>
    </div>
  )
}
