import { useParams } from "react-router-dom"
import { runsApi } from "../api/client"
import { useApi } from "../lib/useApi"
import { Card, ErrorState, LoadingState, PageHeader, StatusPill } from "../components/ui"
import { formatMs } from "../lib/format"
import type { TraceSpan } from "../api/types"

const TYPE_META: Record<
  string,
  { glyph: string; color: string; label: string }
> = {
  llm_call: { glyph: "◆", color: "text-cyan border-cyan/40", label: "LLM Call" },
  tool_call: { glyph: "▶", color: "text-signal border-signal/40", label: "Tool Call" },
  safety_check: { glyph: "◇", color: "text-lime border-lime/40", label: "Safety Check" },
}

function SpanCard({ span }: { span: TraceSpan }) {
  const meta = TYPE_META[span.type] ?? { glyph: "•", color: "text-deck-300 border-deck-600", label: span.type }
  const cacheHit = span.output?.cache_hit === true

  return (
    <div className="relative flex gap-4 rise-in">
      <div className="flex flex-col items-center">
        <div
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full border bg-deck-900 text-sm ${meta.color}`}
        >
          {meta.glyph}
        </div>
        <div className="mt-1 w-px flex-1 bg-deck-700" />
      </div>

      <Card className="mb-4 flex-1">
        <div className="mb-2 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="label text-deck-500">#{span.step_number}</span>
            <span className={`label ${meta.color.split(" ")[0]}`}>{meta.label}</span>
            {cacheHit && (
              <span className="label rounded-sm border border-lime/40 bg-lime/10 px-1.5 py-0.5 !text-[9px] text-lime">
                cache hit
              </span>
            )}
          </div>
          <span className="label text-deck-500">{formatMs(span.latency_ms)}</span>
        </div>

        {span.type === "llm_call" && (
          <div className="space-y-1">
            {typeof span.output.content === "string" && span.output.content && (
              <p className="whitespace-pre-wrap text-sm text-deck-100">{span.output.content}</p>
            )}
            <div className="flex gap-4 pt-1">
              {span.tokens_in != null && (
                <span className="label text-deck-500">in {span.tokens_in}tok</span>
              )}
              {span.tokens_out != null && (
                <span className="label text-deck-500">out {span.tokens_out}tok</span>
              )}
            </div>
          </div>
        )}

        {span.type === "tool_call" && (
          <div className="space-y-2">
            <div>
              <span className="label text-deck-500">arguments</span>
              <pre className="hud-scan mt-1 overflow-x-auto rounded-sm bg-deck-900 p-2 text-xs text-deck-300">
                {JSON.stringify(span.input.arguments ?? {}, null, 2)}
              </pre>
            </div>
            <div>
              <span className="label text-deck-500">result</span>
              <p className="mt-1 text-sm text-deck-100">{String(span.output.result ?? "")}</p>
            </div>
          </div>
        )}

        {span.type === "safety_check" && (
          <div>
            <div className="mb-1 flex items-center gap-2">
              <span
                className={`label ${span.output.passed ? "text-lime" : "text-danger"}`}
              >
                {span.output.passed ? "passed" : "violation detected"}
              </span>
              {typeof span.output.action === "string" && (
                <span className="label text-deck-500">action: {span.output.action}</span>
              )}
            </div>
            {Array.isArray(span.output.violations) && span.output.violations.length > 0 && (
              <ul className="space-y-1">
                {(span.output.violations as Record<string, unknown>[]).map((v, i) => (
                  <li key={i} className="text-xs text-deck-300">
                    <span className="text-danger">{String(v.pattern_name)}</span>{" "}
                    matched "{String(v.matched_text)}"
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </Card>
    </div>
  )
}

export function TraceViewer() {
  const { runId } = useParams<{ runId: string }>()
  const { data, loading, error } = useApi(() => runsApi.trace(runId!), [runId])

  if (loading) return <LoadingState />
  if (error) return <ErrorState message={error} />
  if (!data) return null

  const trace = data.data

  return (
    <div>
      <PageHeader
        eyebrow={`run ${trace.run_id.slice(0, 8)}`}
        title="Execution Trace"
        action={<StatusPill status={trace.status} />}
      />

      <Card className="mb-6">
        <div className="mb-3">
          <span className="label text-deck-500">input</span>
          <p className="mt-1 text-sm text-deck-100">{trace.input}</p>
        </div>
        {trace.output && (
          <div className="mb-4">
            <span className="label text-deck-500">output</span>
            <p className="mt-1 whitespace-pre-wrap text-sm text-deck-100">{trace.output}</p>
          </div>
        )}
        <div className="grid grid-cols-3 gap-4 border-t border-deck-700 pt-4 sm:grid-cols-6">
          <Stat label="steps" value={trace.summary.total_steps} />
          <Stat label="llm calls" value={trace.summary.total_llm_calls} />
          <Stat label="tool calls" value={trace.summary.total_tool_calls} />
          <Stat label="safety checks" value={trace.summary.total_safety_checks} />
          <Stat label="tokens" value={trace.summary.total_tokens_in + trace.summary.total_tokens_out} />
          <Stat label="latency" value={formatMs(trace.summary.total_latency_ms)} />
        </div>
      </Card>

      <div>
        {trace.spans.map((span) => (
          <SpanCard key={span.step_number} span={span} />
        ))}
      </div>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <div className="font-display text-lg text-deck-50">{value}</div>
      <div className="label text-deck-500">{label}</div>
    </div>
  )
}
