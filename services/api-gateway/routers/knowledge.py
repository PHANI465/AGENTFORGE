"""Knowledge base routes (RAG) — /api/v1/agents/{id}/knowledge.

Lets an agent be given reference documents. On ingest the text is chunked and
embedded; at run time (see routers/runs.py) the most relevant chunks for the
user's question are retrieved and injected into the agent's context. Scoped to
the caller's owner_id like every other resource.
"""

import os
import uuid

import crud_agents
import httpx
from agentforge_common.envelope import DataResponse
from agentforge_common.exceptions import AgentForgeError
from agentforge_common.orm import ApiKeyORM, KnowledgeChunkORM
from agentforge_common.security import decrypt_key
from dependencies import get_db, owner_id_of, require_api_key
from fastapi import APIRouter, Depends, status
from knowledge import chunk_text, embed_texts
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/agents", tags=["knowledge"])


class EmbeddingError(AgentForgeError):
    code = "embedding_error"


class KnowledgeAdd(BaseModel):
    source: str = Field(default="document", max_length=200)
    text: str = Field(min_length=1, max_length=200_000)


class KnowledgeInfo(BaseModel):
    chunk_count: int
    sources: list[str]


def _llm_key(auth: ApiKeyORM) -> str:
    return decrypt_key(auth.encrypted_key) or os.getenv("OPENAI_API_KEY", "")


@router.post(
    "/{agent_id}/knowledge",
    response_model=DataResponse[KnowledgeInfo],
    status_code=status.HTTP_201_CREATED,
    summary="Add a document to an agent's knowledge base",
    operation_id="addKnowledge",
)
async def add_knowledge(
    agent_id: uuid.UUID,
    payload: KnowledgeAdd,
    session: AsyncSession = Depends(get_db),
    auth: ApiKeyORM = Depends(require_api_key),
) -> DataResponse[KnowledgeInfo]:
    owner_id = owner_id_of(auth)
    await crud_agents.get_agent(session, owner_id, agent_id)  # 404s if not the owner's

    chunks = chunk_text(payload.text)
    if not chunks:
        raise EmbeddingError("No usable text to add.")

    key = _llm_key(auth)
    if not key:
        raise EmbeddingError("No LLM key configured for embeddings.")
    try:
        vectors = await embed_texts(chunks, key)
    except httpx.HTTPStatusError as e:
        raise EmbeddingError(
            "Embedding failed — RAG needs an OpenAI-compatible key "
            f"(provider returned {e.response.status_code})."
        ) from e
    except httpx.RequestError as e:
        raise EmbeddingError(f"Embedding request failed: {e}") from e

    for content, vec in zip(chunks, vectors, strict=False):
        session.add(KnowledgeChunkORM(
            id=uuid.uuid4(), owner_id=owner_id, agent_id=agent_id,
            source=payload.source, content=content, embedding=vec,
        ))
    await session.flush()

    return await _info(session, owner_id, agent_id)


@router.get(
    "/{agent_id}/knowledge",
    response_model=DataResponse[KnowledgeInfo],
    summary="Summarize an agent's knowledge base",
    operation_id="getKnowledge",
)
async def get_knowledge(
    agent_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    auth: ApiKeyORM = Depends(require_api_key),
) -> DataResponse[KnowledgeInfo]:
    owner_id = owner_id_of(auth)
    await crud_agents.get_agent(session, owner_id, agent_id)
    return await _info(session, owner_id, agent_id)


@router.delete(
    "/{agent_id}/knowledge",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear an agent's knowledge base",
    operation_id="clearKnowledge",
)
async def clear_knowledge(
    agent_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    auth: ApiKeyORM = Depends(require_api_key),
) -> None:
    owner_id = owner_id_of(auth)
    await crud_agents.get_agent(session, owner_id, agent_id)
    await session.execute(
        delete(KnowledgeChunkORM).where(
            KnowledgeChunkORM.agent_id == agent_id,
            KnowledgeChunkORM.owner_id == owner_id,
        )
    )
    await session.flush()


async def _info(
    session: AsyncSession, owner_id: uuid.UUID, agent_id: uuid.UUID
) -> DataResponse[KnowledgeInfo]:
    count = (
        await session.execute(
            select(func.count()).select_from(KnowledgeChunkORM).where(
                KnowledgeChunkORM.agent_id == agent_id,
                KnowledgeChunkORM.owner_id == owner_id,
            )
        )
    ).scalar_one()
    sources = (
        await session.execute(
            select(KnowledgeChunkORM.source)
            .where(
                KnowledgeChunkORM.agent_id == agent_id,
                KnowledgeChunkORM.owner_id == owner_id,
            )
            .distinct()
        )
    ).scalars().all()
    return DataResponse(data=KnowledgeInfo(chunk_count=count, sources=list(sources)))
