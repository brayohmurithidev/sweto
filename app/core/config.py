from functools import lru_cache
from typing import Literal

from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configurations loaded from environment variables."""

    app_name: str = "SWETO API"
    app_version: str = "0.1.0"
    app_environment: Literal["local", "development", "staging", "production"] = "local"
    debug: bool = True

    api_v1_prefix: str = "/api/v1"

    database_url: PostgresDsn
    database_echo: bool = False

    otp_length: int = 6
    otp_expiry_seconds: int = 300
    otp_resend_cooldown_seconds: int = 60
    otp_max_attempts: int = 5

    otp_hash_secret: str
    default_phone_region: str = "KE"

    sms_provider: Literal["console"] = "console"

    jwt_secret_key: str
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_expiry_minutes: int = 30
    refresh_token_expiry_days: int = 30

    session_activity_update_interval_seconds: int = 300

    redis_url: str = "redis://localhost:6379/0"
    redis_key_prefix: str = "sweto"

    otp_request_phone_limit: int = 5
    otp_request_phone_window_seconds: int = 900

    otp_request_ip_limit: int = 20
    otp_request_ip_window_seconds: int = 3600

    otp_verify_challenge_limit: int = 10
    otp_verify_challenge_window_seconds: int = 900

    otp_verify_ip_limit: int = 30
    otp_verify_ip_window_seconds: int = 900

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )


@lru_cache
def get_settings() -> Settings:
    """
    Return one cached settings instance.
    Caching prevents the environment file from being re-read every time.
    settings are requested through dependency injection.
    """
    return Settings()
