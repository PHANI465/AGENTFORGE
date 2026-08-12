"""Core agent execution loop: think -> act -> observe, with safety enforcement,
OTel tracing, and token-optimization (smart routing, caching, compression)."""

import asyncio
import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from agentforge_common.models import TokenOptimizationConfig
from compression import compress_content
from llm import call_llm
from metrics import (
    AGENT_RUN_DURATION,
    COMPRESSION_SAVED_CHARS_TOTAL,
    COST_USD_TOTAL,
    LLM_CACHE_HITS_TOTAL,
    LLM_CACHE_MISSES_TOTAL,
    LLM_CALL_DURATION,
    LLM_CALLS_TOTAL,
    MODEL_ROUTING_TOTAL,
    SAFETY_VIOLATIONS_TOTAL,
    TOKENS_IN_TOTAL,
    TOKENS_OUT_TOTAL,
    TOOL_CALLS_TOTAL,
)
from opentelemetry import trace
from routing import pick_model
from safety import CheckPoint, SafetyChecker
from tools import ToolRegistry
from tracing import current_trace_id, tracer

BLOCKED_OUTPUT = "[BLOCKED] Response violated safety policy and was not delivered."


@dataclass
class StepRecord:
    """One step in the execution trace (an LLM call, tool call, or safety check)."""

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
    trace_id: str | None = None


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
    safety_rules: list[str] | None = None,
    on_violation: str = "log",
    optimization: TokenOptimizationConfig | None = None,
) -> RunResult:
    """Run the think->act->observe loop with safety enforcement, tracing, and
    token-optimization (smart routing, response caching, prompt compression)."""
    optimization = optimization or TokenOptimizationConfig()
    registry = ToolRegistry()
    tools_for_llm = registry.to_openai_tools(tool_names) if tool_names else None
    checker = SafetyChecker(safety_rules or [], on_violation)

    effective_model, routing_tier = pick_model(
        user_input=user_input,
        configured_model=model,
        enable_smart_routing=optimization.enable_smart_routing,
        simple_model=optimization.simple_model,
        complex_model=optimization.complex_model,
        complexity_threshold=optimization.complexity_threshold,
        has_tools=bool(tool_names),
    )
    MODEL_ROUTING_TOTAL.labels(tier=routing_tier).inc()

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]

    with tracer.start_as_current_span(
        "agent.execute",
        attributes={
            "agent.model": effective_model,
            "agent.routing_tier": routing_tier,
            "agent.max_tokens": max_tokens,
            "agent.temperature": temperature,
            "agent.max_iterations": max_iterations,
            "agent.tool_count": len(tool_names),
            "agent.has_safety_rules": bool(safety_rules),
        },
    ) as root_span:
        trace_id = current_trace_id()
        start = time.monotonic()

        try:
            result = await asyncio.wait_for(
                _loop(messages, effective_model, tools_for_llm, registry, api_key,
                      max_tokens, temperature, max_iterations, checker, optimization),
                timeout=timeout,
            )
        except TimeoutError:
            root_span.set_status(trace.StatusCode.ERROR, f"Timeout after {timeout}s")
            return RunResult(
                output="", model=effective_model, trace_id=trace_id,
                error=f"Execution timed out after {timeout}s",
            )
        except Exception as e:
            root_span.set_status(trace.StatusCode.ERROR, str(e))
            return RunResult(output="", model=effective_model, trace_id=trace_id, error=str(e))
        finally:
            AGENT_RUN_DURATION.observe(time.monotonic() - start)

        result.trace_id = trace_id

        if result.error:
            root_span.set_status(trace.StatusCode.ERROR, result.error)
        else:
            root_span.set_status(trace.StatusCode.OK)

        root_span.set_attribute("agent.total_tokens_in", result.total_tokens_in)
        root_span.set_attribute("agent.total_tokens_out", result.total_tokens_out)
        root_span.set_attribute("agent.total_cost_usd", result.total_cost_usd)
        root_span.set_attribute("agent.steps_count", len(result.steps))

        return result


