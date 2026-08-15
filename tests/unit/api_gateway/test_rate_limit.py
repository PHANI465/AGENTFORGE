"""Unit tests for the rate limiter's key function and env-driven defaults."""

import importlib
import sys
from pathlib import Path
from unittest.mock import Mock

API_GATEWAY_DIR = Path(__file__).resolve().parents[3] / "services" / "api-gateway"
if str(API_GATEWAY_DIR) not in sys.path:
    sys.path.append(str(API_GATEWAY_DIR))

import rate_limit  # noqa: E402


def _mock_request(api_key: str | None = None, client_host: str | None = "203.0.113.5"):
    request = Mock()
    request.headers = {"X-API-Key": api_key} if api_key else {}
    request.client = Mock(host=client_host) if client_host else None
    return request


class TestKeyFunc:
    def test_uses_api_key_when_present(self) -> None:
        request = _mock_request(api_key="afk_abcdefghijklmnopqrstuvwxyz")
        assert rate_limit._key_func(request) == "afk_abcdefghijkl"

    def test_truncates_api_key_to_16_chars(self) -> None:
        request = _mock_request(api_key="afk_" + "x" * 40)
        key = rate_limit._key_func(request)
        assert len(key) == 16

    def test_falls_back_to_client_host_when_no_api_key(self) -> None:
        request = _mock_request(api_key=None, client_host="198.51.100.7")
        assert rate_limit._key_func(request) == "198.51.100.7"

    def test_falls_back_to_unknown_when_no_client(self) -> None:
        request = _mock_request(api_key=None, client_host=None)
        assert rate_limit._key_func(request) == "unknown"

    def test_different_api_keys_produce_different_buckets(self) -> None:
        req_a = _mock_request(api_key="afk_aaaaaaaaaaaaaaaaaaaa")
        req_b = _mock_request(api_key="afk_bbbbbbbbbbbbbbbbbbbb")
        assert rate_limit._key_func(req_a) != rate_limit._key_func(req_b)


class TestDefaults:
    def test_default_limits_when_env_unset(self, monkeypatch) -> None:
        monkeypatch.delenv("RATE_LIMIT_DEFAULT", raising=False)
        monkeypatch.delenv("RATE_LIMIT_RUN", raising=False)
        reloaded = importlib.reload(rate_limit)
        assert reloaded.RATE_LIMIT_DEFAULT == "60/minute"
        assert reloaded.RATE_LIMIT_RUN == "10/minute"
        importlib.reload(rate_limit)  # restore module state for later tests

    def test_env_vars_override_defaults(self, monkeypatch) -> None:
        monkeypatch.setenv("RATE_LIMIT_DEFAULT", "5/second")
        monkeypatch.setenv("RATE_LIMIT_RUN", "1/second")
        reloaded = importlib.reload(rate_limit)
        assert reloaded.RATE_LIMIT_DEFAULT == "5/second"
        assert reloaded.RATE_LIMIT_RUN == "1/second"
        monkeypatch.delenv("RATE_LIMIT_DEFAULT", raising=False)
        monkeypatch.delenv("RATE_LIMIT_RUN", raising=False)
        importlib.reload(rate_limit)  # restore module state for later tests

    def test_limiter_uses_key_func(self) -> None:
        assert rate_limit.limiter._key_func is rate_limit._key_func
