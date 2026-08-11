"""OpenTelemetry tracing setup for the agent-runtime execution engine.

Creates spans for each step (LLM call, tool call, safety check) in the
execution loop.  A custom in-memory exporter collects completed spans so
the trace_id and span summaries can be returned in the RunResult.
"""

from __future__ import annotations

import threading
from collections.abc import Sequence

from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult

SERVICE_NAME = "agent-runtime"
_TRACER_NAME = "agentforge.agent-runtime"


class InMemorySpanExporter(SpanExporter):
    """Collects finished spans in a thread-safe list so they can be read after execution."""

    def __init__(self) -> None:
        self._spans: list[ReadableSpan] = []
        self._lock = threading.Lock()

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        with self._lock:
            self._spans.extend(spans)
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        self.clear()

    def force_flush(self, timeout_millis: int = 30000) -> bool:  # noqa: ARG002
        return True

    def get_spans(self) -> list[ReadableSpan]:
        with self._lock:
            return list(self._spans)

    def clear(self) -> None:
        with self._lock:
            self._spans.clear()


_exporter = InMemorySpanExporter()
_provider = TracerProvider()
_provider.add_span_processor(SimpleSpanProcessor(_exporter))
trace.set_tracer_provider(_provider)

tracer = trace.get_tracer(_TRACER_NAME)


def get_collected_spans() -> list[ReadableSpan]:
    """Return spans collected since the last clear, then clear the buffer."""
    spans = _exporter.get_spans()
    _exporter.clear()
    return spans


def current_trace_id() -> str | None:
    """Return the hex trace_id of the currently active span, or None."""
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx and ctx.trace_id:
        return format(ctx.trace_id, "032x")
    return None
