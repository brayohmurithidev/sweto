from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.database import models  # noqa: F401
from app.modules.auth.enums import UserRole, UserStatus
from app.modules.auth.models import User
from app.modules.gyms.enums import (
    GymOnboardingStep,
    GymStaffRole,
    GymStatus,
    GymVerificationDecision,
    GymVerificationDocumentType,
    GymVerificationStatus,
)
from app.modules.gyms.exceptions import (
    GymVerificationAccessDeniedError,
    GymVerificationAlreadyApprovedError,
    GymVerificationAlreadyPendingError,
    GymVerificationDocumentInvalidError,
    GymVerificationNotPendingError,
    GymVerificationRequirementsError,
    GymVerificationReviewInProgressError,
)
from app.modules.gyms.models import Gym, GymVerificationDocument, GymVerificationReview
from app.modules.gyms.schemas import (
    CreateGymVerificationDocumentRequest,
    GymVerificationReviewRequest,
)
from app.modules.gyms.service import GymService


def session_mock() -> Mock:
    session = Mock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


def gym(status: GymVerificationStatus = GymVerificationStatus.NOT_SUBMITTED) -> Gym:
    now = datetime.now(UTC)
    return Gym(
        id=uuid4(),
        name="FlexFit",
        slug=f"flexfit-{uuid4()}",
        status=GymStatus.DRAFT,
        verification_status=status,
        onboarding_step=GymOnboardingStep.VERIFICATION,
        onboarding_completed=False,
        is_listed=False,
        created_at=now,
        updated_at=now,
    )


def account(role: UserRole = UserRole.USER) -> User:
    now = datetime.now(UTC)
    return User(
        id=uuid4(),
        phone_number="+254712345678",
        role=role,
        status=UserStatus.ACTIVE,
        is_phone_verified=True,
        must_change_password=False,
        is_system_protected=role == UserRole.SUPER_ADMIN,
        created_at=now,
        updated_at=now,
    )


def document(
    gym_id: object,
    document_type: GymVerificationDocumentType,
) -> GymVerificationDocument:
    now = datetime.now(UTC)
    return GymVerificationDocument(
        id=uuid4(),
        gym_id=gym_id,
        document_type=document_type,
        document_name="Registration",
        storage_key="verification/registration.pdf",
        file_url=None,
        mime_type="application/pdf",
        file_size_bytes=100,
        uploaded_by_user_id=uuid4(),
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def service() -> GymService:
    return GymService(session=session_mock(), default_phone_region="KE")


@pytest.mark.parametrize(
    ("status", "expected_step", "expected_next", "expected_limited"),
    [
        (
            GymVerificationStatus.NOT_SUBMITTED,
            GymOnboardingStep.VERIFICATION,
            "verification",
            True,
        ),
        (
            GymVerificationStatus.PENDING,
            GymOnboardingStep.WAITING_FOR_VERIFICATION,
            None,
            True,
        ),
        (
            GymVerificationStatus.APPROVED,
            GymOnboardingStep.COMPLETED,
            "limited_dashboard",
            False,
        ),
        (
            GymVerificationStatus.REJECTED,
            GymOnboardingStep.VERIFICATION,
            "verification",
            True,
        ),
    ],
)
def test_onboarding_is_driven_by_verification_status(
    status: GymVerificationStatus,
    expected_step: GymOnboardingStep,
    expected_next: str | None,
    expected_limited: bool,
) -> None:
    current_gym = gym(status)
    current_gym.verification_rejection_reason = (
        "Replace the registration document."
        if status == GymVerificationStatus.REJECTED
        else None
    )

    onboarding = GymService._build_onboarding_data(current_gym)

    assert onboarding.onboarding_step == expected_step
    assert onboarding.next_step == expected_next
    assert onboarding.limited_access is expected_limited
    assert onboarding.onboarding_completed is (status == GymVerificationStatus.APPROVED)
    assert (
        onboarding.verification_rejection_reason
        == current_gym.verification_rejection_reason
    )


def payload(**overrides: object) -> CreateGymVerificationDocumentRequest:
    values: dict[str, object] = {
        "document_name": "Registration",
        "storage_key": "verification/registration.pdf",
        "file_url": None,
        "mime_type": "application/pdf",
        "file_size_bytes": 100,
    }
    values.update(overrides)
    return CreateGymVerificationDocumentRequest(**values)


@pytest.mark.asyncio
async def test_owner_registers_document_with_authenticated_uploader() -> None:
    current_gym = gym()
    current_user = account()
    item = document(current_gym.id, GymVerificationDocumentType.BUSINESS_REGISTRATION)
    verification_service = service()
    verification_service.staff_repository.get_user_membership = AsyncMock(
        return_value=SimpleNamespace(role=GymStaffRole.OWNER)
    )
    verification_service.gym_repository.get_by_id_for_update = AsyncMock(
        return_value=current_gym
    )
    verification_service.verification_repository.create_or_replace_document = AsyncMock(
        return_value=item
    )

    result = await verification_service.create_verification_document(
        user_id=current_user.id,
        gym_id=current_gym.id,
        document_type=GymVerificationDocumentType.BUSINESS_REGISTRATION,
        payload=payload(),
    )

    assert result.uploaded_by_user_id == item.uploaded_by_user_id
    repository = verification_service.verification_repository
    call_args = repository.create_or_replace_document.call_args
    kwargs = call_args.kwargs
    assert kwargs["user_id"] == current_user.id


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [GymStaffRole.MANAGER, GymStaffRole.OWNER])
async def test_owner_or_manager_can_register_document(role: GymStaffRole) -> None:
    current_gym = gym()
    verification_service = service()
    verification_service.staff_repository.get_user_membership = AsyncMock(
        return_value=SimpleNamespace(role=role)
    )
    verification_service.gym_repository.get_by_id_for_update = AsyncMock(
        return_value=current_gym
    )
    verification_service.verification_repository.create_or_replace_document = AsyncMock(
        return_value=document(
            current_gym.id, GymVerificationDocumentType.OWNER_IDENTIFICATION
        )
    )
    await verification_service.create_verification_document(
        user_id=uuid4(),
        gym_id=current_gym.id,
        document_type=GymVerificationDocumentType.OWNER_IDENTIFICATION,
        payload=payload(),
    )


