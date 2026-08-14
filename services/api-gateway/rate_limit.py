"""Rate limiting for the API Gateway.

Uses slowapi (a Starlette wrapper around limits) keyed by the X-API-Key
header so each authenticated caller gets their own bucket.  Unauthenticated
requests fall back to client IP.

Default limits (configurable via RATE_LIMIT_* env vars):
  - General endpoints: 60/minute
  - Agent run (expensive LLM call): 10/minute
"""

import os

from fastapi import Request
from slowapi import Limiter

RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "60/minute")
RATE_LIMIT_RUN = os.getenv("RATE_LIMIT_RUN", "10/minute")


def _key_func(request: Request) -> str:
    api_key = request.headers.get("X-API-Key", "")
    if api_key:
        return api_key[:16]
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=_key_func)
