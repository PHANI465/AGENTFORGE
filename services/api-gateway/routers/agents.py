"""Agent CRUD routes — /api/v1/agents."""

import uuid

import crud_agents
from agentforge_common.envelope import DataResponse, ListMeta, ListResponse
from agentforge_common.models import Agent, AgentCreate, AgentUpdate
from agentforge_common.orm import ApiKeyORM
from dependencies import get_db, require_api_key
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


@router.post("", response_model=DataResponse[Agent], status_code=status.HTTP_201_CREATED)
async def create_agent(
    payload: AgentCreate,
    session: AsyncSession = Depends(get_db),
    _auth: ApiKeyORM = Depends(require_api_key),
) -> DataResponse[Agent]:
    agent = await crud_agents.create_agent(session, payload)
    return DataResponse(data=agent)


@router.get("", response_model=ListResponse[Agent])
async def list_agents(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
    _auth: ApiKeyORM = Depends(require_api_key),
) -> ListResponse[Agent]:
    agents, next_cursor = await crud_agents.list_agents(session, limit, cursor)
    return ListResponse(data=agents, meta=ListMeta(next_cursor=next_cursor, limit=limit))


@router.get("/{agent_id}", response_model=DataResponse[Agent])
async def get_agent(
    agent_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _auth: ApiKeyORM = Depends(require_api_key),
) -> DataResponse[Agent]:
    agent = await crud_agents.get_agent(session, agent_id)
    return DataResponse(data=agent)


@router.put("/{agent_id}", response_model=DataResponse[Agent])
async def update_agent(
    agent_id: uuid.UUID,
    payload: AgentUpdate,
    session: AsyncSession = Depends(get_db),
    _auth: ApiKeyORM = Depends(require_api_key),
) -> DataResponse[Agent]:
    agent = await crud_agents.update_agent(session, agent_id, payload)
    return DataResponse(data=agent)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _auth: ApiKeyORM = Depends(require_api_key),
) -> None:
    await crud_agents.delete_agent(session, agent_id)
