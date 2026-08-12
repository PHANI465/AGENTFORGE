import { useState } from "react"
import { Link } from "react-router-dom"
import { agentsApi } from "../api/client"
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
import { formatRelativeTime } from "../lib/format"

const BUILTIN_TOOLS = [
  {
    name: "calculate",
    description: "Evaluates a mathematical expression.",
    parameters_schema: {
      type: "object",
      properties: { expression: { type: "string" } },
      required: ["expression"],
    },
  },
  {
    name: "get_current_time",
    description: "Returns the current UTC time.",
    parameters_schema: { type: "object", properties: {}, required: [] },
  },
]

function CreateAgentForm({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState("")
  const [model, setModel] = useState("gpt-4o-mini")
  const [prompt, setPrompt] = useState("You are a helpful assistant.")
  const [tools, setTools] = useState<string[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const toggleTool = (toolName: string) => {
    setTools((prev) =>
      prev.includes(toolName) ? prev.filter((t) => t !== toolName) : [...prev, toolName],
    )
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      await agentsApi.create({
        name,
        model,
        system_prompt: prompt,
        tools: BUILTIN_TOOLS.filter((t) => tools.includes(t.name)),
      })
      setName("")
      setPrompt("You are a helpful assistant.")
      setTools([])
      setOpen(false)
      onCreated()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setSubmitting(false)
    }
  }

  if (!open) {
    return (
      <Button onClick={() => setOpen(true)} variant="primary">
        + New Agent
      </Button>
    )
  }

  return (
    <Card className="rise-in mb-6">
      <form onSubmit={submit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <Field label="Name">
            <Input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="support-triage-agent"
            />
          </Field>
          <Field label="Model">
            <Input required value={model} onChange={(e) => setModel(e.target.value)} />
          </Field>
        </div>
        <Field label="System prompt">
          <Textarea
            required
            rows={3}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
          />
        </Field>
        <div>
          <span className="label mb-2 block text-deck-300">Tools</span>
          <div className="flex gap-3">
            {BUILTIN_TOOLS.map((t) => (
              <label
                key={t.name}
                className="label flex cursor-pointer items-center gap-2 !text-[11px] !normal-case text-deck-200"
              >
                <input
                  type="checkbox"
                  checked={tools.includes(t.name)}
                  onChange={() => toggleTool(t.name)}
                  className="accent-signal"
                />
                {t.name}
              </label>
            ))}
          </div>
        </div>
        {error && <ErrorState message={error} />}
        <div className="flex gap-3">
          <Button type="submit" disabled={submitting}>
            {submitting ? "Creating…" : "Create Agent"}
          </Button>
          <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
            Cancel
          </Button>
        </div>
      </form>
    </Card>
  )
}

export function AgentCatalog() {
  const { data, loading, error, refetch } = useApi(() => agentsApi.list(), [])

  return (
    <div>
      <PageHeader
        eyebrow="Roster"
        title="Agents"
        action={<CreateAgentForm onCreated={refetch} />}
      />

      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}

      {data && data.data.length === 0 && (
        <EmptyState message="No agents yet. Create one above to get started." />
      )}

      {data && data.data.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.data.map((agent, i) => (
            <Link
              key={agent.id}
              to={`/agents/${agent.id}`}
              className="rise-in block"
              style={{ animationDelay: `${i * 40}ms` }}
            >
              <Card className="h-full transition-colors hover:border-signal/40">
                <div className="mb-3 flex items-start justify-between gap-2">
                  <h3 className="font-display text-lg text-deck-50">{agent.name}</h3>
                  <StatusPill status={agent.status} />
                </div>
                <p className="mb-4 line-clamp-2 text-xs text-deck-300">{agent.system_prompt}</p>
                <div className="flex items-center justify-between border-t border-deck-700 pt-3">
                  <span className="label text-deck-400">{agent.model}</span>
                  <span className="label text-deck-500">
                    {agent.tools.length} tool{agent.tools.length === 1 ? "" : "s"}
                  </span>
                </div>
                <div className="label mt-2 text-deck-600">
                  updated {formatRelativeTime(agent.updated_at)}
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
