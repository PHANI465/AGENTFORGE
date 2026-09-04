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


async def tool_text_stats(text: str) -> str:
    """Counts words, characters, sentences and lines in a piece of text."""
    words = len(text.split())
    chars = len(text)
    sentences = sum(text.count(c) for c in ".!?") or (1 if text.strip() else 0)
    lines = text.count("\n") + 1 if text else 0
    return f"words={words}, characters={chars}, sentences={sentences}, lines={lines}"


async def tool_random_number(min: int = 0, max: int = 100) -> str:
    """Returns a random integer between min and max (inclusive)."""
    import random

    lo, hi = (min, max) if min <= max else (max, min)
    return str(random.randint(lo, hi))


async def tool_count_occurrences(text: str, substring: str) -> str:
    """Counts how many times substring appears in text (case-insensitive)."""
    if not substring:
        return "Error: substring is empty"
    return str(text.lower().count(substring.lower()))


# Conversion factors to a canonical base unit per dimension.
_UNIT_DIMS: dict[str, tuple[str, float]] = {
    # length → metres
    "m": ("length", 1.0), "km": ("length", 1000.0), "cm": ("length", 0.01),
    "mm": ("length", 0.001), "mi": ("length", 1609.344), "ft": ("length", 0.3048),
    "in": ("length", 0.0254), "yd": ("length", 0.9144),
    # mass → grams
    "g": ("mass", 1.0), "kg": ("mass", 1000.0), "mg": ("mass", 0.001),
    "lb": ("mass", 453.59237), "oz": ("mass", 28.349523125),
}


async def tool_unit_convert(value: float, from_unit: str, to_unit: str) -> str:
    """Converts a value between units of length, mass, or temperature."""
    f, t = from_unit.lower().strip(), to_unit.lower().strip()

    # Temperature is affine, not a simple ratio — handle separately.
    temps = {"c", "f", "k", "celsius", "fahrenheit", "kelvin"}
    norm = {"celsius": "c", "fahrenheit": "f", "kelvin": "k"}
    if f in temps and t in temps:
        f, t = norm.get(f, f), norm.get(t, t)
        celsius = value if f == "c" else (value - 32) * 5 / 9 if f == "f" else value - 273.15
        out = celsius if t == "c" else celsius * 9 / 5 + 32 if t == "f" else celsius + 273.15
        return f"{round(out, 4)} {t}"

    if f not in _UNIT_DIMS or t not in _UNIT_DIMS:
        return f"Error: unsupported unit(s). Known: {', '.join(sorted(_UNIT_DIMS))}, c, f, k"
    if _UNIT_DIMS[f][0] != _UNIT_DIMS[t][0]:
        return (
            f"Error: cannot convert {from_unit} ({_UNIT_DIMS[f][0]}) "
            f"to {to_unit} ({_UNIT_DIMS[t][0]})"
        )
    result = value * _UNIT_DIMS[f][1] / _UNIT_DIMS[t][1]
    return f"{round(result, 6)} {t}"


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
    "text_stats": ToolSpec(
        name="text_stats",
        description="Counts words, characters, sentences and lines in a piece of text.",
        parameters_schema={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The text to analyse."},
            },
            "required": ["text"],
        },
    ),
    "random_number": ToolSpec(
        name="random_number",
        description="Returns a random integer between min and max (inclusive).",
        parameters_schema={
            "type": "object",
            "properties": {
                "min": {"type": "integer", "description": "Lower bound (default 0)."},
                "max": {"type": "integer", "description": "Upper bound (default 100)."},
            },
            "required": [],
        },
    ),
    "count_occurrences": ToolSpec(
        name="count_occurrences",
        description="Counts how many times a substring appears in a text (case-insensitive).",
        parameters_schema={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The text to search in."},
                "substring": {"type": "string", "description": "The substring to count."},
            },
            "required": ["text", "substring"],
        },
    ),
    "unit_convert": ToolSpec(
        name="unit_convert",
        description="Converts a value between units of length (m, km, cm, mm, mi, ft, in, yd), "
        "mass (g, kg, mg, lb, oz), or temperature (c, f, k).",
        parameters_schema={
            "type": "object",
            "properties": {
                "value": {"type": "number", "description": "The numeric value to convert."},
                "from_unit": {"type": "string", "description": "Unit to convert from, e.g. 'km'."},
                "to_unit": {"type": "string", "description": "Unit to convert to, e.g. 'mi'."},
            },
            "required": ["value", "from_unit", "to_unit"],
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
    "text_stats": tool_text_stats,
    "random_number": tool_random_number,
    "count_occurrences": tool_count_occurrences,
    "unit_convert": tool_unit_convert,
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
