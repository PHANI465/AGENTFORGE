"""LiteLLM wrapper — async LLM calls with token and cost tracking."""

import time
from dataclasses import dataclass, field
from typing import Any

import litellm


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


async def call_llm(
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    api_key: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.7,
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
    )
