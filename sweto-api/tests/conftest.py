import os

import pytest

from app.core.config import Settings

# Provider settings a developer may have in their shell or sweto-api/.env.
# Tests that build Settings directly must see only what they pass in.
_PROVIDER_ENV_PREFIXES = (
    "SMS_",
    "WHATSAPP_",
    "ADVANTA_",
    "AFRICASTALKING_",
    "META_",
)


@pytest.fixture(autouse=True)
def _isolate_settings_from_local_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep a developer's .env and provider env vars out of the tests.

    The app itself was already configured at import time, so this only
    affects Settings objects that tests construct.
    """
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    for name in list(os.environ):
        if name.upper().startswith(_PROVIDER_ENV_PREFIXES):
            monkeypatch.delenv(name)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url=(
            "postgresql+asyncpg://sweto:sweto_dev_password@localhost:5432/sweto"
        ),
        otp_hash_secret=("test-otp-secret-that-is-long-enough-for-secure-hmac-testing"),
        jwt_secret_key=("test-jwt-secret-that-is-at-least-thirty-two-bytes-long"),
    )
