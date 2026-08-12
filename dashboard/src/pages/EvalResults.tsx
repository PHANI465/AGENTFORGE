import { useState } from "react"
import { Link } from "react-router-dom"
import { agentsApi, evalsApi } from "../api/client"
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
} from "../components/ui"
import type { EvalTestCase } from "../api/types"

interface DraftCase {
  input: string
  expectedOutput: string
  expectedTools: string
}

function CreateSuiteForm({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false)
  const { data: agents } = useApi(() => agentsApi.list(), [])
  const [name, setName] = useState("")
  const [agentId, setAgentId] = useState("")
  const [cases, setCases] = useState<DraftCase[]>([
    { input: "", expectedOutput: "", expectedTools: "" },
  ])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const updateCase = (i: number, patch: Partial<DraftCase>) => {
    setCases((prev) => prev.map((c, idx) => (idx === i ? { ...c, ...patch } : c)))
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      const test_cases: EvalTestCase[] = cases
        .filter((c) => c.input.trim())
        .map((c, i) => ({
          id: `tc-${i + 1}`,
          input: c.input,
          expected_output: c.expectedOutput.trim() || null,
          expected_tool_calls: c.expectedTools
            .split(",")
            .map((t) => t.trim())
            .filter(Boolean),
        }))
      await evalsApi.createSuite({ name, agent_id: agentId, test_cases })
      setName("")
      setAgentId("")
      setCases([{ input: "", expectedOutput: "", expectedTools: "" }])
      setOpen(false)
      onCreated()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setSubmitting(false)
    }
  }

  if (!open) {
    return <Button onClick={() => setOpen(true)}>+ New Suite</Button>
  }

  return (
    <Card className="rise-in mb-6">
      <form onSubmit={submit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <Field label="Suite name">
            <Input required value={name} onChange={(e) => setName(e.target.value)} />
          </Field>
          <Field label="Agent">
            <select
              required
              value={agentId}
              onChange={(e) => setAgentId(e.target.value)}
              className="w-full rounded-sm border border-deck-600 bg-deck-900 px-3 py-2 text-sm text-deck-50"
            >
              <option value="">select an agent…</option>
              {agents?.data.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
          </Field>
        </div>

        <div className="space-y-3">
          <span className="label block text-deck-300">Test cases</span>
          {cases.map((c, i) => (
            <div key={i} className="grid grid-cols-3 gap-2 rounded-sm border border-deck-700 p-3">
              <Input
                placeholder="input"
                value={c.input}
                onChange={(e) => updateCase(i, { input: e.target.value })}
              />
              <Input
                placeholder="expected output (optional)"
                value={c.expectedOutput}
                onChange={(e) => updateCase(i, { expectedOutput: e.target.value })}
              />
              <Input
                placeholder="expected tools, comma-sep"
                value={c.expectedTools}
                onChange={(e) => updateCase(i, { expectedTools: e.target.value })}
              />
            </div>
          ))}
          <Button
            type="button"
            variant="ghost"
            onClick={() =>
              setCases((prev) => [...prev, { input: "", expectedOutput: "", expectedTools: "" }])
            }
          >
            + Add test case
          </Button>
        </div>

        {error && <ErrorState message={error} />}
        <div className="flex gap-3">
          <Button type="submit" disabled={submitting || !agentId}>
            {submitting ? "Creating…" : "Create Suite"}
          </Button>
          <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
            Cancel
          </Button>
        </div>
      </form>
    </Card>
  )
}

export function EvalResults() {
  const { data, loading, error, refetch } = useApi(() => evalsApi.listSuites(), [])

  return (
    <div>
      <PageHeader
        eyebrow="Test Suites"
        title="Evaluations"
        action={<CreateSuiteForm onCreated={refetch} />}
      />

      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}
      {data && data.data.length === 0 && (
        <EmptyState message="No eval suites yet. Create one above." />
      )}

      {data && data.data.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.data.map((suite, i) => (
            <Link
              key={suite.id}
              to={`/evals/${suite.id}`}
              className="rise-in block"
              style={{ animationDelay: `${i * 40}ms` }}
            >
              <Card className="h-full transition-colors hover:border-signal/40">
                <h3 className="mb-2 font-display text-lg text-deck-50">{suite.name}</h3>
                <div className="label text-deck-500">
                  {suite.test_cases.length} test case
                  {suite.test_cases.length === 1 ? "" : "s"}
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

