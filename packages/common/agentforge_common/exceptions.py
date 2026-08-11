"""Shared exception types used across AgentForge services.

Each carries an HTTP-agnostic `code` and `message`; services map them to HTTP
status codes at the API boundary (see api-gateway's exception handlers).
"""


class AgentForgeError(Exception):
    """Base class for all AgentForge application errors."""

    code = "internal_error"

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class NotFoundError(AgentForgeError):
    code = "not_found"

    def __init__(self, resource: str, resource_id: str):
        super().__init__(f"{resource} '{resource_id}' not found")


class UnauthorizedError(AgentForgeError):
    code = "unauthorized"

    def __init__(self, message: str = "Missing or invalid API key"):
        super().__init__(message)


class ConflictError(AgentForgeError):
    code = "conflict"
