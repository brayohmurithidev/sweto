import re
from functools import lru_cache
from typing import Literal

import phonenumbers
from pydantic import Field, PostgresDsn, SecretStr, model_validator
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

    whatsapp_provider: Literal["disabled", "console", "meta"] = "disabled"
    whatsapp_send_timeout_seconds: float = Field(default=10, gt=0, le=30)

    # Meta WhatsApp Cloud API (WHATSAPP_PROVIDER=meta). Values come from the
    # environment only; none has a default except the public Graph host.
    meta_graph_api_base_url: str = "https://graph.facebook.com"
    meta_graph_api_version: str | None = None
    meta_whatsapp_phone_number_id: str | None = None
    meta_whatsapp_access_token: SecretStr | None = None
    meta_whatsapp_otp_template_name: str | None = None
    meta_whatsapp_otp_template_language: str | None = None
    meta_app_secret: SecretStr | None = None
    meta_webhook_verify_token: SecretStr | None = None

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
    def validate_meta_whatsapp(self) -> "Settings":
        if self.whatsapp_provider != "meta":
            return self
        required = {
            "META_GRAPH_API_VERSION": self.meta_graph_api_version,
            "META_WHATSAPP_PHONE_NUMBER_ID": self.meta_whatsapp_phone_number_id,
            "META_WHATSAPP_ACCESS_TOKEN": self.meta_whatsapp_access_token,
            "META_WHATSAPP_OTP_TEMPLATE_NAME": self.meta_whatsapp_otp_template_name,
            "META_WHATSAPP_OTP_TEMPLATE_LANGUAGE": (
                self.meta_whatsapp_otp_template_language
            ),
            "META_APP_SECRET": self.meta_app_secret,
            "META_WEBHOOK_VERIFY_TOKEN": self.meta_webhook_verify_token,
        }
        missing = [
            name
            for name, value in required.items()
            if value is None
            or not (
                value.get_secret_value() if isinstance(value, SecretStr) else value
            ).strip()
        ]
        if missing:
            raise ValueError(
                "WHATSAPP_PROVIDER=meta needs these settings: " + ", ".join(missing)
            )
        if not re.fullmatch(r"v\d+\.\d+", self.meta_graph_api_version or ""):
            raise ValueError("META_GRAPH_API_VERSION must look like v24.0.")
        if not (self.meta_whatsapp_phone_number_id or "").isdigit():
            raise ValueError("META_WHATSAPP_PHONE_NUMBER_ID must be numeric.")
        if not re.fullmatch(r"[a-z0-9_]+", self.meta_whatsapp_otp_template_name or ""):
            raise ValueError(
                "META_WHATSAPP_OTP_TEMPLATE_NAME uses lowercase letters, digits "
                "and underscores only."
            )
        if not self.meta_graph_api_base_url.startswith("https://"):
            raise ValueError("META_GRAPH_API_BASE_URL must use https.")
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
