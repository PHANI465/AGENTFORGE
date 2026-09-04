"""Public demo endpoint.

Exposes the shared demo API key so the dashboard can offer a one-click
"try the demo" entry point. In the no-auth public demo (auth-service
disabled), visitors would otherwise have no way to discover the current
key — it's minted server-side by the demo-reset job. The key is
intentionally public: it's scoped to the demo owner (multi-tenant
isolation), per-agent budget-capped, WAF-rate-limited, and the data resets
on a schedule, so sharing it openly is the point, not a leak.

Only mounted-effective when DEMO_API_KEY is set (i.e. an environment
deliberately running as a public demo). Any other deployment returns 404,
so this never leaks anything in a normal single-tenant install.
"""

import os

from agentforge_common.envelope import DataResponse
from agentforge_common.exceptions import NotFoundError
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/demo", tags=["demo"])


class DemoKey(BaseModel):
    api_key: str


@router.get("/api-key", response_model=DataResponse[DemoKey])
async def get_demo_api_key() -> DataResponse[DemoKey]:
    """Return the shared public demo API key, if this is a demo deployment."""
    demo_key = os.getenv("DEMO_API_KEY", "").strip()
    if not demo_key:
        # Not a demo deployment — behave as if the route doesn't exist.
        raise NotFoundError("Not a demo deployment.")
    return DataResponse(data=DemoKey(api_key=demo_key))
