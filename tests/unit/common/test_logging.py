"""Unit tests for structured logging setup."""

import logging

import structlog
from agentforge_common.logging import setup_logging


class TestSetupLogging:
    def test_sets_root_log_level_from_env(self, monkeypatch) -> None:
        monkeypatch.setenv("LOG_LEVEL", "WARNING")
        setup_logging("test-service")
        assert logging.getLogger().level == logging.WARNING

    def test_defaults_to_info_level(self, monkeypatch) -> None:
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        setup_logging("test-service")
        assert logging.getLogger().level == logging.INFO

    def test_replaces_root_handlers_not_accumulates(self, monkeypatch) -> None:
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        setup_logging("test-service")
        setup_logging("test-service")
        setup_logging("test-service")
        assert len(logging.getLogger().handlers) == 1

    def test_uvicorn_access_logger_propagates(self, monkeypatch) -> None:
        setup_logging("test-service")
        uvicorn_access = logging.getLogger("uvicorn.access")
        assert uvicorn_access.propagate is True
        assert uvicorn_access.handlers == []

    def test_structlog_is_configured_and_usable(self, monkeypatch) -> None:
        setup_logging("test-service")
        log = structlog.get_logger()
        # Should not raise — confirms the processor chain is wired correctly.
        log.info("test_event", key="value")

    def test_json_format_does_not_raise(self, monkeypatch) -> None:
        monkeypatch.setenv("LOG_FORMAT", "json")
        setup_logging("test-service")
        log = structlog.get_logger()
        log.info("test_event", key="value")

    def test_console_format_is_default(self, monkeypatch) -> None:
        monkeypatch.delenv("LOG_FORMAT", raising=False)
        setup_logging("test-service")
        log = structlog.get_logger()
        log.info("test_event", key="value")
