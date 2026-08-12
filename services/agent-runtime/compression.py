"""Prompt compression — shrink long tool-result content before it re-enters the conversation.

Opt-in per agent via TokenOptimizationConfig.enable_compression. Uses LLMLingua
if it's installed (`pip install llmlingua`, a heavy optional extra — pulls in
torch — so it's not a hard dependency of this service); otherwise falls back to
a lightweight, dependency-free strategy: collapse redundant whitespace, and if
still over threshold, keep the head and tail of the content (where the
task-relevant instructions and most recent result usually live) and drop the
middle.
"""

from typing import Any

try:
    from llmlingua import PromptCompressor as _LLMLinguaCompressor

    _llmlingua_instance = _LLMLinguaCompressor()
except Exception:
    _llmlingua_instance = None

_HEAD_RATIO = 0.6
_TAIL_RATIO = 0.2


def _collapse_whitespace(text: str) -> str:
    return " ".join(text.split())


def _fallback_compress(text: str, threshold_chars: int) -> str:
    collapsed = _collapse_whitespace(text)
    if len(collapsed) <= threshold_chars:
        return collapsed

    head_len = int(threshold_chars * _HEAD_RATIO)
    tail_len = int(threshold_chars * _TAIL_RATIO)
    dropped = len(collapsed) - head_len - tail_len
    head = collapsed[:head_len].rstrip()
    tail = collapsed[-tail_len:].lstrip()
    return f"{head} ...[{dropped} chars truncated]... {tail}"


def compress_content(text: str, threshold_chars: int) -> tuple[str, dict[str, Any]]:
    """Compress text if it exceeds threshold_chars. Returns (text, stats).

    stats.strategy is one of "none" (already under threshold), "llmlingua",
    or "fallback_truncate".
    """
    original_len = len(text)
    if original_len <= threshold_chars:
        return text, {
            "strategy": "none",
            "original_chars": original_len,
            "compressed_chars": original_len,
        }

    if _llmlingua_instance is not None:
        try:
            result = _llmlingua_instance.compress_prompt(text, target_token=threshold_chars // 4)
            compressed = result.get("compressed_prompt", text)
            return compressed, {
                "strategy": "llmlingua",
                "original_chars": original_len,
                "compressed_chars": len(compressed),
            }
        except Exception:
            pass

    compressed = _fallback_compress(text, threshold_chars)
    return compressed, {
        "strategy": "fallback_truncate",
        "original_chars": original_len,
        "compressed_chars": len(compressed),
    }
