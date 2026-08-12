"""Unit tests for prompt compression (fallback strategy — llmlingua isn't installed
in the test environment, so these exercise the dependency-free path)."""

import sys
from pathlib import Path

AGENT_RUNTIME_DIR = Path(__file__).resolve().parents[3] / "services" / "agent-runtime"
if str(AGENT_RUNTIME_DIR) not in sys.path:
    sys.path.append(str(AGENT_RUNTIME_DIR))

from compression import compress_content  # noqa: E402


class TestCompressContent:
    def test_short_content_untouched(self):
        text = "short result"
        compressed, stats = compress_content(text, threshold_chars=100)
        assert compressed == text
        assert stats["strategy"] == "none"
        assert stats["original_chars"] == stats["compressed_chars"]

    def test_content_exactly_at_threshold_untouched(self):
        text = "x" * 100
        compressed, stats = compress_content(text, threshold_chars=100)
        assert compressed == text
        assert stats["strategy"] == "none"

    def test_long_content_gets_compressed(self):
        text = "x" * 5000
        compressed, stats = compress_content(text, threshold_chars=100)
        assert len(compressed) < len(text)
        assert stats["strategy"] == "fallback_truncate"
        assert stats["original_chars"] == 5000
        assert stats["compressed_chars"] == len(compressed)

    def test_compressed_content_preserves_head_and_tail(self):
        text = "START" + ("x" * 5000) + "END"
        compressed, _ = compress_content(text, threshold_chars=200)
        assert compressed.startswith("START")
        assert compressed.endswith("END")
        assert "truncated" in compressed

    def test_whitespace_is_collapsed_when_compression_kicks_in(self):
        text = "hello    world\n\n\n" + ("foo   bar " * 200)
        compressed, stats = compress_content(text, threshold_chars=100)
        assert "  " not in compressed
        assert stats["strategy"] == "fallback_truncate"

    def test_empty_content(self):
        compressed, stats = compress_content("", threshold_chars=100)
        assert compressed == ""
        assert stats["strategy"] == "none"
