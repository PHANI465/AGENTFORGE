import { useMemo, useState } from "react"
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { agentsApi, analyticsApi } from "../api/client"
import { useApi } from "../lib/useApi"
import { Card, ErrorState, LoadingState, PageHeader } from "../components/ui"
import { formatUsd } from "../lib/format"

const WINDOWS = [7, 14, 30, 90]

function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: { name: string; value: number; color: string }[]
  label?: string
}) {
  if (!active || !payload?.length) return null
  return (
    <div className="hud-card rounded-sm px-3 py-2 text-xs">
      <div className="label mb-1 text-deck-400">{label}</div>
      {payload.map((p) => (
        <div key={p.name} style={{ color: p.color }}>
          {p.name}: {formatUsd(p.value)}
        </div>
      ))}
    </div>
  )
}

export function Analytics() {
  const [days, setDays] = useState(7)
  const { data: usage, loading: usageLoading, error: usageError } = useApi(
    () => analyticsApi.usage(days),
    [days],
  )
  const { data: costs, loading: costsLoading } = useApi(() => analyticsApi.costs(days), [days])
  const { data: agents } = useApi(() => agentsApi.list(), [])

  const agentName = useMemo(() => {
    const map = new Map<string, string>()
    agents?.data.forEach((a) => map.set(a.id, a.name))
    return (id: string) => map.get(id) ?? id.slice(0, 8)
  }, [agents])

  const dailyTotals = useMemo(() => {
    if (!costs) return []
    const byDate = new Map<string, number>()
    costs.data.forEach((row) => {
      byDate.set(row.date, (byDate.get(row.date) ?? 0) + row.total_cost_usd)
    })
    return Array.from(byDate.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, cost]) => ({ date: date.slice(5), cost }))
  }, [costs])

  const perAgent = useMemo(() => {
    if (!costs) return []
    const byAgent = new Map<string, number>()
    costs.data.forEach((row) => {
      byAgent.set(row.agent_id, (byAgent.get(row.agent_id) ?? 0) + row.total_cost_usd)
    })
    return Array.from(byAgent.entries())
      .sort(([, a], [, b]) => b - a)
      .map(([agentId, cost]) => ({ name: agentName(agentId), cost }))
  }, [costs, agentName])

  return (
    <div>
      <PageHeader
        eyebrow="Ledger"
        title="Cost Analytics"
        action={
          <div className="flex gap-1.5">
            {WINDOWS.map((w) => (
              <button
                key={w}
                onClick={() => setDays(w)}
                className={`label rounded-sm border px-2.5 py-1 !text-[10px] transition-colors ${
                  days === w
                    ? "border-signal/50 bg-signal/10 text-signal"
                    : "border-deck-600 text-deck-400 hover:border-deck-500"
                }`}
              >
                {w}d
              </button>
            ))}
          </div>
        }
      />

      {usageError && <ErrorState message={usageError} />}
      {usageLoading && <LoadingState />}

      {usage && (
        <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Card>
            <div className="font-display text-2xl text-deck-50">
              {formatUsd(usage.data.total_cost_usd)}
            </div>
            <div className="label mt-1 text-deck-500">total spend</div>
          </Card>
          <Card>
            <div className="font-display text-2xl text-deck-50">{usage.data.total_calls}</div>
            <div className="label mt-1 text-deck-500">total calls</div>
          </Card>
          <Card>
            <div className="font-display text-2xl text-deck-50">
              {usage.data.total_tokens_in + usage.data.total_tokens_out}
            </div>
            <div className="label mt-1 text-deck-500">total tokens</div>
          </Card>
          <Card>
            <div className="font-display text-2xl text-deck-50">
              {formatUsd(usage.data.avg_cost_per_call_usd)}
            </div>
            <div className="label mt-1 text-deck-500">avg / call</div>
          </Card>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <div className="label mb-4 text-deck-300">Daily Spend</div>
          {costsLoading ? (
            <LoadingState />
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={dailyTotals}>
                <defs>
                  <linearGradient id="costGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#ff8a3d" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#ff8a3d" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#20252f" vertical={false} />
                <XAxis
                  dataKey="date"
                  tick={{ fill: "#6b7280", fontSize: 10 }}
                  axisLine={{ stroke: "#20252f" }}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: "#6b7280", fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                  width={40}
                />
                <Tooltip content={<ChartTooltip />} />
                <Area
                  type="monotone"
                  dataKey="cost"
                  name="cost"
                  stroke="#ff8a3d"
                  strokeWidth={2}
                  fill="url(#costGradient)"
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </Card>

        <Card>
          <div className="label mb-4 text-deck-300">Cost by Agent</div>
          {costsLoading ? (
            <LoadingState />
          ) : perAgent.length === 0 ? (
            <div className="flex h-[220px] items-center justify-center">
              <span className="label text-deck-500">no spend in this window</span>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={perAgent} layout="vertical">
                <CartesianGrid stroke="#20252f" horizontal={false} />
                <XAxis
                  type="number"
                  tick={{ fill: "#6b7280", fontSize: 10 }}
                  axisLine={{ stroke: "#20252f" }}
                  tickLine={false}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  tick={{ fill: "#c7cbd4", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  width={110}
                />
                <Tooltip content={<ChartTooltip />} />
                <Bar dataKey="cost" name="cost" fill="#5eead4" radius={[0, 3, 3, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>
      </div>
    </div>
  )
}
