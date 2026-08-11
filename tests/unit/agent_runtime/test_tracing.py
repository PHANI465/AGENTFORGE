"""Unit tests for the OTel tracing module."""

import sys
from pathlib import Path

AGENT_RUNTIME_DIR = Path(__file__).resolve().parents[3] / "services" / "agent-runtime"
if str(AGENT_RUNTIME_DIR) not in sys.path:
    sys.path.append(str(AGENT_RUNTIME_DIR))

from tracing import (  # noqa: E402
    InMemorySpanExporter,
    current_trace_id,
    get_collected_spans,
    tracer,
)


class TestInMemorySpanExporter:
    def test_export_and_get(self):
        exporter = InMemorySpanExporter()
        assert exporter.get_spans() == []

    def test_clear(self):
        exporter = InMemorySpanExporter()
        exporter.clear()
        assert exporter.get_spans() == []

    def test_force_flush(self):
        exporter = InMemorySpanExporter()
        assert exporter.force_flush() is True


class TestTracerIntegration:
    def test_tracer_creates_spans(self):
        get_collected_spans()

        with tracer.start_as_current_span("test.operation") as span:
            span.set_attribute("test.key", "value")

        spans = get_collected_spans()
        assert len(spans) == 1
        assert spans[0].name == "test.operation"

    def test_nested_spans(self):
        get_collected_spans()

        with tracer.start_as_current_span("parent"):
            with tracer.start_as_current_span("child"):
                pass

        spans = get_collected_spans()
        assert len(spans) == 2
        names = {s.name for s in spans}
        assert "parent" in names
        assert "child" in names

    def test_current_trace_id_returns_hex(self):
        with tracer.start_as_current_span("trace_id_test"):
            tid = current_trace_id()
            assert tid is not None
            assert len(tid) == 32
            int(tid, 16)

    def test_get_collected_spans_clears_buffer(self):
        get_collected_spans()

        with tracer.start_as_current_span("one"):
            pass

        first = get_collected_spans()
        assert len(first) == 1

        second = get_collected_spans()
        assert len(second) == 0

    def test_span_attributes_preserved(self):
        get_collected_spans()

        with tracer.start_as_current_span("attr_test") as span:
            span.set_attribute("llm.model", "gpt-4o-mini")
            span.set_attribute("llm.tokens_in", 42)

        spans = get_collected_spans()
        attrs = dict(spans[0].attributes)
        assert attrs["llm.model"] == "gpt-4o-mini"
        assert attrs["llm.tokens_in"] == 42