async def _loop(
    messages: list[dict[str, Any]],
    model: str,
    tools_for_llm: list[dict[str, Any]] | None,
    registry: ToolRegistry,
    api_key: str,
    max_tokens: int,
    temperature: float,
    max_iterations: int,
    checker: SafetyChecker,
    optimization: TokenOptimizationConfig,
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
        with tracer.start_as_current_span(
            "llm.call",
            attributes={"llm.model": model, "llm.step_number": step_num},
        ) as llm_span:
            llm_resp = await call_llm(
                model=model, messages=messages, tools=tools_for_llm,
                api_key=api_key, max_tokens=max_tokens, temperature=temperature,
                enable_caching=optimization.enable_caching,
            )
            actual_model = llm_resp.model
            total_in += llm_resp.tokens_in
            total_out += llm_resp.tokens_out
            total_cost += llm_resp.cost_usd

            LLM_CALLS_TOTAL.labels(model=actual_model).inc()
            TOKENS_IN_TOTAL.labels(model=actual_model).inc(llm_resp.tokens_in)
            TOKENS_OUT_TOTAL.labels(model=actual_model).inc(llm_resp.tokens_out)
            COST_USD_TOTAL.labels(model=actual_model).inc(llm_resp.cost_usd)
            LLM_CALL_DURATION.labels(model=actual_model).observe(llm_resp.latency_ms / 1000)
            if llm_resp.cache_hit:
                LLM_CACHE_HITS_TOTAL.labels(model=actual_model).inc()
            else:
                LLM_CACHE_MISSES_TOTAL.labels(model=actual_model).inc()

            llm_span.set_attribute("llm.tokens_in", llm_resp.tokens_in)
            llm_span.set_attribute("llm.tokens_out", llm_resp.tokens_out)
            llm_span.set_attribute("llm.cost_usd", llm_resp.cost_usd)
            llm_span.set_attribute("llm.latency_ms", llm_resp.latency_ms)
            llm_span.set_attribute("llm.tool_calls_count", len(llm_resp.tool_calls))
            llm_span.set_attribute("llm.cache_hit", llm_resp.cache_hit)

        steps.append(StepRecord(
            step_number=step_num, type="llm_call",
            input={"messages_count": len(messages)},
            output={"content": llm_resp.content,
                    "tool_calls_count": len(llm_resp.tool_calls),
                    "cache_hit": llm_resp.cache_hit},
            tokens_in=llm_resp.tokens_in, tokens_out=llm_resp.tokens_out,
            latency_ms=llm_resp.latency_ms,
        ))

        # --- POST-LLM SAFETY CHECK ---
        if checker.has_rules and llm_resp.content:
            with tracer.start_as_current_span(
                "safety.check",
                attributes={"safety.check_point": "post_llm", "safety.step_number": step_num + 1},
            ) as safety_span:
                check_result = checker.check(llm_resp.content, CheckPoint.POST_LLM)
                safety_span.set_attribute("safety.passed", check_result.passed)
                safety_span.set_attribute("safety.violation_count", len(check_result.violations))

            if not check_result.passed:
                step_num += 1
                violation_details = [asdict(v) for v in check_result.violations]
                for v in check_result.violations:
                    SAFETY_VIOLATIONS_TOTAL.labels(
                        check_point=v.check_point, action=checker.on_violation
                    ).inc()
                steps.append(StepRecord(
                    step_number=step_num, type="safety_check",
                    input={"check_point": "post_llm",
                            "content_length": len(llm_resp.content)},
                    output={"passed": False,
                            "violations": violation_details,
                            "action": checker.on_violation},
                ))

                if checker.should_block:
                    return RunResult(
                        output=BLOCKED_OUTPUT, steps=steps,
                        total_tokens_in=total_in, total_tokens_out=total_out,
                        total_cost_usd=total_cost, model=actual_model,
                        error="Safety policy violation: response blocked",
                    )

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

            # --- PRE-TOOL SAFETY CHECK ---
            args_text = json.dumps(args)
            if checker.has_rules:
                with tracer.start_as_current_span(
                    "safety.check",
                    attributes={"safety.check_point": "pre_tool", "safety.tool_name": tool_name},
                ) as safety_span:
                    tool_check = checker.check(args_text, CheckPoint.PRE_TOOL)
                    safety_span.set_attribute("safety.passed", tool_check.passed)
                    safety_span.set_attribute("safety.violation_count", len(tool_check.violations))

                if not tool_check.passed:
                    violation_details = [asdict(v) for v in tool_check.violations]
                    for v in tool_check.violations:
                        SAFETY_VIOLATIONS_TOTAL.labels(
                            check_point=v.check_point, action=checker.on_violation
                        ).inc()
                    steps.append(StepRecord(
                        step_number=step_num, type="safety_check",
                        input={"check_point": "pre_tool",
                                "tool_name": tool_name,
                                "arguments": args},
                        output={"passed": False,
                                "violations": violation_details,
                                "action": checker.on_violation},
                    ))

                    if checker.should_block:
                        tool_result = f"[BLOCKED] Tool call '{tool_name}' violated safety policy"
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": tool_result,
                        })
                        continue

            with tracer.start_as_current_span(
                "tool.execute",
                attributes={"tool.name": tool_name, "tool.step_number": step_num},
            ) as tool_span:
                callable_fn = registry.get_callable(tool_name)
                tool_latency = 0

                if callable_fn is None:
                    tool_result = f"Error: unknown tool '{tool_name}'"
                    tool_span.set_status(trace.StatusCode.ERROR, tool_result)
                else:
                    start = time.monotonic()
                    try:
                        tool_result = await callable_fn(**args)
                    except Exception as e:
                        tool_result = f"Error executing tool: {e}"
                        tool_span.set_status(trace.StatusCode.ERROR, str(e))
                    tool_latency = int((time.monotonic() - start) * 1000)

                tool_span.set_attribute("tool.latency_ms", tool_latency)
                TOOL_CALLS_TOTAL.labels(tool_name=tool_name).inc()

            steps.append(StepRecord(
                step_number=step_num, type="tool_call",
                input={"tool_name": tool_name, "arguments": args},
                output={"result": tool_result},
                latency_ms=tool_latency,
            ))

            tool_result_str = str(tool_result)
            if optimization.enable_compression:
                compressed, comp_stats = compress_content(
                    tool_result_str, optimization.compression_threshold_chars
                )
                if comp_stats["strategy"] != "none":
                    saved = comp_stats["original_chars"] - comp_stats["compressed_chars"]
                    if saved > 0:
                        COMPRESSION_SAVED_CHARS_TOTAL.inc(saved)
                tool_result_str = compressed

            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": tool_result_str,
            })

    return RunResult(
        output=f"Max iterations ({max_iterations}) reached", steps=steps,
        total_tokens_in=total_in, total_tokens_out=total_out,
        total_cost_usd=total_cost, model=actual_model,
    )
