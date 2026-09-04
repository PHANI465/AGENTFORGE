import { useState } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"
import { agentsApi, analyticsApi, knowledgeApi, runsApi } from "../api/client"
import { useApi } from "../lib/useApi"
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  Field,
  Input,
  LoadingState,
  PageHeader,
  StatusPill,
  Textarea,
} from "../components/ui"
import { formatDateTime, formatUsd } from "../lib/format"
import type { Agent, AgentUpdate } from "../api/types"

function RunTester({ agentId, onRan }: { agentId: string; onRan: () => void }) {
  const [input, setInput] = useState("")
  const [running, setRunning] = useState(false)
  const [output, setOutput] = useState<string | null>(null)
  const [status, setStatus] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim()) return
    setRunning(true)
    setError(null)
    setOutput(null)
    try {
      const res = await runsApi.run(agentId, input)
      setOutput(res.data.output)
      setStatus(res.data.status)
      onRan()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setRunning(false)
    }
  }

  return (
    <Card>
      <div className="label mb-3 text-deck-300">Test Run</div>
      <form onSubmit={submit} className="flex gap-2">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Send a message to this agent…"
          disabled={running}
        />
        <Button type="submit" disabled={running || !input.trim()}>
          {running ? "Running…" : "Run"}
        </Button>
      </form>
      {error && (
        <div className="mt-3">
          <ErrorState message={error} />
        </div>
      )}
      {output !== null && (
        <div className="mt-3 rounded-sm border border-deck-700 bg-deck-900 p-3">
          <div className="mb-1.5 flex items-center gap-2">
            {status && <StatusPill status={status} />}
          </div>
          <p className="whitespace-pre-wrap text-sm text-deck-100">{output}</p>
        </div>
      )}
    </Card>
  )
}

function RecentRuns({ agentId, refreshKey }: { agentId: string; refreshKey: number }) {
  const { data, loading, error } = useApi(
    () => runsApi.listForAgent(agentId, 10),
    [agentId, refreshKey],
  )

  return (
    <Card>
      <div className="label mb-3 text-deck-300">Recent Runs</div>
      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}
      {data && data.data.length === 0 && <EmptyState message="No runs yet." />}
      {data && data.data.length > 0 && (
        <div className="space-y-2">
          {data.data.map((run) => (
            <Link
              key={run.id}
              to={`/runs/${run.id}/trace`}
              className="flex items-center justify-between rounded-sm border border-deck-700 px-3 py-2 text-sm transition-colors hover:border-signal/40 hover:bg-deck-800/50"
            >
              <span className="truncate pr-3 text-deck-200">{run.input}</span>
              <div className="flex shrink-0 items-center gap-3">
                <span className="label text-deck-500">{formatDateTime(run.started_at)}</span>
                <StatusPill status={run.status} />
              </div>
            </Link>
          ))}
        </div>
      )}
    </Card>
  )
}

function CostSummary({ agentId }: { agentId: string }) {
  const { data, loading } = useApi(() => analyticsApi.usage(30, agentId), [agentId])

  if (loading || !data) return <Card><LoadingState /></Card>

  const u = data.data
  return (
    <Card>
      <div className="label mb-3 text-deck-300">Cost — Last 30 Days</div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <div className="font-display text-2xl text-deck-50">{formatUsd(u.total_cost_usd)}</div>
          <div className="label text-deck-500">total spend</div>
        </div>
        <div>
          <div className="font-display text-2xl text-deck-50">{u.total_calls}</div>
          <div className="label text-deck-500">calls</div>
        </div>
        <div>
          <div className="font-display text-lg text-deck-100">
            {u.total_tokens_in + u.total_tokens_out}
          </div>
          <div className="label text-deck-500">tokens</div>
        </div>
        <div>
          <div className="font-display text-lg text-deck-100">
            {formatUsd(u.avg_cost_per_call_usd)}
          </div>
          <div className="label text-deck-500">avg / call</div>
        </div>
      </div>
    </Card>
  )
}

