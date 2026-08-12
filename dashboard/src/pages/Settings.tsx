import { useState } from "react"
import { apiKeysApi } from "../api/client"
import { useApi } from "../lib/useApi"
import { useAuth } from "../lib/auth"
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  Field,
  Input,
  LoadingState,
  PageHeader,
} from "../components/ui"
import { formatDateTime } from "../lib/format"

function ApiKeys() {
  const { data, loading, error, refetch } = useApi(() => apiKeysApi.list(), [])
  const [userId, setUserId] = useState("")
  const [creating, setCreating] = useState(false)
  const [newKey, setNewKey] = useState<string | null>(null)
  const [createError, setCreateError] = useState<string | null>(null)

  const create = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!userId.trim()) return
    setCreating(true)
    setCreateError(null)
    try {
      const res = await apiKeysApi.create(userId.trim())
      setNewKey(res.data.raw_key)
      setUserId("")
      refetch()
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : String(err))
    } finally {
      setCreating(false)
    }
  }

  return (
    <Card>
      <div className="label mb-4 text-deck-300">API Keys</div>

      <form onSubmit={create} className="mb-4 flex gap-2">
        <Field label="New key for user">
          <Input
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            placeholder="e.g. jane@team.dev"
          />
        </Field>
        <div className="flex items-end">
          <Button type="submit" disabled={creating || !userId.trim()}>
            {creating ? "Minting…" : "Generate"}
          </Button>
        </div>
      </form>

      {createError && <ErrorState message={createError} />}

      {newKey && (
        <div className="mb-4 rounded-sm border border-signal/40 bg-signal/5 p-3">
          <p className="label mb-1 text-signal">
            save this now — it will not be shown again
          </p>
          <code className="block break-all font-mono text-sm text-deck-50">{newKey}</code>
        </div>
      )}

      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}
      {data && data.data.length === 0 && <EmptyState message="No API keys minted yet." />}
      {data && data.data.length > 0 && (
        <div className="space-y-2">
          {data.data.map((k) => (
            <div
              key={k.id}
              className="flex items-center justify-between rounded-sm border border-deck-700 px-3 py-2 text-sm"
            >
              <span className="text-deck-200">{k.user_id}</span>
              <div className="flex items-center gap-3">
                <span className="label text-deck-500">{k.provider}</span>
                <span className="label text-deck-600">{formatDateTime(k.created_at)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  )
}

function SessionCard() {
  const { apiKey, signOut } = useAuth()
  return (
    <Card>
      <div className="label mb-3 text-deck-300">Current Session</div>
      <p className="mb-3 font-mono text-xs text-deck-400">
        {apiKey?.slice(0, 8)}••••••••••••••••••••
      </p>
      <Button variant="ghost" onClick={signOut}>
        Sign out
      </Button>
    </Card>
  )
}

function SafetyPolicyNote() {
  return (
    <Card>
      <div className="label mb-2 text-deck-300">Safety Policies</div>
      <p className="text-xs text-deck-400">
        Safety rules and enforcement mode (block / warn / log) are configured per agent —
        open an agent's detail page and edit its configuration there. There is no
        platform-wide policy; every agent decides its own rules.
      </p>
    </Card>
  )
}

export function Settings() {
  return (
    <div>
      <PageHeader eyebrow="Configuration" title="Settings" />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="space-y-6">
          <ApiKeys />
        </div>
        <div className="space-y-6">
          <SessionCard />
          <SafetyPolicyNote />
        </div>
      </div>
    </div>
  )
}
