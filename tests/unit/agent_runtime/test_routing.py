"""Unit tests for smart model routing."""

import sys
from pathlib import Path

AGENT_RUNTIME_DIR = Path(__file__).resolve().parents[3] / "services" / "agent-runtime"
if str(AGENT_RUNTIME_DIR) not in sys.path:
    sys.path.append(str(AGENT_RUNTIME_DIR))

from routing import pick_model  # noqa: E402


class TestPickModel:
    def test_routing_disabled_uses_configured_model(self):
        model, tier = pick_model(
            user_input="hello", configured_model="gpt-4o", enable_smart_routing=False,
            simple_model="gpt-4o-mini", complex_model="gpt-4o",
            complexity_threshold=200, has_tools=False,
        )
        assert model == "gpt-4o"
        assert tier == "configured"

    def test_missing_simple_model_falls_back_to_configured(self):
        model, tier = pick_model(
            user_input="hello", configured_model="gpt-4o", enable_smart_routing=True,
            simple_model=None, complex_model="gpt-4o",
            complexity_threshold=200, has_tools=False,
        )
        assert model == "gpt-4o"
        assert tier == "configured"

    def test_missing_complex_model_falls_back_to_configured(self):
        model, tier = pick_model(
            user_input="hello", configured_model="gpt-4o", enable_smart_routing=True,
            simple_model="gpt-4o-mini", complex_model=None,
            complexity_threshold=200, has_tools=False,
        )
        assert model == "gpt-4o"
        assert tier == "configured"

    def test_short_input_no_tools_routes_simple(self):
        model, tier = pick_model(
            user_input="hi there", configured_model="gpt-4o", enable_smart_routing=True,
            simple_model="gpt-4o-mini", complex_model="gpt-4o",
            complexity_threshold=200, has_tools=False,
        )
        assert model == "gpt-4o-mini"
        assert tier == "simple"

    def test_long_input_routes_complex(self):
        long_input = "x" * 500
        model, tier = pick_model(
            user_input=long_input, configured_model="gpt-4o", enable_smart_routing=True,
            simple_model="gpt-4o-mini", complex_model="gpt-4o",
            complexity_threshold=200, has_tools=False,
        )
        assert model == "gpt-4o"
        assert tier == "complex"

    def test_short_input_with_tools_routes_complex(self):
        model, tier = pick_model(
            user_input="hi", configured_model="gpt-4o", enable_smart_routing=True,
            simple_model="gpt-4o-mini", complex_model="gpt-4o",
            complexity_threshold=200, has_tools=True,
        )
        assert model == "gpt-4o"
        assert tier == "complex"

    def test_input_exactly_at_threshold_routes_simple(self):
        input_at_threshold = "x" * 200
        model, tier = pick_model(
            user_input=input_at_threshold, configured_model="gpt-4o",
            enable_smart_routing=True, simple_model="gpt-4o-mini", complex_model="gpt-4o",
            complexity_threshold=200, has_tools=False,
        )
        assert model == "gpt-4o-mini"
        assert tier == "simple"
