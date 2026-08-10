"""Async SQLAlchemy engine/session setup, shared by every service that talks to Postgres."""

from collections.abc import AsyncGenerator
from datetime import datetime

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import DateTime
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    # Every `Mapped[datetime]` column defaults to TIMESTAMP WITH TIME ZONE — the migration
    # creates all timestamp columns as tz-aware, so the ORM side must match or asyncpg
    # rejects tz-aware Python datetimes bound to a tz-naive column.
    type_annotation_map = {
        datetime: DateTime(timezone=True),
    }


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    postgres_dsn: str = (
        "postgresql+asyncpg://agentforge:agentforge@localhost:5432/agentforge"
    )


settings = DatabaseSettings()

engine = create_async_engine(settings.postgres_dsn, pool_pre_ping=True)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields a session, commits on success, rolls back on error."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
