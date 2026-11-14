"""A fresh checkout starts from .env.example, and so does CI."""

from pathlib import Path

from app.core.config import Settings

EXAMPLE = Path(__file__).resolve().parents[1] / ".env.example"


def test_the_example_env_file_is_valid() -> None:
    settings = Settings(_env_file=EXAMPLE)  # type: ignore[call-arg]

    assert settings.mpesa_mode == "disabled"
    assert settings.sms_provider == "console"
