import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.integrations.delivery import OTPDeliveryError
from app.modules.auth.audit import AuthAuditLogger
from app.modules.auth.enums import (
    AuthEventOutcome,
    AuthEventType,
    OTPDeliveryStatus,
    OTPPurpose,
    OTPStatus,
    SessionStatus,
    UserStatus,
)
from app.modules.auth.exceptions import (
    AuthenticationRateLimitError,
    CurrentPasswordIncorrectError,
    CurrentSessionRevocationError,
    InvalidEmailOrPasswordError,
    InvalidOTPError,
    InvalidRefreshTokenError,
    OTPAttemptsExceededError,
    OTPChallengeConsumedError,
    OTPChallengeExpiredError,
    OTPChallengeNotFoundError,
    OTPDeliveryFailedError,
    OTPResendCooldownError,
    PasswordLoginNotAvailableError,
    PasswordReuseNotAllowedError,
    RefreshSessionExpiredError,
    RefreshSessionRevokedError,
    SessionNotFoundError,
    UserAccessDeniedError,
)
from app.modules.auth.models import (
    OTPChallenge,
    RefreshSession,
    User,
)
from app.modules.auth.otp_delivery import OTPDelivery
from app.modules.auth.phone import normalize_phone_number
from app.modules.auth.repository import (
    OTPChallengeRepository,
    RefreshSessionRepository,
    UserRepository,
)
from app.modules.auth.schemas import (
    AuthenticatedUserData,
    ChangePasswordData,
    ChangePasswordRequest,
    LogoutAllData,
    OTPDeliveryData,
    PasswordLoginData,
    PasswordLoginRequest,
    RefreshTokenData,
    RefreshTokenRequest,
    RequestOTPData,
    SessionData,
    SessionListData,
    TokenData,
    VerifyOTPData,
    VerifyOTPRequest,
)
from app.modules.auth.security import (
    generate_numeric_otp,
    hash_otp,
    hash_password,
    normalize_email,
    password_needs_rehash,
    validate_password_policy,
    verify_otp_hash,
    verify_password,
)
from app.modules.auth.tokens import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
)
from app.rate_limit.base import RateLimiter

logger = logging.getLogger(__name__)

_DUMMY_PASSWORD_HASH = hash_password("invalid-password-login-placeholder")


