from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.core.config import get_settings
from app.modules.admin.router import router as admin_router
from app.modules.auth.router import router as auth_router
from app.modules.gyms.router import router as gym_router
from app.modules.profiles.router import (
    account_router,
    profile_router,
)

settings = get_settings()

api_router = APIRouter(prefix=settings.api_v1_prefix)

api_router.include_router(health_router)
api_router.include_router(admin_router)
api_router.include_router(auth_router)
api_router.include_router(account_router)
api_router.include_router(profile_router)
api_router.include_router(gym_router)