@pytest.mark.asyncio
async def test_document_access_and_metadata_are_validated() -> None:
    current_gym = gym()
    verification_service = service()
    verification_service.staff_repository.get_user_membership = AsyncMock(
        return_value=None
    )
    with pytest.raises(GymVerificationAccessDeniedError):
        await verification_service.create_verification_document(
            user_id=uuid4(),
            gym_id=current_gym.id,
            document_type=GymVerificationDocumentType.BUSINESS_REGISTRATION,
            payload=payload(),
        )

    verification_service.staff_repository.get_user_membership = AsyncMock(
        return_value=SimpleNamespace(role=GymStaffRole.OWNER)
    )
    verification_service.gym_repository.get_by_id_for_update = AsyncMock(
        return_value=current_gym
    )
    with pytest.raises(GymVerificationDocumentInvalidError):
        await verification_service.create_verification_document(
            user_id=uuid4(),
            gym_id=current_gym.id,
            document_type=GymVerificationDocumentType.BUSINESS_REGISTRATION,
            payload=payload(mime_type="text/plain"),
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "error"),
    [
        (GymVerificationStatus.PENDING, GymVerificationReviewInProgressError),
        (GymVerificationStatus.APPROVED, GymVerificationAlreadyApprovedError),
    ],
)
async def test_documents_cannot_change_during_pending_or_after_approval(
    status: GymVerificationStatus, error: type[Exception]
) -> None:
    current_gym = gym(status)
    verification_service = service()
    verification_service.staff_repository.get_user_membership = AsyncMock(
        return_value=SimpleNamespace(role=GymStaffRole.OWNER)
    )
    verification_service.gym_repository.get_by_id_for_update = AsyncMock(
        return_value=current_gym
    )
    with pytest.raises(error):
        await verification_service.create_verification_document(
            user_id=uuid4(),
            gym_id=current_gym.id,
            document_type=GymVerificationDocumentType.BUSINESS_REGISTRATION,
            payload=payload(),
        )


@pytest.mark.asyncio
async def test_submission_requires_documents_then_sets_pending_without_activation() -> (
    None
):
    current_gym = gym()
    verification_service = service()
    verification_service.staff_repository.get_user_membership = AsyncMock(
        return_value=SimpleNamespace(role=GymStaffRole.OWNER)
    )
    verification_service.gym_repository.get_by_id_for_update = AsyncMock(
        return_value=current_gym
    )
    verification_service.verification_repository.list_documents = AsyncMock(
        return_value=[]
    )
    with pytest.raises(GymVerificationRequirementsError) as error:
        await verification_service.submit_verification(
            user_id=uuid4(), gym_id=current_gym.id
        )
    assert error.value.missing_document_types == [
        "business_registration",
        "owner_identification",
    ]

    docs = [
        document(current_gym.id, GymVerificationDocumentType.BUSINESS_REGISTRATION),
        document(current_gym.id, GymVerificationDocumentType.OWNER_IDENTIFICATION),
    ]
    verification_service.verification_repository.list_documents = AsyncMock(
        return_value=docs
    )
    verification_service.verification_repository.list_reviews = AsyncMock(
        return_value=[]
    )
    result = await verification_service.submit_verification(
        user_id=uuid4(), gym_id=current_gym.id
    )
    assert result.verification_status == GymVerificationStatus.PENDING
    assert current_gym.status == GymStatus.DRAFT
    assert current_gym.onboarding_completed is False


