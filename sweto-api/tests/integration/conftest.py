"""Fixtures for tests that run the real API against PostgreSQL.

These tests are opt-in: set SWETO_TEST_DATABASE_URL to a dedicated, disposable
database (it is migrated and every table is truncated between tests). They are
skipped otherwise, so the default `pytest` run needs no database.
"""

import os
import subprocess
import sys
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import Settings, get_settings
from app.database.session import get_db_session
from app.integrations.sms.base import SMSDeliveryError
from app.integrations.sms.dependencies import get_sms_provider
from app.main import app
from app.rate_limit.dependencies import get_rate_limiter
from app.rate_limit.memory import MemoryRateLimiter

API_ROOT = Path(__file__).resolve().parents[2]
TEST_DATABASE_URL = os.environ.get("SWETO_TEST_DATABASE_URL")

# Seeded by migrations and needed by the app; never truncated.
_PRESERVED_TABLES = {"alembic_version", "amenities"}


@pytest.fixture(scope="session")
def migrated_database_url() -> str:
    if not TEST_DATABASE_URL:
        pytest.skip("Set SWETO_TEST_DATABASE_URL to run integration tests.")
    if not TEST_DATABASE_URL.rsplit("/", 1)[-1].endswith("_test"):
        pytest.fail("SWETO_TEST_DATABASE_URL must name a database ending in _test.")
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=API_ROOT,
        env={**os.environ, "DATABASE_URL": TEST_DATABASE_URL},
        check=True,
        capture_output=True,
    )
    return TEST_DATABASE_URL


@pytest_asyncio.fixture
async def db_engine(migrated_database_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(migrated_database_url, poolclass=NullPool)
    async with engine.begin() as connection:
        result = await connection.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        )
        tables = [row[0] for row in result.all() if row[0] not in _PRESERVED_TABLES]
        if tables:
            quoted = ", ".join(f'"{name}"' for name in tables)
            await connection.execute(text(f"TRUNCATE {quoted} CASCADE"))
    yield engine
    await engine.dispose()


@dataclass
class RecordingSMSProvider:
    """SMS provider double that records messages or fails on demand."""

    sent: list[tuple[str, str]] = field(default_factory=list)
    failure: Exception | None = None
    delay_seconds: float = 0

    async def send_otp(
        self,
        *,
        phone_number: str,
        otp_code: str,
        expires_in_seconds: int,
    ) -> None:
        if self.delay_seconds:
            import asyncio

            await asyncio.sleep(self.delay_seconds)
        if self.failure is not None:
            raise self.failure
        self.sent.append((phone_number, otp_code))

    def last_code(self) -> str:
        return self.sent[-1][1]


@dataclass
class IntegrationAPI:
    client: AsyncClient
    sms: RecordingSMSProvider
    engine: AsyncEngine
    settings: Settings

    async def sql(self, statement: str, **params: object) -> list[tuple[object, ...]]:
        async with self.engine.begin() as connection:
            result = await connection.execute(text(statement), params)
            return [tuple(row) for row in result.all()] if result.returns_rows else []


@pytest.fixture
def test_settings() -> Iterator[Settings]:
    yield get_settings().model_copy(update={"sms_send_timeout_seconds": 0.2})


@pytest_asyncio.fixture
async def api(
    db_engine: AsyncEngine, test_settings: Settings
) -> AsyncIterator[IntegrationAPI]:
    factory = async_sessionmaker(
        bind=db_engine, class_=AsyncSession, autoflush=False, expire_on_commit=False
    )

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    sms = RecordingSMSProvider()
    limiter = MemoryRateLimiter()
    app.dependency_overrides[get_db_session] = session_override
    app.dependency_overrides[get_sms_provider] = lambda: sms
    app.dependency_overrides[get_rate_limiter] = lambda: limiter
    app.dependency_overrides[get_settings] = lambda: test_settings
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield IntegrationAPI(
                client=client, sms=sms, engine=db_engine, settings=test_settings
            )
    finally:
        app.dependency_overrides.clear()


__all__ = ["IntegrationAPI", "RecordingSMSProvider", "SMSDeliveryError"]
