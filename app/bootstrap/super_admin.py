import asyncio
import sys

from app.core.config import get_settings
from app.database.session import async_session_factory, engine
from app.modules.admin.exceptions import AdminError
from app.modules.admin.service import AdminService


async def bootstrap() -> int:
    settings = get_settings()
    try:
        async with async_session_factory() as session:
            try:
                result = await AdminService(session).ensure_initial_super_admin(
                    email=settings.sweto_super_admin_email,
                    password=settings.sweto_super_admin_password,
                )
            except AdminError as exc:
                await session.rollback()
                print(f"Super Admin bootstrap failed: {exc}", file=sys.stderr)
                return 1
    finally:
        await engine.dispose()
    if result.created:
        print(f"Created protected Super Admin: {result.user.email}")
    else:
        print(f"Protected Super Admin already exists: {result.user.email}")
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(bootstrap()))


if __name__ == "__main__":
    main()
