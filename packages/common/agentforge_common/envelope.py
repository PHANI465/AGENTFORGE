"""Response envelope shared by every service's API, per CLAUDE.md's API design conventions:
success responses are {"data": ..., "meta": ...}, errors are {"error": {"code", "message"}}.
"""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ListMeta(BaseModel):
    """Pagination metadata for list endpoints."""

    total: int | None = None
    limit: int
    offset: int = 0
    next_cursor: str | None = None


class DataResponse(BaseModel, Generic[T]):
    data: T
    meta: dict | None = None


class ListResponse(BaseModel, Generic[T]):
    data: list[T]
    meta: ListMeta


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
