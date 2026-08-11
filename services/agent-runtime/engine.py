"""Core agent execution loop: think -> act -> observe."""

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any

from llm import call_llm
from tools import ToolRegistry


@dataclass
class StepRecord:
    """One step in the execution trace (an LLM call or a tool call)."""

    step_number: int
    type: str
    input: dict[str, Any]
    output: dict[str, Any]
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0


@dataclass
class RunResult:
    """Complete result of an agent execution."""

    output: str
    steps: list[StepRecord] = field(default_factory=list)
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_cost_usd: float = 0.0
    model: str = ""
    error: str | None = None


async def execute_agent(
    system_prompt: str,
    user_input: str,
    model: str,
    tool_names: list[str],
    api_key: str,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    timeout: int = 120,
    max_iterations: int = 10,
) -> RunResult:
    """Run the think->act->observe loop until the LLM stops calling tools."""
    registry = ToolRegistry()
    tools_for_llm = registry.to_openai_tools(tool_names) if tool_names else None

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]

    try:
        return await asyncio.wait_for(
            _loop(messages, model, tools_for_llm, registry, api_key,
                  max_tokens, temperature, max_iterations),
            timeout=timeout,
        )
    except TimeoutError:
        return RunResult(
            output="", model=model,
            error=f"Execution timed out after {timeout}s",
        )
    except Exception as e:
        return RunResult(output="", model=model, error=str(e))


async def _loop(
    messages: list[dict[str, Any]],
    model: str,
    tools_for_llm: list[dict[str, Any]] | None,
    registry: ToolRegistry,
    api_key: str,
    max_tokens: int,
    temperature: float,
    max_iterations: int,
) -> RunResult:
    steps: list[StepRecord] = []
    total_in = 0
    total_out = 0
    total_cost = 0.0
    actual_model = model
    step_num = 0

    for _ in range(max_iterations):
        # --- THINK: call the LLM ---
        step_num += 1
        llm_resp = await call_llm(
            model=model, messages=messages, tools=tools_for_llm,
            api_key=api_key, max_tokens=max_tokens, temperature=temperature,
        )
        actual_model = llm_resp.model
        total_in += llm_resp.tokens_in
        total_out += llm_resp.tokens_out
        total_cost += llm_resp.cost_usd

        steps.append(StepRecord(
            step_number=step_num, type="llm_call",
            input={"messages_count": len(messages)},
            output={"content": llm_resp.content,
                    "tool_calls_count": len(llm_resp.tool_calls)},
            tokens_in=llm_resp.tokens_in, tokens_out=llm_resp.tokens_out,
            latency_ms=llm_resp.latency_ms,
        ))

        if not llm_resp.tool_calls:
            return RunResult(
                output=llm_resp.content or "", steps=steps,
                total_tokens_in=total_in, total_tokens_out=total_out,
                total_cost_usd=total_cost, model=actual_model,
            )

        # Append the assistant message (with tool_calls) to the conversation
        assistant_msg: dict[str, Any] = {
            "role": "assistant",
            "content": llm_resp.content,
            "tool_calls": [
                {"id": tc["id"], "type": "function",
                 "function": {"name": tc["name"],
                              "arguments": tc["arguments"]}}
                for tc in llm_resp.tool_calls
            ],
        }
        messages.append(assistant_msg)

        # --- ACT + OBSERVE: execute each tool, feed result back ---
        for tc in llm_resp.tool_calls:
            step_num += 1
            tool_name = tc["name"]

            try:
                args = json.loads(tc["arguments"]) if tc["arguments"] else {}
            except json.JSONDecodeError:
                args = {}

            callable_fn = registry.get_callable(tool_name)
            tool_latency = 0

            if callable_fn is None:
                tool_result = f"Error: unknown tool '{tool_name}'"
            else:
                start = time.monotonic()
                try:
                    tool_result = await callable_fn(**args)
                except Exception as e:
                    tool_result = f"Error executing tool: {e}"
                tool_latency = int((time.monotonic() - start) * 1000)

            steps.append(StepRecord(
                step_number=step_num, type="tool_call",
                input={"tool_name": tool_name, "arguments": args},
                output={"result": tool_result},
                latency_ms=tool_latency,
            ))

            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": str(tool_result),
            })

    return RunResult(
        output=f"Max iterations ({max_iterations}) reached", steps=steps,
        total_tokens_in=total_in, total_tokens_out=total_out,
        total_cost_usd=total_cost, model=actual_model,
    )
