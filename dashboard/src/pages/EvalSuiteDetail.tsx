import { useState } from "react"
import { useParams } from "react-router-dom"
import { evalsApi } from "../api/client"
import { useApi } from "../lib/useApi"
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  StatusPill,
} from "../components/ui"
import { formatDateTime, formatMs, formatUsd } from "../lib/format"
import type { EvalCompareOut, EvalRunOut } from "../api/types"

function RunRow({
  run,
  selected,
  onToggleSelect,
}: {
  run: EvalRunOut
  selected: boolean
  onToggleSelect: () => void
}) {
  return (
    <div
      onClick={onToggleSelect}
      className={`flex cursor-pointer items-center justify-between rounded-sm border px-3 py-2.5 text-sm transition-colors ${
        selected ? "border-signal/60 bg-signal/5" : "border-deck-700 hover:border-deck-500"
      }`}
    >
      <div className="flex items-center gap-3">
        <input type="checkbox" checked={selected} readOnly className="accent-signal" />
        <span className="text-deck-200">{formatDateTime(run.started_at)}</span>
      </div>
      <div className="flex items-center gap-4">
        {run.summary && (
          <>
            <span className="label text-deck-400">
              {run.summary.passed}/{run.summary.total} passed
            </span>
            <span className="label text-deck-400">{formatUsd(run.summary.total_cost_usd)}</span>
          </>
        )}
        <StatusPill status={run.status} />
      </div>
    </div>
  )
}

function CompareView({ compare }: { compare: EvalCompareOut }) {
  const rows = [
    {
      label: "Pass rate",
      a: `${((compare.run_a.summary?.pass_rate ?? 0) * 100).toFixed(0)}%`,
      b: `${((compare.run_b.summary?.pass_rate ?? 0) * 100).toFixed(0)}%`,
      delta: compare.pass_rate_delta,
      good: (d: number) => d >= 0,
    },
    {
      label: "Avg latency",
      a: formatMs(compare.run_a.summary?.avg_latency_ms),
      b: formatMs(compare.run_b.summary?.avg_latency_ms),
      delta: compare.avg_latency_ms_delta,
      good: (d: number) => d <= 0,
    },
    {
      label: "Total cost",
      a: formatUsd(compare.run_a.summary?.total_cost_usd ?? 0),
      b: formatUsd(compare.run_b.summary?.total_cost_usd ?? 0),
      delta: compare.total_cost_usd_delta,
      good: (d: number) => d <= 0,
    },
  ]

  return (
    <Card className="rise-in mt-4">
      <div className="label mb-4 text-deck-300">Comparison — A (earlier) vs B (later)</div>
      <div className="space-y-3">
        {rows.map((r) => (
          <div key={r.label} className="grid grid-cols-4 items-center gap-3 text-sm">
            <span className="label text-deck-400">{r.label}</span>
            <span className="text-deck-100">{r.a}</span>
            <span className="text-deck-100">{r.b}</span>
            <span
              className={
                r.delta == null
                  ? "text-deck-500"
                  : r.good(r.delta)
                    ? "text-lime"
                    : "text-danger"
              }
            >
              {r.delta == null ? "—" : r.delta > 0 ? `+${r.delta.toFixed(4)}` : r.delta.toFixed(4)}
            </span>
          </div>
        ))}
      </div>
    </Card>
  )
}

export function EvalSuiteDetail() {
  const { suiteId } = useParams<{ suiteId: string }>()
  const [refreshKey, setRefreshKey] = useState(0)
  const [running, setRunning] = useState(false)
  const [selected, setSelected] = useState<string[]>([])
  const [compare, setCompare] = useState<EvalCompareOut | null>(null)
  const [compareError, setCompareError] = useState<string | null>(null)

  const { data: suiteData, loading: suiteLoading, error: suiteError } = useApi(
    () => evalsApi.getSuite(suiteId!),
    [suiteId],
  )
  const { data: runsData, loading: runsLoading, refetch } = useApi(
    () => evalsApi.listRuns(suiteId!),
    [suiteId, refreshKey],
  )

  const runSuite = async () => {
    setRunning(true)
    try {
      await evalsApi.runSuite(suiteId!)
      setRefreshKey((k) => k + 1)
      refetch()
    } finally {
      setRunning(false)
    }
  }

  const toggleSelect = (runId: string) => {
    setCompare(null)
    setCompareError(null)
    setSelected((prev) => {
      if (prev.includes(runId)) return prev.filter((id) => id !== runId)
      if (prev.length >= 2) return [prev[1], runId]
      return [...prev, runId]
    })
  }

  const doCompare = async () => {
    if (selected.length !== 2) return
    setCompareError(null)
    try {
      // Compare in chronological order: runsData is newest-first, so the
      // later-index selection is "earlier" (A) and earlier-index is "later" (B).
      const [first, second] = selected
      const firstIdx = runsData?.data.findIndex((r) => r.id === first) ?? 0
      const secondIdx = runsData?.data.findIndex((r) => r.id === second) ?? 0
      const [runA, runB] = firstIdx > secondIdx ? [first, second] : [second, first]
      const res = await evalsApi.compare(runA, runB)
      setCompare(res.data)
    } catch (err) {
      setCompareError(err instanceof Error ? err.message : String(err))
    }
  }

  if (suiteLoading) return <LoadingState />
  if (suiteError) return <ErrorState message={suiteError} />
  if (!suiteData) return null

  const suite = suiteData.data

  return (
    <div>
      <PageHeader
        eyebrow={`${suite.test_cases.length} test cases`}
        title={suite.name}
        action={
          <Button onClick={runSuite} disabled={running}>
            {running ? "Running…" : "Run Suite"}
          </Button>
        }
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Card className="mb-4">
            <div className="label mb-3 text-deck-300">Run History</div>
            {runsLoading && <LoadingState />}
            {runsData && runsData.data.length === 0 && (
              <EmptyState message="No runs yet — click Run Suite to execute it." />
            )}
            {runsData && runsData.data.length > 0 && (
              <div className="space-y-2">
                {runsData.data.map((run) => (
                  <RunRow
                    key={run.id}
                    run={run}
                    selected={selected.includes(run.id)}
                    onToggleSelect={() => toggleSelect(run.id)}
                  />
                ))}
              </div>
            )}
            {selected.length === 2 && (
              <div className="mt-3">
                <Button onClick={doCompare} variant="ghost">
                  Compare selected runs
                </Button>
              </div>
            )}
            {compareError && (
              <div className="mt-3">
                <ErrorState message={compareError} />
              </div>
            )}
          </Card>
          {compare && <CompareView compare={compare} />}
        </div>

        <Card>
          <div className="label mb-3 text-deck-300">Test Cases</div>
          <div className="space-y-2">
            {suite.test_cases.map((tc, i) => (
              <div key={tc.id ?? i} className="rounded-sm border border-deck-700 p-2.5">
                <p className="text-xs text-deck-100">{tc.input}</p>
                {tc.expected_output && (
                  <p className="mt-1 text-xs text-deck-500">
                    expects: {tc.expected_output}
                  </p>
                )}
                {tc.expected_tool_calls && tc.expected_tool_calls.length > 0 && (
                  <p className="mt-1 font-mono text-[11px] text-cyan">
                    {tc.expected_tool_calls.join(", ")}
                  </p>
                )}
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}
