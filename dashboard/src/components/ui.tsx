import type { ReactNode } from "react"
import { STATUS_COLORS } from "../lib/format"

export function Card({
  children,
  className = "",
}: {
  children: ReactNode
  className?: string
}) {
  return <div className={`hud-card p-6 ${className}`}>{children}</div>
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
    <div className="mb-9 flex flex-wrap items-end justify-between gap-4 rise-in">
      <div>
        <div className="label mb-2 text-signal">{eyebrow}</div>
        <h1 className="font-display text-4xl leading-none text-deck-50">{title}</h1>
      </div>
      {action}
    </div>
  )
}

export function StatusPill({ status }: { status: string }) {
  const cls = STATUS_COLORS[status] ?? "text-deck-300 bg-deck-700/50 border-deck-600"
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider ${cls}`}
    >
      <span className="h-1 w-1 rounded-full bg-current" />
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
    "inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed active:scale-[0.97]"
  const variants = {
    primary:
      "text-white bg-[linear-gradient(100deg,var(--color-signal),var(--color-pink))] shadow-[0_10px_28px_-10px_rgba(139,92,255,0.6)] hover:shadow-[0_14px_34px_-8px_rgba(255,77,146,0.6)] hover:brightness-110",
    ghost:
      "border border-deck-600 text-deck-100 hover:border-signal/60 hover:bg-deck-800 hover:text-deck-50",
    danger: "border border-danger/40 text-danger hover:bg-danger/10 hover:border-danger/70",
  }
  return (
    <button className={`${base} ${variants[variant]} ${className}`} {...props}>
      {children}
    </button>
  )
}

const fieldBase =
  "w-full rounded-xl border border-deck-600 bg-deck-900/70 px-3.5 py-2.5 text-sm text-deck-50 placeholder:text-deck-500 transition-all focus:border-signal/70 focus:outline-none focus:ring-4 focus:ring-signal/15"

export function Input({ className = "", ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input className={`${fieldBase} ${className}`} {...props} />
}

export function Select({
  className = "",
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={`${fieldBase} cursor-pointer ${className}`} {...props} />
}

export function Textarea({
  className = "",
  ...props
}: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={`${fieldBase} ${className}`} {...props} />
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="label mb-2 block text-deck-300">{label}</span>
      {children}
    </label>
  )
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-deck-700 px-6 py-14 text-center">
      <p className="label text-deck-500">{message}</p>
    </div>
  )
}

export function LoadingState() {
  return (
    <div className="flex items-center gap-2.5 px-2 py-10">
      <span className="status-dot-live h-2 w-2 rounded-full bg-lime" />
      <span className="label text-deck-400">Loading…</span>
    </div>
  )
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-danger/30 bg-danger/8 px-4 py-3">
      <p className="label !normal-case !tracking-normal text-danger">{message}</p>
    </div>
  )
}
