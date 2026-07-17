import pytest

from app.core.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url=(
            "postgresql+asyncpg://sweto:sweto_dev_password@localhost:5432/sweto"
        ),
        otp_hash_secret=("test-otp-secret-that-is-long-enough-for-secure-hmac-testing"),
        jwt_secret_key=("test-jwt-secret-that-is-at-least-thirty-two-bytes-long"),
    )