class AuthenticationService:
    """Application service for authentication workflows."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        settings: Settings,
        otp_delivery: OTPDelivery,
        rate_limiter: RateLimiter,
    ) -> None:
        self.session = session
        self.settings = settings
        self.otp_delivery = otp_delivery
        self.rate_limiter = rate_limiter

        self.otp_repository = OTPChallengeRepository(session)
        self.user_repository = UserRepository(session)
        self.refresh_session_repository = RefreshSessionRepository(session)
        self.audit_logger = AuthAuditLogger(session)

    async def _enforce_password_login_limits(
        self,
        *,
        email: str,
        ip_address: str | None,
    ) -> None:
        email_result = await self.rate_limiter.consume(
            key=f"password-login:email:{email}",
            limit=self.settings.password_login_email_limit,
            window_seconds=self.settings.password_login_email_window_seconds,
        )
        if not email_result.allowed:
            raise AuthenticationRateLimitError(
                code="PASSWORD_LOGIN_RATE_LIMITED",
                message="Too many password login attempts were made.",
                retry_after_seconds=email_result.retry_after_seconds,
                limit=email_result.limit,
            )

        if ip_address is None:
            return

        ip_result = await self.rate_limiter.consume(
            key=f"password-login:ip:{ip_address}",
            limit=self.settings.password_login_ip_limit,
            window_seconds=self.settings.password_login_ip_window_seconds,
        )
        if not ip_result.allowed:
            raise AuthenticationRateLimitError(
                code="PASSWORD_LOGIN_RATE_LIMITED",
                message="Too many password login attempts were made.",
                retry_after_seconds=ip_result.retry_after_seconds,
                limit=ip_result.limit,
            )

    @staticmethod
    def _validate_new_password(password: str) -> None:
        validate_password_policy(password)

    @staticmethod
    def _build_user_data(user: User) -> AuthenticatedUserData:
        return AuthenticatedUserData(
            id=user.id,
            phone_number=user.phone_number,
            email=user.email,
            status=user.status.value,
            is_phone_verified=user.is_phone_verified,
            role=user.role,
            must_change_password=user.must_change_password,
        )

    async def password_login(
        self,
        *,
        payload: PasswordLoginRequest,
        ip_address: str | None,
        user_agent: str | None,
    ) -> PasswordLoginData:
        """Authenticate email/password credentials using existing sessions."""

        now = datetime.now(UTC)
        email = normalize_email(str(payload.email))
        await self._enforce_password_login_limits(
            email=email,
            ip_address=ip_address,
        )
        user = await self.user_repository.get_by_email(email)
        stored_hash = (
            user.password_hash
            if user is not None and user.password_hash is not None
            else _DUMMY_PASSWORD_HASH
        )
        password_is_valid = verify_password(payload.password, stored_hash)

        if user is None or user.password_hash is None or not password_is_valid:
            self.audit_logger.record(
                event_type=AuthEventType.LOGIN_DENIED,
                outcome=AuthEventOutcome.FAILURE,
                user_id=user.id if user is not None else None,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"reason": "invalid_email_or_password"},
            )
            await self.session.commit()
            raise InvalidEmailOrPasswordError("The email or password is incorrect.")

        if user.status in {UserStatus.SUSPENDED, UserStatus.DEACTIVATED}:
            self.audit_logger.record(
                event_type=AuthEventType.LOGIN_DENIED,
                outcome=AuthEventOutcome.BLOCKED,
                user_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"user_status": user.status.value},
            )
            await self.session.commit()
            raise UserAccessDeniedError("This account is not permitted to sign in.")

        if password_needs_rehash(user.password_hash):
            user.password_hash = hash_password(payload.password)

        user.last_login_at = now
        raw_refresh_token = generate_refresh_token()
        refresh_token_expires_at = now + timedelta(
            days=self.settings.refresh_token_expiry_days
        )
        refresh_session = RefreshSession(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh_token),
            status=SessionStatus.ACTIVE,
            expires_at=refresh_token_expires_at,
            device_id=payload.device_id,
            device_name=payload.device_name,
            platform=payload.platform,
            ip_address=ip_address,
            user_agent=user_agent,
            last_used_at=now,
        )
        self.refresh_session_repository.add(refresh_session)
        await self.session.flush()
        access_token, access_token_expires_at = create_access_token(
            user_id=user.id,
            session_id=refresh_session.id,
            settings=self.settings,
            now=now,
        )
        self.audit_logger.record(
            event_type=AuthEventType.LOGIN_SUCCEEDED,
            outcome=AuthEventOutcome.SUCCESS,
            user_id=user.id,
            session_id=refresh_session.id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"authentication_method": "password"},
        )
        await self.session.commit()
        return PasswordLoginData(
            user=self._build_user_data(user),
            tokens=TokenData(
                access_token=access_token,
                refresh_token=raw_refresh_token,
                access_token_expires_at=access_token_expires_at,
                refresh_token_expires_at=refresh_token_expires_at,
            ),
            must_change_password=user.must_change_password,
        )

    async def change_password(
        self,
        *,
        user_id: UUID,
        payload: ChangePasswordRequest,
        ip_address: str | None,
        user_agent: str | None,
    ) -> ChangePasswordData:
        """Change a password atomically and revoke every existing session."""

        user = await self.user_repository.get_by_id_for_update(user_id)
        if user is None:
            raise PasswordLoginNotAvailableError(
                "Password login is not available for this account."
            )
        if user.password_hash is None:
            raise PasswordLoginNotAvailableError(
                "Password login is not available for this account."
            )
        if not verify_password(payload.current_password, user.password_hash):
            raise CurrentPasswordIncorrectError("The current password is incorrect.")
        if verify_password(payload.new_password, user.password_hash):
            raise PasswordReuseNotAllowedError(
                "The new password must differ from the current password."
            )
        self._validate_new_password(payload.new_password)

        now = datetime.now(UTC)
        user.password_hash = hash_password(payload.new_password)
        user.must_change_password = False
        sessions_revoked = await self.refresh_session_repository.revoke_all_for_user(
            user_id=user.id,
            now=now,
        )
        self.audit_logger.record(
            event_type=AuthEventType.PASSWORD_CHANGED,
            outcome=AuthEventOutcome.SUCCESS,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"sessions_revoked": sessions_revoked},
        )
        await self.session.commit()
        return ChangePasswordData(sessions_revoked=sessions_revoked)

    async def _enforce_otp_request_limits(
        self,
        *,
        phone_number: str,
        requested_ip: str | None,
    ) -> None:
        """Apply phone-number and IP limits to OTP requests."""

        phone_result = await self.rate_limiter.consume(
            key=f"otp-request:phone:{phone_number}",
            limit=self.settings.otp_request_phone_limit,
            window_seconds=self.settings.otp_request_phone_window_seconds,
        )

        if not phone_result.allowed:
            raise AuthenticationRateLimitError(
                code="OTP_REQUEST_PHONE_RATE_LIMITED",
                message=(
                    "Too many verification codes were requested for this phone number."
                ),
                retry_after_seconds=phone_result.retry_after_seconds,
                limit=phone_result.limit,
            )

        if requested_ip is None:
            return

        ip_result = await self.rate_limiter.consume(
            key=f"otp-request:ip:{requested_ip}",
            limit=self.settings.otp_request_ip_limit,
            window_seconds=self.settings.otp_request_ip_window_seconds,
        )

        if not ip_result.allowed:
            raise AuthenticationRateLimitError(
                code="OTP_REQUEST_IP_RATE_LIMITED",
                message=(
                    "Too many verification codes were requested from this network."
                ),
                retry_after_seconds=ip_result.retry_after_seconds,
                limit=ip_result.limit,
            )

    async def _enforce_otp_verification_limits(
        self,
        *,
        challenge_id: UUID,
        ip_address: str | None,
    ) -> None:
        """Apply challenge and IP limits to OTP verification."""

        challenge_result = await self.rate_limiter.consume(
            key=f"otp-verify:challenge:{challenge_id}",
            limit=self.settings.otp_verify_challenge_limit,
            window_seconds=self.settings.otp_verify_challenge_window_seconds,
        )

        if not challenge_result.allowed:
            raise AuthenticationRateLimitError(
                code="OTP_VERIFY_CHALLENGE_RATE_LIMITED",
                message=("Too many verification attempts were made for this code."),
                retry_after_seconds=challenge_result.retry_after_seconds,
                limit=challenge_result.limit,
            )

        if ip_address is None:
            return

        ip_result = await self.rate_limiter.consume(
            key=f"otp-verify:ip:{ip_address}",
            limit=self.settings.otp_verify_ip_limit,
            window_seconds=self.settings.otp_verify_ip_window_seconds,
        )

        if not ip_result.allowed:
            raise AuthenticationRateLimitError(
                code="OTP_VERIFY_IP_RATE_LIMITED",
                message=("Too many verification attempts were made from this network."),
                retry_after_seconds=ip_result.retry_after_seconds,
                limit=ip_result.limit,
            )

    async def request_login_otp(
        self,
        *,
        raw_phone_number: str,
        requested_ip: str | None,
        user_agent: str | None,
    ) -> RequestOTPData:
        phone_number = normalize_phone_number(
            raw_phone_number,
            default_region=self.settings.default_phone_region,
            require_mobile=True,
        )
        channel = self.otp_delivery.channel_for(phone_number)

        await self._enforce_otp_request_limits(
            phone_number=phone_number,
            requested_ip=requested_ip,
        )

        now = datetime.now(UTC)

        latest_challenge = await self.otp_repository.get_latest_pending(
            phone_number=phone_number,
            purpose=OTPPurpose.LOGIN,
        )

        if latest_challenge is not None:
            resend_available_at = latest_challenge.created_at + timedelta(
                seconds=self.settings.otp_resend_cooldown_seconds
            )

            if now < resend_available_at:
                retry_after_seconds = max(
                    1,
                    int((resend_available_at - now).total_seconds()),
                )

                self.audit_logger.record(
                    event_type=AuthEventType.OTP_REQUEST_BLOCKED,
                    outcome=AuthEventOutcome.BLOCKED,
                    challenge_id=latest_challenge.id,
                    phone_number=phone_number,
                    ip_address=requested_ip,
                    user_agent=user_agent,
                    metadata={
                        "reason": "resend_cooldown",
                        "retry_after_seconds": retry_after_seconds,
                    },
                )

                await self.session.commit()

                raise OTPResendCooldownError(retry_after_seconds=retry_after_seconds)

        await self.otp_repository.expire_pending_challenges(
            phone_number=phone_number,
            purpose=OTPPurpose.LOGIN,
            now=now,
        )

        challenge_id = uuid4()
        otp_code = generate_numeric_otp(self.settings.otp_length)
        expires_at = now + timedelta(seconds=self.settings.otp_expiry_seconds)
        resend_available_at = now + timedelta(
            seconds=self.settings.otp_resend_cooldown_seconds
        )

        challenge = OTPChallenge(
            id=challenge_id,
            phone_number=phone_number,
            purpose=OTPPurpose.LOGIN,
            status=OTPStatus.PENDING,
            delivery_channel=channel,
            code_hash=hash_otp(
                challenge_id=challenge_id,
                phone_number=phone_number,
                otp_code=otp_code,
                secret=self.settings.otp_hash_secret,
            ),
            expires_at=expires_at,
            max_attempts=self.settings.otp_max_attempts,
            requested_ip=(str(requested_ip) if requested_ip is not None else None),
            user_agent=user_agent,
        )

        self.otp_repository.add(challenge)

        try:
            await self.session.flush()
        except IntegrityError as exc:
            # Another request for this number created a pending challenge
            # between our check and insert (one pending code per number).
            await self.session.rollback()
            raise OTPResendCooldownError(
                retry_after_seconds=self.settings.otp_resend_cooldown_seconds
            ) from exc

        self.audit_logger.record(
            event_type=AuthEventType.OTP_REQUESTED,
            outcome=AuthEventOutcome.SUCCESS,
            challenge_id=challenge.id,
            phone_number=phone_number,
            ip_address=requested_ip,
            user_agent=user_agent,
            metadata={
                "purpose": OTPPurpose.LOGIN.value,
                "expires_in_seconds": self.settings.otp_expiry_seconds,
                "channel": channel.value,
            },
        )

        await self.session.commit()
        await self.session.refresh(challenge)

        try:
            provider_message_id = await self.otp_delivery.send(
                channel=channel,
                phone_number=phone_number,
                otp_code=otp_code,
                expires_in_seconds=self.settings.otp_expiry_seconds,
            )
        except Exception as exc:
            retryable = await self._record_otp_delivery_failure(
                challenge=challenge,
                error=exc,
                requested_ip=requested_ip,
                user_agent=user_agent,
            )
            raise OTPDeliveryFailedError(channel=channel, retryable=retryable) from exc

        # Accepted by the provider. Whether it arrived is reported later
        # (WhatsApp status webhook); acceptance is not delivery.
        challenge.provider_message_id = provider_message_id
        challenge.delivery_status = OTPDeliveryStatus.ACCEPTED
        challenge.delivery_status_updated_at = datetime.now(UTC)
        await self.session.commit()

        return RequestOTPData(
            challenge_id=str(challenge.id),
            phone_number=challenge.phone_number,
            expires_at=challenge.expires_at,
            resend_available_at=resend_available_at,
            expires_in_seconds=self.settings.otp_expiry_seconds,
            delivery_channel=channel,
        )

    async def get_otp_delivery(self, *, challenge_id: UUID) -> OTPDeliveryData:
        """Return where a sign-in code is on its way to the user.

        Lets the app tell the user quickly when WhatsApp could not deliver
        the code. Reveals no phone number and nothing about code validity.
        """

        challenge = await self.otp_repository.get_by_id(challenge_id=challenge_id)
        if challenge is None or challenge.purpose is not OTPPurpose.LOGIN:
            raise OTPChallengeNotFoundError("The verification challenge was not found.")
        return OTPDeliveryData(
            challenge_id=challenge.id,
            delivery_channel=challenge.delivery_channel,
            delivery_status=challenge.delivery_status,
        )

    async def _record_otp_delivery_failure(
        self,
        *,
        challenge: OTPChallenge,
        error: Exception,
        requested_ip: str | None,
        user_agent: str | None,
    ) -> bool:
        """Retire an undelivered challenge so the user can request a new code.

        The challenge is expired rather than left pending, which would hold
        the user in the resend cooldown for a code that never arrived. Only
        the failure category is recorded; the code itself is never logged.
        Returns whether retrying the same channel could succeed.
        """

        provider_code: str | None = None
        if isinstance(error, TimeoutError):
            reason, retryable = "timeout", True
        elif isinstance(error, OTPDeliveryError):
            reason, retryable = error.reason, error.retryable
            provider_code = error.provider_code
        else:
            reason, retryable = f"unexpected_{type(error).__name__}", True

        challenge.status = OTPStatus.EXPIRED
        challenge.delivery_status = OTPDeliveryStatus.FAILED
        challenge.delivery_status_updated_at = datetime.now(UTC)
        challenge.delivery_error_code = (provider_code or reason)[:32]

        self.audit_logger.record(
            event_type=AuthEventType.OTP_DELIVERY_FAILED,
            outcome=AuthEventOutcome.FAILURE,
            challenge_id=challenge.id,
            phone_number=challenge.phone_number,
            ip_address=requested_ip,
            user_agent=user_agent,
            metadata={
                "reason": reason,
                "retryable": retryable,
                "channel": challenge.delivery_channel.value,
                "provider_code": provider_code,
            },
        )

        await self.session.commit()

        logger.warning(
            "OTP delivery failed for challenge %s (channel=%s, reason=%s, "
            "retryable=%s)",
            challenge.id,
            challenge.delivery_channel.value,
            reason,
            retryable,
        )
        return retryable

    async def verify_login_otp(
        self,
        *,
        payload: VerifyOTPRequest,
        ip_address: str | None,
        user_agent: str | None,
    ) -> VerifyOTPData:
        await self._enforce_otp_verification_limits(
            challenge_id=payload.challenge_id,
            ip_address=ip_address,
        )

        now = datetime.now(UTC)

        challenge = await self.otp_repository.get_by_id_for_update(
            challenge_id=payload.challenge_id
        )

        if challenge is None:
            raise OTPChallengeNotFoundError("The verification challenge was not found.")

        if challenge.purpose != OTPPurpose.LOGIN:
            raise OTPChallengeConsumedError(
                "This verification challenge cannot be used for login."
            )

        if challenge.status == OTPStatus.VERIFIED:
            raise OTPChallengeConsumedError(
                "This verification code has already been used."
            )

        if challenge.status == OTPStatus.EXPIRED:
            raise OTPChallengeExpiredError("The verification code has expired.")

        if challenge.status == OTPStatus.BLOCKED:
            raise OTPAttemptsExceededError(
                "Too many incorrect attempts. Request a new code."
            )

        if now >= challenge.expires_at:
            challenge.status = OTPStatus.EXPIRED

            self.audit_logger.record(
                event_type=AuthEventType.OTP_EXPIRED,
                outcome=AuthEventOutcome.FAILURE,
                challenge_id=challenge.id,
                phone_number=challenge.phone_number,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={
                    "purpose": challenge.purpose.value,
                },
            )

            await self.session.commit()

            raise OTPChallengeExpiredError("The verification code has expired.")

        if challenge.attempt_count >= challenge.max_attempts:
            challenge.status = OTPStatus.BLOCKED

            self.audit_logger.record(
                event_type=AuthEventType.OTP_ATTEMPTS_EXCEEDED,
                outcome=AuthEventOutcome.BLOCKED,
                challenge_id=challenge.id,
                phone_number=challenge.phone_number,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={
                    "attempt_count": challenge.attempt_count,
                    "max_attempts": challenge.max_attempts,
                },
            )

            await self.session.commit()

            raise OTPAttemptsExceededError(
                "Too many incorrect attempts. Request a new code."
            )

        is_valid = verify_otp_hash(
            challenge_id=challenge.id,
            phone_number=challenge.phone_number,
            otp_code=payload.code,
            secret=self.settings.otp_hash_secret,
            expected_hash=challenge.code_hash,
        )

        if not is_valid:
            challenge.attempt_count += 1

            attempts_remaining = max(
                0,
                challenge.max_attempts - challenge.attempt_count,
            )

            self.audit_logger.record(
                event_type=AuthEventType.OTP_VERIFICATION_FAILED,
                outcome=AuthEventOutcome.FAILURE,
                challenge_id=challenge.id,
                phone_number=challenge.phone_number,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={
                    "attempt_count": challenge.attempt_count,
                    "attempts_remaining": attempts_remaining,
                },
            )

            if attempts_remaining == 0:
                challenge.status = OTPStatus.BLOCKED

                self.audit_logger.record(
                    event_type=AuthEventType.OTP_ATTEMPTS_EXCEEDED,
                    outcome=AuthEventOutcome.BLOCKED,
                    challenge_id=challenge.id,
                    phone_number=challenge.phone_number,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    metadata={
                        "attempt_count": challenge.attempt_count,
                        "max_attempts": challenge.max_attempts,
                    },
                )

            await self.session.commit()

            if attempts_remaining == 0:
                raise OTPAttemptsExceededError(
                    "Too many incorrect attempts. Request a new code."
                )

            raise InvalidOTPError(attempts_remaining=attempts_remaining)

        user = await self.user_repository.get_by_phone_number(challenge.phone_number)

        is_new_user = user is None

        if user is None:
            user = User(
                phone_number=challenge.phone_number,
                status=UserStatus.ACTIVE,
                is_phone_verified=True,
                phone_verified_at=now,
                last_login_at=now,
            )

            self.user_repository.add(user)
            await self.session.flush()
        else:
            if user.status in {
                UserStatus.SUSPENDED,
                UserStatus.DEACTIVATED,
            }:
                challenge.status = OTPStatus.VERIFIED
                challenge.verified_at = now

                self.audit_logger.record(
                    event_type=AuthEventType.LOGIN_DENIED,
                    outcome=AuthEventOutcome.BLOCKED,
                    user_id=user.id,
                    challenge_id=challenge.id,
                    phone_number=user.phone_number,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    metadata={
                        "user_status": user.status.value,
                    },
                )

                await self.session.commit()

                raise UserAccessDeniedError("This account is not permitted to sign in.")

            user.status = UserStatus.ACTIVE
            user.is_phone_verified = True
            user.phone_verified_at = user.phone_verified_at or now
            user.last_login_at = now

        raw_refresh_token = generate_refresh_token()
        refresh_token_expires_at = now + timedelta(
            days=self.settings.refresh_token_expiry_days
        )

        refresh_session = RefreshSession(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh_token),
            status=SessionStatus.ACTIVE,
            expires_at=refresh_token_expires_at,
            device_id=payload.device_id,
            device_name=payload.device_name,
            platform=payload.platform,
            ip_address=ip_address,
            user_agent=user_agent,
            last_used_at=now,
        )

        self.refresh_session_repository.add(refresh_session)
        await self.session.flush()

        access_token, access_token_expires_at = create_access_token(
            user_id=user.id,
            session_id=refresh_session.id,
            settings=self.settings,
            now=now,
        )

        challenge.status = OTPStatus.VERIFIED
        challenge.verified_at = now

        self.audit_logger.record(
            event_type=AuthEventType.OTP_VERIFIED,
            outcome=AuthEventOutcome.SUCCESS,
            user_id=user.id,
            session_id=refresh_session.id,
            challenge_id=challenge.id,
            phone_number=user.phone_number,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        self.audit_logger.record(
            event_type=AuthEventType.LOGIN_SUCCEEDED,
            outcome=AuthEventOutcome.SUCCESS,
            user_id=user.id,
            session_id=refresh_session.id,
            challenge_id=challenge.id,
            phone_number=user.phone_number,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={
                "is_new_user": is_new_user,
                "platform": payload.platform,
                "device_name": payload.device_name,
            },
        )

        await self.session.commit()

        return VerifyOTPData(
            user=self._build_user_data(user),
            tokens=TokenData(
                access_token=access_token,
                refresh_token=raw_refresh_token,
                access_token_expires_at=access_token_expires_at,
                refresh_token_expires_at=refresh_token_expires_at,
            ),
            is_new_user=is_new_user,
            requires_account_setup=is_new_user,
        )

    async def refresh_tokens(
        self,
        *,
        payload: RefreshTokenRequest,
        ip_address: str | None,
        user_agent: str | None,
    ) -> RefreshTokenData:
        """Rotate a refresh token and issue a new token pair."""

        now = datetime.now(UTC)

        presented_token_hash = hash_refresh_token(payload.refresh_token)

        current_session = (
            await self.refresh_session_repository.get_by_token_hash_for_update(
                presented_token_hash
            )
        )

        if current_session is None:
            self.audit_logger.record(
                event_type=AuthEventType.TOKEN_REFRESH_FAILED,
                outcome=AuthEventOutcome.FAILURE,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={
                    "reason": "invalid_refresh_token",
                },
            )

            await self.session.commit()

            raise InvalidRefreshTokenError("The refresh token is invalid.")

        if current_session.status == SessionStatus.REVOKED:
            self.audit_logger.record(
                event_type=AuthEventType.TOKEN_REFRESH_FAILED,
                outcome=AuthEventOutcome.BLOCKED,
                user_id=current_session.user_id,
                session_id=current_session.id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={
                    "reason": "revoked_session_reuse",
                },
            )

            await self.session.commit()

            raise RefreshSessionRevokedError("The refresh session has been revoked.")

        if current_session.status == SessionStatus.EXPIRED:
            self.audit_logger.record(
                event_type=AuthEventType.TOKEN_REFRESH_FAILED,
                outcome=AuthEventOutcome.FAILURE,
                user_id=current_session.user_id,
                session_id=current_session.id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={
                    "reason": "session_expired",
                },
            )

            await self.session.commit()

            raise RefreshSessionExpiredError("The refresh session has expired.")

        if now >= current_session.expires_at:
            current_session.status = SessionStatus.EXPIRED

            self.audit_logger.record(
                event_type=AuthEventType.SESSION_EXPIRED,
                outcome=AuthEventOutcome.FAILURE,
                user_id=current_session.user_id,
                session_id=current_session.id,
                ip_address=ip_address,
                user_agent=user_agent,
            )

            self.audit_logger.record(
                event_type=AuthEventType.TOKEN_REFRESH_FAILED,
                outcome=AuthEventOutcome.FAILURE,
                user_id=current_session.user_id,
                session_id=current_session.id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={
                    "reason": "session_expired",
                },
            )

            await self.session.commit()

            raise RefreshSessionExpiredError("The refresh session has expired.")

        user = await self.user_repository.get_by_id(current_session.user_id)

        if user is None:
            current_session.status = SessionStatus.REVOKED
            current_session.revoked_at = now
            await self.session.commit()

            raise InvalidRefreshTokenError(
                "The account associated with this session no longer exists."
            )

        if user.status in {
            UserStatus.SUSPENDED,
            UserStatus.DEACTIVATED,
        }:
            current_session.status = SessionStatus.REVOKED
            current_session.revoked_at = now

            self.audit_logger.record(
                event_type=AuthEventType.TOKEN_REFRESH_FAILED,
                outcome=AuthEventOutcome.BLOCKED,
                user_id=user.id,
                session_id=current_session.id,
                phone_number=user.phone_number,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={
                    "reason": "user_access_denied",
                    "user_status": user.status.value,
                },
            )

            await self.session.commit()

            raise UserAccessDeniedError("This account is not permitted to sign in.")

        # Revoke the token that was just presented.
        current_session.status = SessionStatus.REVOKED
        current_session.revoked_at = now
        current_session.last_used_at = now

        raw_refresh_token = generate_refresh_token()
        refresh_token_expires_at = now + timedelta(
            days=self.settings.refresh_token_expiry_days
        )

        new_session = RefreshSession(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh_token),
            status=SessionStatus.ACTIVE,
            expires_at=refresh_token_expires_at,
            device_id=payload.device_id or current_session.device_id,
            device_name=payload.device_name or current_session.device_name,
            platform=payload.platform or current_session.platform,
            ip_address=ip_address,
            user_agent=user_agent,
            last_used_at=now,
        )

        self.refresh_session_repository.add(new_session)
        await self.session.flush()

        access_token, access_token_expires_at = create_access_token(
            user_id=user.id,
            session_id=new_session.id,
            settings=self.settings,
            now=now,
        )

        self.audit_logger.record(
            event_type=AuthEventType.TOKEN_REFRESHED,
            outcome=AuthEventOutcome.SUCCESS,
            user_id=user.id,
            session_id=new_session.id,
            phone_number=user.phone_number,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={
                "previous_session_id": str(current_session.id),
                "platform": new_session.platform,
                "device_name": new_session.device_name,
            },
        )

        await self.session.commit()

        return RefreshTokenData(
            tokens=TokenData(
                access_token=access_token,
                refresh_token=raw_refresh_token,
                access_token_expires_at=access_token_expires_at,
                refresh_token_expires_at=refresh_token_expires_at,
            ),
            must_change_password=user.must_change_password,
        )

    async def logout(
        self,
        *,
        refresh_token: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> None:
        """Revoke the refresh session associated with a token."""

        now = datetime.now(UTC)

        token_hash = hash_refresh_token(refresh_token)

        refresh_session = (
            await self.refresh_session_repository.get_by_token_hash_for_update(
                token_hash
            )
        )

        if refresh_session is None:
            # Logout remains idempotent.
            return

        if refresh_session.status == SessionStatus.ACTIVE:
            refresh_session.status = SessionStatus.REVOKED
            refresh_session.revoked_at = now
            refresh_session.last_used_at = now

            self.audit_logger.record(
                event_type=AuthEventType.LOGOUT,
                outcome=AuthEventOutcome.SUCCESS,
                user_id=refresh_session.user_id,
                session_id=refresh_session.id,
                ip_address=ip_address,
                user_agent=user_agent,
            )

            await self.session.commit()

    async def list_sessions(
        self,
        *,
        user_id: UUID,
        current_session_id: UUID,
    ) -> SessionListData:
        """Return active login sessions belonging to a user."""

        sessions = await self.refresh_session_repository.list_active_for_user(user_id)

        session_data = [
            SessionData(
                id=item.id,
                device_name=item.device_name,
                device_id=item.device_id,
                platform=item.platform,
                ip_address=item.ip_address,
                status=item.status.value,
                created_at=item.created_at,
                last_used_at=item.last_used_at,
                expires_at=item.expires_at,
                is_current=item.id == current_session_id,
            )
            for item in sessions
        ]

        return SessionListData(
            sessions=session_data,
            total=len(session_data),
        )

    async def revoke_session(
        self,
        *,
        user_id: UUID,
        current_session_id: UUID,
        target_session_id: UUID,
        ip_address: str | None,
        user_agent: str | None,
    ) -> None:
        """Revoke one of the user's other sessions."""

        if target_session_id == current_session_id:
            raise CurrentSessionRevocationError(
                "Use the logout endpoint to revoke the current session."
            )

        target_session = await self.refresh_session_repository.get_by_id_for_update(
            session_id=target_session_id,
            user_id=user_id,
        )

        if target_session is None:
            raise SessionNotFoundError("The requested session was not found.")

        if target_session.status != SessionStatus.ACTIVE:
            return

        now = datetime.now(UTC)

        target_session.status = SessionStatus.REVOKED
        target_session.revoked_at = now
        target_session.last_used_at = now

        self.audit_logger.record(
            event_type=AuthEventType.SESSION_REVOKED,
            outcome=AuthEventOutcome.SUCCESS,
            user_id=user_id,
            session_id=target_session.id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={
                "revoked_by_session_id": str(current_session_id),
                "device_name": target_session.device_name,
                "platform": target_session.platform,
            },
        )

        await self.session.commit()

    async def logout_all(
        self,
        *,
        user_id: UUID,
        current_session_id: UUID,
        keep_current_session: bool,
        ip_address: str | None,
        user_agent: str | None,
    ) -> LogoutAllData:
        """Revoke all active sessions belonging to a user."""

        now = datetime.now(UTC)

        excluded_session_id = current_session_id if keep_current_session else None

        revoked_sessions = await self.refresh_session_repository.revoke_all_for_user(
            user_id=user_id,
            now=now,
            exclude_session_id=excluded_session_id,
        )

        self.audit_logger.record(
            event_type=AuthEventType.LOGOUT_ALL,
            outcome=AuthEventOutcome.SUCCESS,
            user_id=user_id,
            session_id=current_session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={
                "revoked_sessions": revoked_sessions,
                "current_session_kept": keep_current_session,
            },
        )

        await self.session.commit()

        return LogoutAllData(
            revoked_sessions=revoked_sessions,
            current_session_kept=keep_current_session,
        )
