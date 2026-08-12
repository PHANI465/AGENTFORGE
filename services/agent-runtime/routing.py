"""Smart model routing — send simple turns to a cheaper model, complex ones to a stronger one.

Opt-in per agent via TokenOptimizationConfig. A turn is "complex" if its input
is longer than complexity_threshold characters, or if the agent has any tools
available (tool-using tasks tend to need stronger reasoning). Everything else
routes to the cheaper model. Routing is decided once per run, from the initial
user input — not re-evaluated each iteration, so a run's model choice stays
predictable and traceable.
"""


def pick_model(
    user_input: str,
    configured_model: str,
    enable_smart_routing: bool,
    simple_model: str | None,
    complex_model: str | None,
    complexity_threshold: int,
    has_tools: bool,
) -> tuple[str, str]:
    """Return (model_to_use, tier) where tier is 'simple' | 'complex' | 'configured'.

    Falls back to the agent's configured_model (tier 'configured') whenever
    routing is disabled or either tier model is missing from the config.
    """
    if not enable_smart_routing or not simple_model or not complex_model:
        return configured_model, "configured"

    is_complex = has_tools or len(user_input) > complexity_threshold
    if is_complex:
        return complex_model, "complex"
    return simple_model, "simple"
