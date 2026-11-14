"""Meta WhatsApp webhook helpers: signature check and status parsing.

Meta signs every webhook POST with ``X-Hub-Signature-256: sha256=<hex>``, an
HMAC-SHA256 of the raw request body keyed with the app secret. Message status
notifications arrive under ``entry[].changes[]`` with ``field == "messages"``
and ``value.statuses[]``.
"""

import hashlib
import hmac
from dataclasses import dataclass
from typing import Any

SIGNATURE_HEADER = "X-Hub-Signature-256"

# Statuses SWETO tracks. Others (for example "played" for voice) are ignored.
TRACKED_STATUSES = frozenset({"sent", "delivered", "read", "failed"})


@dataclass(frozen=True)
class WhatsAppStatusEvent:
    message_id: str
    status: str
    error_code: str | None


def signature_is_valid(*, body: bytes, header: str | None, app_secret: str) -> bool:
    """Check Meta's X-Hub-Signature-256 header in constant time."""

    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    # Compare bytes: a non-ASCII header must fail the check, not raise.
    received = header.removeprefix("sha256=").encode("utf-8", "replace")
    return hmac.compare_digest(expected.encode(), received)


def parse_status_events(
    payload: Any, *, phone_number_id: str
) -> list[WhatsAppStatusEvent]:
    """Extract message status events for our sender number from a webhook.

    Events for other phone numbers, other webhook fields and statuses we
    don't track are skipped. Malformed parts are skipped rather than failing
    the whole notification, so one bad item can't block the others.
    """

    events: list[WhatsAppStatusEvent] = []
    if not isinstance(payload, dict):
        return events
    for entry in _list(payload.get("entry")):
        for change in _list(_dict(entry).get("changes")):
            change = _dict(change)
            if change.get("field") != "messages":
                continue
            value = _dict(change.get("value"))
            metadata = _dict(value.get("metadata"))
            if str(metadata.get("phone_number_id", "")) != phone_number_id:
                continue
            for status in _list(value.get("statuses")):
                status = _dict(status)
                message_id = status.get("id")
                state = status.get("status")
                if not isinstance(message_id, str) or not message_id:
                    continue
                if state not in TRACKED_STATUSES:
                    continue
                error_code = None
                errors = _list(status.get("errors"))
                if errors:
                    code = _dict(errors[0]).get("code")
                    error_code = str(code)[:32] if code is not None else None
                events.append(
                    WhatsAppStatusEvent(
                        message_id=message_id, status=state, error_code=error_code
                    )
                )
    return events


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
