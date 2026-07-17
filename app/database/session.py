from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()


engine = create_async_engine(
    str(settings.database_url), echo=settings.database_echo, pool_pre_ping=True
)

async_session_factory = async_sessionmaker(
    bind=engine, class_=AsyncSession, autoflush=False, expire_on_commit=False
)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Provide one database session per request."""

    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
