"""Agent CRUD routes — /api/v1/agents."""

import uuid
from datetime import datetime
from typing import Any

import crud_agents
from agentforge_common.enums import AgentStatus
from agentforge_common.envelope import DataResponse, ListMeta, ListResponse
from agentforge_common.models import Agent, AgentCreate, AgentUpdate
from agentforge_common.orm import ApiKeyORM
from dependencies import get_db, require_api_key
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


@router.post(
    "",
    response_model=DataResponse[Agent],
    status_code=status.HTTP_201_CREATED,
    summary="Create an agent",
    operation_id="createAgent",
)
async def create_agent(
    payload: AgentCreate,
    session: AsyncSession = Depends(get_db),
    _auth: ApiKeyORM = Depends(require_api_key),
) -> DataResponse[Agent]:
    agent = await crud_agents.create_agent(session, payload)
    return DataResponse(data=agent)


@router.get(
    "",
    response_model=ListResponse[Agent],
    summary="List agents",
    operation_id="listAgents",
)
async def list_agents(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    status_filter: AgentStatus | None = Query(
        default=None, alias="status", description="Filter by agent status",
    ),
    search: str | None = Query(
        default=None, max_length=200, description="Case-insensitive name search",
    ),
    session: AsyncSession = Depends(get_db),
    _auth: ApiKeyORM = Depends(require_api_key),
) -> ListResponse[Agent]:
    sf = status_filter.value if status_filter else None
    agents, next_cursor = await crud_agents.list_agents(
        session, limit, cursor, status_filter=sf, search=search,
    )
    total = await crud_agents.count_agents(session, status_filter=sf, search=search)
    return ListResponse(
        data=agents,
        meta=ListMeta(total=total, next_cursor=next_cursor, limit=limit),
    )


@router.get(
    "/{agent_id}",
    response_model=DataResponse[Agent],
    summary="Get agent by ID",
    operation_id="getAgent",
)
async def get_agent(
    agent_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _auth: ApiKeyORM = Depends(require_api_key),
) -> DataResponse[Agent]:
    agent = await crud_agents.get_agent(session, agent_id)
    return DataResponse(data=agent)


@router.put(
    "/{agent_id}",
    response_model=DataResponse[Agent],
    summary="Update an agent",
    operation_id="updateAgent",
)
async def update_agent(
    agent_id: uuid.UUID,
    payload: AgentUpdate,
    session: AsyncSession = Depends(get_db),
    _auth: ApiKeyORM = Depends(require_api_key),
) -> DataResponse[Agent]:
    agent = await crud_agents.update_agent(session, agent_id, payload)
    return DataResponse(data=agent)


class AgentVersionOut(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    version: int
    snapshot: dict[str, Any]
    created_at: datetime


class RollbackRequest(BaseModel):
    version: int


@router.get(
    "/{agent_id}/versions",
    response_model=ListResponse[AgentVersionOut],
    summary="List agent version history",
    operation_id="listAgentVersions",
)
async def list_agent_versions(
    agent_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _auth: ApiKeyORM = Depends(require_api_key),
) -> ListResponse[AgentVersionOut]:
    versions = await crud_agents.list_versions(session, agent_id)
    data = [
        AgentVersionOut(
            id=v.id, agent_id=v.agent_id, version=v.version,
            snapshot=v.snapshot, created_at=v.created_at,
        )
        for v in versions
    ]
    return ListResponse(data=data, meta=ListMeta(next_cursor=None, limit=len(data)))


@router.post(
    "/{agent_id}/rollback",
    response_model=DataResponse[Agent],
    summary="Rollback agent to a previous version",
    operation_id="rollbackAgent",
)
async def rollback_agent(
    agent_id: uuid.UUID,
    payload: RollbackRequest,
    session: AsyncSession = Depends(get_db),
    _auth: ApiKeyORM = Depends(require_api_key),
) -> DataResponse[Agent]:
    agent = await crud_agents.rollback_agent(session, agent_id, payload.version)
    return DataResponse(data=agent)


class CloneRequest(BaseModel):
    name: str | None = None


@router.post(
    "/{agent_id}/clone",
    response_model=DataResponse[Agent],
    status_code=status.HTTP_201_CREATED,
    summary="Clone an agent",
    operation_id="cloneAgent",
)
async def clone_agent(
    agent_id: uuid.UUID,
    payload: CloneRequest | None = None,
    session: AsyncSession = Depends(get_db),
    _auth: ApiKeyORM = Depends(require_api_key),
) -> DataResponse[Agent]:
    new_name = payload.name if payload else None
    agent = await crud_agents.clone_agent(session, agent_id, new_name)
    return DataResponse(data=agent)


@router.delete(
    "/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an agent",
    operation_id="deleteAgent",
)
async def delete_agent(
    agent_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _auth: ApiKeyORM = Depends(require_api_key),
) -> None:
    await crud_agents.delete_agent(session, agent_id)
