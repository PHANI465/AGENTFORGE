"""Tool registry and built-in sample tools for the agent runtime."""

import ast
import operator
import os
from datetime import UTC, datetime
from typing import Any

import httpx
from agentforge_common.models import ToolSpec

API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://api-gateway:8000")

_SAFE_OPS: dict[type, Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


def _safe_eval(expr: str) -> float:
    """Evaluate a simple arithmetic expression via AST — no eval/exec."""
    tree = ast.parse(expr, mode="eval")

    def _walk(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return _walk(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in _SAFE_OPS:
                raise ValueError(f"Unsupported operator: {op_type.__name__}")
            return _SAFE_OPS[op_type](_walk(node.left), _walk(node.right))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -_walk(node.operand)
        raise ValueError(f"Unsupported expression node: {ast.dump(node)}")

    return _walk(tree)


async def tool_get_current_time(**_kwargs: Any) -> str:
    """Returns the current UTC date and time."""
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


async def tool_calculate(expression: str) -> str:
    """Evaluates a mathematical expression safely."""
    try:
        return str(_safe_eval(expression))
    except Exception as e:
        return f"Error: {e}"


async def tool_call_agent(agent_id: str, input: str, api_key: str = "") -> str:
    """Delegates a sub-task to another agent and returns its output."""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120)) as client:
            resp = await client.post(
                f"{API_GATEWAY_URL}/api/v1/agents/{agent_id}/run",
                json={"input": input},
                headers={"X-API-Key": api_key} if api_key else {},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", {}).get("output", "No output from sub-agent")
    except httpx.HTTPStatusError as e:
        return f"Sub-agent call failed (HTTP {e.response.status_code}): {e.response.text[:200]}"
    except httpx.RequestError as e:
        return f"Sub-agent call failed: {e}"


BUILTIN_SPECS: dict[str, ToolSpec] = {
    "get_current_time": ToolSpec(
        name="get_current_time",
        description="Returns the current date and time in UTC.",
        parameters_schema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
    "calculate": ToolSpec(
        name="calculate",
        description="Evaluates a mathematical expression. Supports +, -, *, /, %, **.",
        parameters_schema={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The math expression to evaluate, e.g. '2 + 3 * 4'",
                },
            },
            "required": ["expression"],
        },
    ),
}

BUILTIN_SPECS["call_agent"] = ToolSpec(
    name="call_agent",
    description="Delegates a sub-task to another agent by ID. Use when the current task "
    "requires expertise from a specialist agent.",
    parameters_schema={
        "type": "object",
        "properties": {
            "agent_id": {
                "type": "string",
                "description": "UUID of the agent to call",
            },
            "input": {
                "type": "string",
                "description": "The input/question to send to the sub-agent",
            },
        },
        "required": ["agent_id", "input"],
    },
)

BUILTIN_CALLABLES: dict[str, Any] = {
    "get_current_time": tool_get_current_time,
    "calculate": tool_calculate,
    "call_agent": tool_call_agent,
}


class ToolRegistry:
    """Maps tool names to their OpenAI-format specs and async callables."""

    def __init__(self) -> None:
        self._callables: dict[str, Any] = dict(BUILTIN_CALLABLES)
        self._specs: dict[str, ToolSpec] = dict(BUILTIN_SPECS)

    def get_callable(self, name: str) -> Any | None:
        return self._callables.get(name)

    def has_tool(self, name: str) -> bool:
        return name in self._callables

    def to_openai_tools(self, tool_names: list[str]) -> list[dict[str, Any]]:
        """Convert named tool specs into the OpenAI function-calling format."""
        result: list[dict[str, Any]] = []
        for name in tool_names:
            spec = self._specs.get(name)
            if spec:
                result.append({
                    "type": "function",
                    "function": {
                        "name": spec.name,
                        "description": spec.description,
                        "parameters": spec.parameters_schema,
                    },
                })
        return result
