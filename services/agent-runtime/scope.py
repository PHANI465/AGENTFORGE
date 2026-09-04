"""Topic/scope guard — a cheap classifier that decides whether a user's input
falls within an agent's declared scope, so an agent can be confined to a topic.

Runs once, before the main loop, only when an agent turns the guard on. In
`block` mode an off-scope request is refused outright (the agent never runs);
in `warn` mode it's flagged in the trace but still answered.
"""

from dataclasses import dataclass

from llm import call_llm


@dataclass
class ScopeResult:
    in_scope: bool
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0


def refusal_message(allowed_scope: str) -> str:
    scope = allowed_scope.strip().rstrip(".")
    return (
        f"I can only help with {scope}. That request is outside my scope, "
        "so I can't help with it — feel free to ask something within that topic."
    )


async def classify_in_scope(
    user_input: str,
    allowed_scope: str,
    model: str,
    api_key: str,
) -> ScopeResult:
    """Ask the model whether user_input is within allowed_scope. Fails OPEN
    (treats as in-scope) if the classifier errors, so a guard glitch never
    silently blocks a legitimate request."""
    system = (
        "You are a strict topic classifier for an AI assistant. "
        "The assistant is ONLY allowed to help with the following scope:\n"
        f"\"{allowed_scope}\"\n\n"
        "Decide whether the user's message falls within that scope. "
        "Reply with exactly one word: 'yes' if it is within scope, or 'no' if "
        "it is outside it. Do not explain."
    )
    try:
        resp = await call_llm(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_input},
            ],
            tools=None,
            api_key=api_key,
            max_tokens=3,
            temperature=0.0,
            enable_caching=False,
        )
    except Exception:
        return ScopeResult(in_scope=True)

    answer = (resp.content or "").strip().lower()
    return ScopeResult(
        in_scope=not answer.startswith("n"),
        tokens_in=resp.tokens_in,
        tokens_out=resp.tokens_out,
        cost_usd=resp.cost_usd,
        latency_ms=resp.latency_ms,
    )
