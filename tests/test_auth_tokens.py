from uuid import uuid4

import jwt

from app.core.config import Settings
from app.modules.auth.tokens import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
)


def test_create_access_token_contains_expected_claims(
    settings: Settings,
) -> None:
    user_id = uuid4()
    session_id = uuid4()

    token, expires_at = create_access_token(
        user_id=user_id,
        session_id=session_id,
        settings=settings,
    )

    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )

    assert payload["sub"] == str(user_id)
    assert payload["sid"] == str(session_id)
    assert payload["type"] == "access"
    assert expires_at is not None


def test_generate_refresh_token_is_not_deterministic() -> None:
    first = generate_refresh_token()
    second = generate_refresh_token()

    assert first != second
    assert len(first) > 40


def test_hash_refresh_token_is_deterministic() -> None:
    token = "example-refresh-token"

    assert hash_refresh_token(token) == hash_refresh_token(token)
