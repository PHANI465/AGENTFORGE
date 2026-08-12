"""LiteLLM wrapper — async LLM calls with token/cost tracking and Redis-backed caching.

If REDIS_URL is set (docker-compose sets it for every service), exact-match
response caching is enabled globally: identical (model, messages, params) calls
are served from Redis instead of hitting the LLM provider again. Caching can
still be disabled per-call via `enable_caching=False` (e.g. an agent that opts
out via its TokenOptimizationConfig).
"""

import os
import time
from dataclasses import dataclass, field
from typing import Any

import litellm

_redis_url = os.getenv("REDIS_URL", "")
_CACHE_TTL_SECONDS = 3600  # LiteLLM's own default is much shorter (~60s) — too
                            # short to catch a user re-asking the same thing a
                            # few minutes later, so we set an explicit 1-hour TTL.
if _redis_url:
    try:
        litellm.cache = litellm.Cache(type="redis", url=_redis_url, ttl=_CACHE_TTL_SECONDS)
    except Exception:
        litellm.cache = None
else:
    litellm.cache = None


@dataclass
class LLMResponse:
    """Structured result from a single LLM call."""

    content: str | None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    model: str = ""
    latency_ms: int = 0
    cost_usd: float = 0.0
    cache_hit: bool = False


async def call_llm(
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    api_key: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    enable_caching: bool = True,
) -> LLMResponse:
    """Call an LLM via LiteLLM and return a structured response with usage."""
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if tools:
        kwargs["tools"] = tools
    if api_key:
        kwargs["api_key"] = api_key
    if enable_caching and litellm.cache is not None:
        kwargs["caching"] = True

    start = time.monotonic()
    response = await litellm.acompletion(**kwargs)
    latency_ms = int((time.monotonic() - start) * 1000)

    choice = response.choices[0]
    message = choice.message

    tool_calls: list[dict[str, Any]] = []
    if message.tool_calls:
        for tc in message.tool_calls:
            tool_calls.append({
                "id": tc.id,
                "name": tc.function.name,
                "arguments": tc.function.arguments,
            })

    usage = response.usage
    tokens_in = usage.prompt_tokens if usage else 0
    tokens_out = usage.completion_tokens if usage else 0

    hidden_params = getattr(response, "_hidden_params", {}) or {}
    cache_hit = bool(hidden_params.get("cache_hit", False))

    if cache_hit:
        # Served from Redis — no provider API call happened, so no real spend.
        # Token counts are kept for observability; cost is what's zeroed.
        cost = 0.0
    else:
        try:
            cost = litellm.completion_cost(completion_response=response)
        except Exception:
            cost = 0.0

    return LLMResponse(
        content=message.content,
        tool_calls=tool_calls,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        model=response.model or model,
        latency_ms=latency_ms,
        cost_usd=float(cost),
        cache_hit=cache_hit,
    )