@pytest.mark.asyncio
async def test_duplicate_and_approved_submission_are_rejected() -> None:
    for status, error in [
        (GymVerificationStatus.PENDING, GymVerificationAlreadyPendingError),
        (GymVerificationStatus.APPROVED, GymVerificationAlreadyApprovedError),
    ]:
        current_gym = gym(status)
        verification_service = service()
        verification_service.staff_repository.get_user_membership = AsyncMock(
            return_value=SimpleNamespace(role=GymStaffRole.MANAGER)
        )
        verification_service.gym_repository.get_by_id_for_update = AsyncMock(
            return_value=current_gym
        )
        with pytest.raises(error):
            await verification_service.submit_verification(
                user_id=uuid4(), gym_id=current_gym.id
            )


@pytest.mark.asyncio
async def test_platform_admin_approval_completes_onboarding() -> None:
    current_gym = gym(GymVerificationStatus.PENDING)
    reviewer = account(UserRole.ADMIN)
    review = GymVerificationReview(
        id=uuid4(),
        gym_id=current_gym.id,
        reviewed_by_user_id=reviewer.id,
        decision=GymVerificationDecision.APPROVE,
        notes=None,
        rejection_reason=None,
        reviewed_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    verification_service = service()
    verification_service.gym_repository.get_by_id_for_update = AsyncMock(
        return_value=current_gym
    )
    verification_service.verification_repository.create_review = AsyncMock(
        return_value=review
    )
    verification_service.verification_repository.list_documents = AsyncMock(
        return_value=[]
    )
    verification_service.verification_repository.list_reviews = AsyncMock(
        return_value=[review]
    )
    result = await verification_service.review_verification(
        reviewer=reviewer,
        gym_id=current_gym.id,
        payload=GymVerificationReviewRequest(decision=GymVerificationDecision.APPROVE),
    )
    assert result.verification_status == GymVerificationStatus.APPROVED
    assert current_gym.status == GymStatus.ACTIVE
    assert current_gym.onboarding_step == GymOnboardingStep.COMPLETED
    assert current_gym.onboarding_completed is True


@pytest.mark.asyncio
async def test_rejection_and_resubmission_preserve_history() -> None:
    current_gym = gym(GymVerificationStatus.PENDING)
    reviewer = account(UserRole.SUPER_ADMIN)
    review = GymVerificationReview(
        id=uuid4(),
        gym_id=current_gym.id,
        reviewed_by_user_id=reviewer.id,
        decision=GymVerificationDecision.REJECT,
        notes="Upload a clearer registration certificate.",
        rejection_reason="Registration document is unreadable.",
        reviewed_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    verification_service = service()
    verification_service.gym_repository.get_by_id_for_update = AsyncMock(
        return_value=current_gym
    )
    verification_service.verification_repository.create_review = AsyncMock(
        return_value=review
    )
    docs = [
        document(current_gym.id, GymVerificationDocumentType.BUSINESS_REGISTRATION),
        document(current_gym.id, GymVerificationDocumentType.OWNER_IDENTIFICATION),
    ]
    verification_service.verification_repository.list_documents = AsyncMock(
        return_value=docs
    )
    verification_service.verification_repository.list_reviews = AsyncMock(
        return_value=[review]
    )
    await verification_service.review_verification(
        reviewer=reviewer,
        gym_id=current_gym.id,
        payload=GymVerificationReviewRequest(
            decision=GymVerificationDecision.REJECT,
            rejection_reason="Registration document is unreadable.",
        ),
    )
    assert current_gym.verification_status == GymVerificationStatus.REJECTED
    assert current_gym.status == GymStatus.DRAFT
    assert current_gym.onboarding_step == GymOnboardingStep.VERIFICATION

    verification_service.staff_repository.get_user_membership = AsyncMock(
        return_value=SimpleNamespace(role=GymStaffRole.OWNER)
    )
    result = await verification_service.submit_verification(
        user_id=uuid4(), gym_id=current_gym.id
    )
    assert result.verification_status == GymVerificationStatus.PENDING
    assert current_gym.verification_rejection_reason is None
    assert result.review_history[0].id == review.id


@pytest.mark.asyncio
async def test_only_platform_admins_can_review_and_only_pending_is_reviewable() -> None:
    current_gym = gym(GymVerificationStatus.PENDING)
    verification_service = service()
    with pytest.raises(GymVerificationAccessDeniedError):
        await verification_service.review_verification(
            reviewer=account(UserRole.USER),
            gym_id=current_gym.id,
            payload=GymVerificationReviewRequest(
                decision=GymVerificationDecision.APPROVE
            ),
        )

    verification_service.gym_repository.get_by_id_for_update = AsyncMock(
        return_value=gym(GymVerificationStatus.REJECTED)
    )
    with pytest.raises(GymVerificationNotPendingError):
        await verification_service.review_verification(
            reviewer=account(UserRole.ADMIN),
            gym_id=current_gym.id,
            payload=GymVerificationReviewRequest(
                decision=GymVerificationDecision.APPROVE
            ),
        )
