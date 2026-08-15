"""Integration test fixtures for the API Gateway.

Boots a real Postgres test database (agentforge_test on the same local
Postgres server used by docker-compose), creates tables directly from the ORM
metadata (bypassing Alembic — standard for fast test schema setup), and wires
FastAPI's dependency_overrides so the app under test talks to that database
through a single shared, per-test session.
"""

import sys
import uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

API_GATEWAY_DIR = Path(__file__).resolve().parents[3] / "services" / "api-gateway"
if str(API_GATEWAY_DIR) not in sys.path:
    sys.path.insert(0, str(API_GATEWAY_DIR))

from agentforge_common import orm  # noqa: E402,F401  registers tables on Base.metadata
from agentforge_common.db import Base  # noqa: E402
from agentforge_common.orm import ApiKeyORM  # noqa: E402
from agentforge_common.security import encrypt_key, generate_api_key, hash_api_key  # noqa: E402

ADMIN_DSN = "postgresql+asyncpg://agentforge:agentforge@localhost:5432/postgres"
TEST_DB_NAME = "agentforge_test"
TEST_DSN = f"postgresql+asyncpg://agentforge:agentforge@localhost:5432/{TEST_DB_NAME}"


@pytest.fixture(scope="session")
async def test_engine():
    # NullPool: pytest-asyncio gives each test function its own event loop by
    # default, but a pooled asyncpg connection is bound to the loop it was
    # opened in. NullPool opens a fresh connection on every checkout instead
    # of reusing one from the pool, so this session-scoped engine still works
    # correctly across tests that each run in a different loop.
    admin_engine = create_async_engine(
        ADMIN_DSN, isolation_level="AUTOCOMMIT", poolclass=NullPool
    )
    async with admin_engine.connect() as conn:
        exists = await conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": TEST_DB_NAME}
        )
        if not exists:
            await conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    await admin_engine.dispose()

    engine = create_async_engine(TEST_DSN, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def session(test_engine):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session
        for table in reversed(Base.metadata.sorted_tables):
            await db_session.execute(table.delete())
        await db_session.commit()


@pytest.fixture
async def api_key(session) -> str:
    raw_key = generate_api_key()
    session.add(
        ApiKeyORM(
            id=uuid.uuid4(),
            key_hash=hash_api_key(raw_key),
            user_id="test-user",
            provider="openai",
            encrypted_key=encrypt_key("sk-test-dummy-key-for-integration-tests"),
        )
    )
    await session.commit()
    return raw_key


@pytest.fixture
async def client(session):
    import dependencies
    import main as app_module
    from rate_limit import limiter

    async def override_get_db():
        yield session

    app_module.app.dependency_overrides[dependencies.get_db] = override_get_db

    # Disabled for the whole suite: slowapi keys its buckets by API key, and
    # some tests call a rate-limited endpoint (e.g. /run) several times in a
    # tight loop against the same key to build up fixture data. That's not
    # rate-limiting behavior under test, so it shouldn't be able to turn an
    # unrelated test's expected 200 into a 429.
    limiter.enabled = False

    transport = ASGITransport(app=app_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app_module.app.dependency_overrides.clear()