function ConfigEditor({
  agentId,
  initial,
  onSaved,
}: {
  agentId: string
  initial: Agent
  onSaved: () => void
}) {
  const [systemPrompt, setSystemPrompt] = useState(initial.system_prompt)
  const [safetyRules, setSafetyRules] = useState(initial.safety_policy.rules.join("\n"))
  const [onViolation, setOnViolation] = useState(initial.safety_policy.on_violation)
  const [dailyBudget, setDailyBudget] = useState(
    initial.config.optimization.daily_budget_usd?.toString() ?? "",
  )
  const [enableCaching, setEnableCaching] = useState(initial.config.optimization.enable_caching)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const save = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const payload: AgentUpdate = {
        system_prompt: systemPrompt,
        safety_policy: {
          rules: safetyRules.split("\n").map((r) => r.trim()).filter(Boolean),
          on_violation: onViolation,
        },
        config: {
          ...initial.config,
          optimization: {
            ...initial.config.optimization,
            enable_caching: enableCaching,
            daily_budget_usd: dailyBudget.trim() ? Number(dailyBudget) : null,
          },
        },
      }
      await agentsApi.update(agentId, payload)
      onSaved()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card>
      <div className="label mb-4 text-deck-300">Configuration</div>
      <form onSubmit={save} className="space-y-4">
        <Field label="System prompt">
          <Textarea
            rows={4}
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
          />
        </Field>
        <Field label="Safety rules (one per line)">
          <Textarea
            rows={2}
            value={safetyRules}
            onChange={(e) => setSafetyRules(e.target.value)}
            placeholder="never share customer PII"
          />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="On violation">
            <select
              value={onViolation}
              onChange={(e) =>
                setOnViolation(e.target.value as "block" | "warn" | "log")
              }
              className="w-full rounded-sm border border-deck-600 bg-deck-900 px-3 py-2 text-sm text-deck-50"
            >
              <option value="log">log</option>
              <option value="warn">warn</option>
              <option value="block">block</option>
            </select>
          </Field>
          <Field label="Daily budget (USD, blank = unlimited)">
            <Input
              type="number"
              step="0.000001"
              value={dailyBudget}
              onChange={(e) => setDailyBudget(e.target.value)}
              placeholder="unlimited"
            />
          </Field>
        </div>
        <label className="label flex cursor-pointer items-center gap-2 !text-[11px] !normal-case text-deck-200">
          <input
            type="checkbox"
            checked={enableCaching}
            onChange={(e) => setEnableCaching(e.target.checked)}
            className="accent-signal"
          />
          Enable response caching
        </label>
        {error && <ErrorState message={error} />}
        <Button type="submit" disabled={saving}>
          {saving ? "Saving…" : "Save Changes"}
        </Button>
      </form>
    </Card>
  )
}

