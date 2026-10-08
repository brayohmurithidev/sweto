"""Meta WhatsApp webhook: subscription check and message status reports.

GET  /api/v1/webhooks/whatsapp  answers Meta's verification request.
POST /api/v1/webhooks/whatsapp  receives signed status notifications.

Both answer 404 unless WHATSAPP_PROVIDER=meta. Request bodies, phone numbers
and secrets are never logged.
"""

import hmac
import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.database.session import get_db_session
from app.integrations.whatsapp.webhook import (
    SIGNATURE_HEADER,
    parse_status_events,
    signature_is_valid,
)
from app.modules.auth.delivery_status import DeliveryStatusService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/whatsapp", tags=["Webhooks"])

ApplicationSettings = Annotated[Settings, Depends(get_settings)]
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


def _require_meta(settings: Settings) -> None:
    if settings.whatsapp_provider != "meta":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.get("", response_class=PlainTextResponse, include_in_schema=False)
async def verify_subscription(
    settings: ApplicationSettings,
    mode: Annotated[str | None, Query(alias="hub.mode")] = None,
    verify_token: Annotated[str | None, Query(alias="hub.verify_token")] = None,
    challenge: Annotated[str | None, Query(alias="hub.challenge")] = None,
) -> PlainTextResponse:
    """Echo hub.challenge when Meta sends our verify token."""

    _require_meta(settings)
    expected = settings.meta_webhook_verify_token
    if (
        mode != "subscribe"
        or expected is None
        or verify_token is None
        or challenge is None
        or not hmac.compare_digest(
            verify_token.encode(), expected.get_secret_value().encode()
        )
    ):
        logger.warning("Rejected WhatsApp webhook verification request")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return PlainTextResponse(challenge)


@router.post("", include_in_schema=False)
async def receive_notification(
    request: Request,
    settings: ApplicationSettings,
    session: DatabaseSession,
) -> dict[str, bool]:
    """Apply message status reports from a signed Meta notification."""

    _require_meta(settings)
    app_secret = settings.meta_app_secret
    phone_number_id = settings.meta_whatsapp_phone_number_id
    if app_secret is None or phone_number_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    body = await request.body()
    if not signature_is_valid(
        body=body,
        header=request.headers.get(SIGNATURE_HEADER),
        app_secret=app_secret.get_secret_value(),
    ):
        logger.warning("Rejected WhatsApp webhook with an invalid signature")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    try:
        payload = json.loads(body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST) from exc

    events = parse_status_events(payload, phone_number_id=phone_number_id)
    if events:
        await DeliveryStatusService(session).apply_whatsapp_events(events)
    return {"success": True}
