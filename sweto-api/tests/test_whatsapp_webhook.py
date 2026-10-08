"""Meta webhook signature check and status parsing (pure functions)."""

import hashlib
import hmac
import json

from app.integrations.whatsapp.webhook import parse_status_events, signature_is_valid

SECRET = "test-app-secret"
PHONE_NUMBER_ID = "1234567890"


def sign(body: bytes, secret: str = SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def notification(*statuses: dict, phone_number_id: str = PHONE_NUMBER_ID) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WABA_ID",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "254700000000",
                                "phone_number_id": phone_number_id,
                            },
                            "statuses": list(statuses),
                        },
                    }
                ],
            }
        ],
    }


def test_valid_signature_is_accepted() -> None:
    body = b'{"object":"whatsapp_business_account"}'
    assert signature_is_valid(body=body, header=sign(body), app_secret=SECRET)


def test_invalid_missing_or_malformed_signatures_are_rejected() -> None:
    body = b'{"object":"whatsapp_business_account"}'
    for header in (
        None,
        "",
        sign(body, "wrong-secret"),
        sign(body + b" "),  # body changed after signing
        sign(body).removeprefix("sha256="),  # no prefix
        "sha1=" + hashlib.sha1(body).hexdigest(),
    ):
        assert not signature_is_valid(body=body, header=header, app_secret=SECRET)


def test_status_events_are_extracted_with_error_codes() -> None:
    payload = notification(
        {"id": "wamid.1", "status": "sent", "recipient_id": "256701234567"},
        {"id": "wamid.2", "status": "delivered"},
        {
            "id": "wamid.3",
            "status": "failed",
            "errors": [{"code": 131026, "title": "Message undeliverable"}],
        },
    )

    events = parse_status_events(payload, phone_number_id=PHONE_NUMBER_ID)

    assert [(e.message_id, e.status, e.error_code) for e in events] == [
        ("wamid.1", "sent", None),
        ("wamid.2", "delivered", None),
        ("wamid.3", "failed", "131026"),
    ]


def test_other_numbers_fields_and_statuses_are_ignored() -> None:
    other_number = notification(
        {"id": "wamid.1", "status": "failed"}, phone_number_id="999"
    )
    other_field = notification({"id": "wamid.2", "status": "sent"})
    other_field["entry"][0]["changes"][0]["field"] = "message_template_status_update"
    untracked = notification({"id": "wamid.3", "status": "played"})

    for payload in (other_number, other_field, untracked):
        assert parse_status_events(payload, phone_number_id=PHONE_NUMBER_ID) == []


def test_malformed_items_are_skipped_without_failing_the_rest() -> None:
    payload = notification(
        "not-a-dict",
        {"status": "sent"},  # no id
        {"id": "", "status": "sent"},
        {"id": "wamid.ok", "status": "read", "errors": "nope"},
    )
    payload["entry"].append({"changes": "not-a-list"})

    events = parse_status_events(payload, phone_number_id=PHONE_NUMBER_ID)

    assert [(e.message_id, e.status) for e in events] == [("wamid.ok", "read")]
    for broken in (None, [], "text", {"entry": "x"}, json.loads("{}")):
        assert parse_status_events(broken, phone_number_id=PHONE_NUMBER_ID) == []
