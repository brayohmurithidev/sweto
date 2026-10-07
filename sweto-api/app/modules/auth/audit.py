from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.enums import (
    AuthEventOutcome,
    AuthEventType,
)
from app.modules.auth.models import AuthEvent


class AuthAuditLogger:
    """Record immutable authentication and security events."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def record(
        self,
        *,
        event_type: AuthEventType,
        outcome: AuthEventOutcome,
        user_id: UUID | None = None,
        session_id: UUID | None = None,
        challenge_id: UUID | None = None,
        phone_number: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuthEvent:
        event = AuthEvent(
            event_type=event_type,
            outcome=outcome,
            user_id=user_id,
            session_id=session_id,
            challenge_id=challenge_id,
            phone_number=phone_number,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata_=metadata or {},
        )

        self.session.add(event)

        return event
