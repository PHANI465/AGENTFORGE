"""Prometheus metrics for the agent-runtime service.

Custom counters and histograms for LLM calls, token usage, costs, and safety violations.
"""

from prometheus_client import Counter, Histogram

LLM_CALLS_TOTAL = Counter(
    "agentforge_llm_calls_total",
    "Total number of LLM API calls",
    ["model"],
)

TOKENS_IN_TOTAL = Counter(
    "agentforge_tokens_in_total",
    "Total input tokens consumed",
    ["model"],
)

TOKENS_OUT_TOTAL = Counter(
    "agentforge_tokens_out_total",
    "Total output tokens generated",
    ["model"],
)

COST_USD_TOTAL = Counter(
    "agentforge_cost_usd_total",
    "Total LLM cost in USD",
    ["model"],
)

TOOL_CALLS_TOTAL = Counter(
    "agentforge_tool_calls_total",
    "Total tool executions",
    ["tool_name"],
)

SAFETY_VIOLATIONS_TOTAL = Counter(
    "agentforge_safety_violations_total",
    "Total safety policy violations detected",
    ["check_point", "action"],
)

AGENT_RUN_DURATION = Histogram(
    "agentforge_agent_run_duration_seconds",
    "Duration of agent execution runs",
    buckets=[0.5, 1, 2, 5, 10, 30, 60, 120],
)

LLM_CALL_DURATION = Histogram(
    "agentforge_llm_call_duration_seconds",
    "Duration of individual LLM API calls",
    ["model"],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30],
)
