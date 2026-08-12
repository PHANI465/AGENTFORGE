import { useState } from "react"
import { useAuth } from "../lib/auth"
import { Button, Card, Input } from "../components/ui"

export function SignIn() {
  const { signIn } = useAuth()
  const [key, setKey] = useState("")

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (key.trim()) signIn(key.trim())
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-6">
      <div className="w-full max-w-sm rise-in">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-sm border border-signal/40 bg-signal/10 text-signal">
            <span className="font-display text-2xl italic">A</span>
          </div>
          <h1 className="font-display text-2xl text-deck-50">AgentForge</h1>
          <p className="label mt-2 text-deck-400">authenticate to enter the deck</p>
        </div>

        <Card>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <span className="label mb-1.5 block text-deck-300">X-API-Key</span>
              <Input
                type="password"
                autoFocus
                placeholder="afk_…"
                value={key}
                onChange={(e) => setKey(e.target.value)}
              />
            </div>
            <Button type="submit" className="w-full" disabled={!key.trim()}>
              Enter
            </Button>
          </form>
        </Card>

        <p className="label mt-4 text-center !text-[10px] text-deck-500">
          no key yet? run{" "}
          <code className="font-mono text-deck-300">uv run python scripts/seed.py</code> from
          the repo root
        </p>
      </div>
    </div>
  )
}
