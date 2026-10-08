from functools import lru_cache
from typing import Literal

import phonenumbers
from pydantic import Field, PostgresDsn, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configurations loaded from environment variables."""

    app_name: str = "SWETO API"
    app_version: str = "0.1.0"
    app_environment: Literal[
        "local", "development", "testing", "staging", "production"
    ] = "local"
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
    sms_send_timeout_seconds: float = Field(default=10, gt=0, le=30)

    # Countries (ISO 3166 alpha-2) whose numbers can sign in. Codes go by SMS
    # in otp_sms_regions and by WhatsApp everywhere else (D-011).
    otp_supported_regions: list[str] = Field(
        default_factory=lambda: ["KE", "UG", "TZ", "RW", "BI", "SS", "CD", "SO"]
    )
    otp_sms_regions: list[str] = Field(default_factory=lambda: ["KE"])

    whatsapp_provider: Literal["disabled", "console"] = "disabled"
    whatsapp_send_timeout_seconds: float = Field(default=10, gt=0, le=30)

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

    password_login_email_limit: int = 5
    password_login_email_window_seconds: int = 900
    password_login_ip_limit: int = 20
    password_login_ip_window_seconds: int = 900

    sweto_super_admin_email: str | None = None
    sweto_super_admin_password: str | None = None

    aws_region: str = "af-south-1"
    aws_s3_uploads_bucket: str | None = None
    aws_s3_presigned_upload_expiry_seconds: int = Field(default=300, ge=60, le=900)
    aws_s3_presigned_download_expiry_seconds: int = Field(default=300, ge=60, le=900)
    aws_s3_endpoint_url: str | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None

    @model_validator(mode="after")
    def validate_aws_credentials(self) -> "Settings":
        has_access_key = bool(self.aws_access_key_id)
        has_secret_key = bool(self.aws_secret_access_key)
        if has_access_key != has_secret_key:
            raise ValueError(
                "AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY "
                "must be configured together."
            )
        return self

    @model_validator(mode="after")
    def validate_sms_provider(self) -> "Settings":
        # The console provider writes OTP codes to the logs. It must never run
        # where real users sign in.
        if self.sms_provider == "console" and self.app_environment in {
            "staging",
            "production",
        }:
            raise ValueError(
                "SMS_PROVIDER=console logs verification codes and is only "
                "allowed in local, development and testing environments."
            )
        return self

    @model_validator(mode="after")
    def validate_otp_regions(self) -> "Settings":
        supported = set(self.otp_supported_regions)
        unknown = sorted(
            (supported | set(self.otp_sms_regions)) - phonenumbers.SUPPORTED_REGIONS
        )
        if unknown:
            raise ValueError(
                "OTP regions must be ISO 3166 alpha-2 codes in upper case; "
                f"unknown: {', '.join(unknown)}."
            )
        outside = sorted(set(self.otp_sms_regions) - supported)
        if outside:
            raise ValueError(
                "OTP_SMS_REGIONS must be a subset of OTP_SUPPORTED_REGIONS; "
                f"not supported: {', '.join(outside)}."
            )
        return self

    @model_validator(mode="after")
    def validate_whatsapp_provider(self) -> "Settings":
        # Like the console SMS provider, this one writes codes to the logs.
        if self.whatsapp_provider == "console" and self.app_environment in {
            "staging",
            "production",
        }:
            raise ValueError(
                "WHATSAPP_PROVIDER=console logs verification codes and is only "
                "allowed in local, development and testing environments."
            )
        return self

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
