from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.redis import redis_client
from app.database.session import get_db_session
from app.shared.responses import APIResponse

router = APIRouter(tags=["Health"])


DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("/health", response_model=APIResponse[dict[str, str]])
async def health_check() -> APIResponse[dict[str, str]]:
    """
    Confirm that the API process is running.
    Later, a separate readiness endpoint will
    also check dependencies such as PostgreSQL,
    Redis, and S3 to ensure that the API is ready to serve requests.
    """
    settings = get_settings()
    return APIResponse(
        data={
            "status": "healthy",
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.app_environment,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    )


@router.get(
    "/ready",
    response_model=APIResponse[dict[str, str]],
)
async def readiness_check(session: DatabaseSession) -> APIResponse[dict[str, str]]:
    """Confirm that the API can connect to PostgreSQL."""

    await session.execute(text("SELECT 1"))

    await redis_client.ping()

    return APIResponse(
        data={
            "status": "ready",
            "database": "connected",
            "redis": "connected",
        }
    )
