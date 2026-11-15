from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.core.config import get_settings
from app.modules.admin.gym_verification_router import (
    router as admin_gym_verification_router,
)
from app.modules.admin.router import router as admin_router
from app.modules.auth.router import router as auth_router
from app.modules.auth.whatsapp_webhook_router import (
    router as whatsapp_webhook_router,
)
from app.modules.gyms.router import router as gym_router
from app.modules.members.check_in_router import router as check_in_router
from app.modules.members.dashboard_router import router as dashboard_router
from app.modules.members.payments_router import (
    callback_router as mpesa_callback_router,
)
from app.modules.members.payments_router import router as payments_router
from app.modules.members.router import router as member_router
from app.modules.profiles.router import (
    account_router,
    profile_router,
)

settings = get_settings()

api_router = APIRouter(prefix=settings.api_v1_prefix)

api_router.include_router(health_router)
api_router.include_router(admin_router)
api_router.include_router(admin_gym_verification_router)
api_router.include_router(auth_router)
api_router.include_router(whatsapp_webhook_router)
api_router.include_router(account_router)
api_router.include_router(profile_router)
api_router.include_router(gym_router)
api_router.include_router(member_router)
api_router.include_router(check_in_router)
api_router.include_router(dashboard_router)
api_router.include_router(payments_router)
api_router.include_router(mpesa_callback_router)
if settings.app_environment in {"local", "development", "testing"}:
    from app.modules.gyms.dev_router import router as development_gym_router

    api_router.include_router(development_gym_router)