function KnowledgeCard({ agentId }: { agentId: string }) {
  const { data, loading, refetch } = useApi(() => knowledgeApi.get(agentId), [agentId])
  const [source, setSource] = useState("")
  const [text, setText] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const add = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!text.trim()) return
    setBusy(true)
    setError(null)
    try {
      await knowledgeApi.add(agentId, source.trim() || "document", text.trim())
      setSource("")
      setText("")
      refetch()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  const clear = async () => {
    if (!confirm("Clear this agent's knowledge base?")) return
    setBusy(true)
    try {
      await knowledgeApi.clear(agentId)
      refetch()
    } finally {
      setBusy(false)
    }
  }

  const info = data?.data
  return (
    <Card>
      <div className="label mb-2 text-deck-300">Knowledge base (RAG)</div>
      <p className="mb-4 text-xs leading-relaxed text-deck-400">
        Paste reference text (docs, FAQs, policies). It's chunked and embedded;
        the most relevant parts are pulled into the agent's context on every run,
        so it can answer from <em>your</em> material — not just the model's memory.
        Needs an OpenAI-compatible key for embeddings.
      </p>

      {info && info.chunk_count > 0 && (
        <div className="mb-4 flex items-center justify-between rounded-xl border border-deck-700 bg-deck-900/50 px-3 py-2">
          <span className="text-xs text-deck-200">
            <span className="font-mono text-signal">{info.chunk_count}</span> chunk
            {info.chunk_count === 1 ? "" : "s"}
            {info.sources.length > 0 && (
              <span className="text-deck-500"> · {info.sources.join(", ")}</span>
            )}
          </span>
          <button
            onClick={clear}
            disabled={busy}
            className="font-mono text-[11px] uppercase tracking-wider text-deck-400 hover:text-danger"
          >
            Clear
          </button>
        </div>
      )}

      <form onSubmit={add} className="space-y-3">
        <Field label="Source name (optional)">
          <Input value={source} onChange={(e) => setSource(e.target.value)} placeholder="e.g. product-faq" />
        </Field>
        <Field label="Text">
          <Textarea
            rows={4}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste documents, FAQs, policies…"
          />
        </Field>
        {error && <ErrorState message={error} />}
        <Button type="submit" disabled={busy || !text.trim()}>
          {busy ? "Embedding…" : loading ? "Loading…" : "Add to knowledge base"}
        </Button>
      </form>
    </Card>
  )
}

export function AgentDetail() {
  const { agentId } = useParams<{ agentId: string }>()
  const navigate = useNavigate()
  const [refreshKey, setRefreshKey] = useState(0)
  const [cloning, setCloning] = useState(false)
  const [cloneError, setCloneError] = useState<string | null>(null)
  const { data, loading, error, refetch } = useApi(
    () => agentsApi.get(agentId!),
    [agentId, refreshKey],
  )

  const handleDelete = async () => {
    if (!agentId || !confirm("Delete this agent? This cannot be undone.")) return
    await agentsApi.delete(agentId)
    navigate("/agents")
  }

  const handleClone = async () => {
    if (!agentId) return
    setCloning(true)
    setCloneError(null)
    try {
      const cloned = await agentsApi.clone(agentId)
      navigate(`/agents/${cloned.data.id}`)
    } catch (err) {
      setCloneError(err instanceof Error ? err.message : String(err))
      setCloning(false)
    }
  }

  if (loading) return <LoadingState />
  if (error) return <ErrorState message={error} />
  if (!data) return null

  const agent = data.data

  return (
    <div>
      <PageHeader
        eyebrow={agent.model}
        title={agent.name}
        action={
          <div className="flex items-center gap-3">
            <StatusPill status={agent.status} />
            <Button variant="ghost" onClick={handleClone} disabled={cloning}>
              {cloning ? "Cloning…" : "Clone"}
            </Button>
            <Button variant="danger" onClick={handleDelete}>
              Delete
            </Button>
          </div>
        }
      />

      {cloneError && (
        <div className="mb-6">
          <ErrorState message={cloneError} />
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <RunTester agentId={agent.id} onRan={() => setRefreshKey((k) => k + 1)} />
          <RecentRuns agentId={agent.id} refreshKey={refreshKey} />
          <ConfigEditor
            agentId={agent.id}
            initial={agent}
            onSaved={() => {
              refetch()
              setRefreshKey((k) => k + 1)
            }}
          />
          <KnowledgeCard agentId={agent.id} />
        </div>
        <div className="space-y-6">
          <CostSummary agentId={agent.id} />
          <Card>
            <div className="label mb-3 text-deck-300">Tools</div>
            {agent.tools.length === 0 ? (
              <p className="text-xs text-deck-500">No tools attached.</p>
            ) : (
              <div className="space-y-2">
                {agent.tools.map((t) => (
                  <div key={t.name} className="rounded-sm border border-deck-700 px-3 py-2">
                    <div className="font-mono text-xs text-signal">{t.name}</div>
                    <div className="mt-0.5 text-xs text-deck-400">{t.description}</div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  )
}
