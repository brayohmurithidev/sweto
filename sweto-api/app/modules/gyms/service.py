from datetime import UTC, datetime, timedelta
from pathlib import PurePosixPath
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.audit import AuthAuditLogger
from app.modules.auth.enums import AuthEventOutcome, AuthEventType, UserRole
from app.modules.auth.models import User
from app.modules.auth.phone import normalize_phone_number
from app.modules.gyms.constants import (
    ALLOWED_GYM_PHOTO_MIME_TYPES,
    ALLOWED_GYM_VERIFICATION_MIME_TYPES,
    MAX_GYM_PHOTO_FILE_SIZE_BYTES,
    MAX_GYM_PHOTOS,
    MAX_GYM_VERIFICATION_FILE_SIZE_BYTES,
    REQUIRED_GYM_VERIFICATION_DOCUMENT_TYPES,
)
from app.modules.gyms.enums import (
    GymOnboardingStep,
    GymStaffRole,
    GymStaffStatus,
    GymStatus,
    GymVerificationDecision,
    GymVerificationDocumentType,
    GymVerificationStatus,
)
from app.modules.gyms.exceptions import (
    AmenityNotFoundError,
    GymAccessDeniedError,
    GymAlreadyExistsError,
    GymNotFoundError,
    GymPhotoLimitReachedError,
    GymPhotoUploadInvalidError,
    GymProfileIncompleteError,
    GymSlugConflictError,
    GymVerificationAccessDeniedError,
    GymVerificationAlreadyApprovedError,
    GymVerificationAlreadyPendingError,
    GymVerificationDocumentInvalidError,
    GymVerificationNotPendingError,
    GymVerificationRejectionReasonRequiredError,
    GymVerificationRequirementsError,
    GymVerificationReviewInProgressError,
)
from app.modules.gyms.models import (
    Amenity,
    Gym,
    GymDayPass,
    GymMembershipPlan,
    GymMembershipPlanBenefit,
    GymOperatingHours,
    GymPhoto,
    GymStaff,
    GymVerificationDocument,
    GymVerificationReview,
)
from app.modules.gyms.photo_upload import GymPhotoUploadPurpose
from app.modules.gyms.repository import (
    AmenityRepository,
    GymOperatingHoursRepository,
    GymPhotoRepository,
    GymPricingRepository,
    GymRepository,
    GymStaffRepository,
    GymVerificationRepository,
)
from app.modules.gyms.schemas import (
    AmenityData,
    CreateGymData,
    CreateGymRequest,
    CreateGymVerificationDocumentRequest,
    DevelopmentStorageUploadData,
    GymData,
    GymDayPassData,
    GymMembershipBenefitData,
    GymMembershipPlanData,
    GymOnboardingData,
    GymOperatingHoursData,
    GymPhotoData,
    GymPhotoDeleteData,
    GymPhotoListData,
    GymPhotoResponse,
    GymPhotoUploadCompletionData,
    GymPhotoUploadData,
    GymPhotoUploadRequest,
    GymPricingData,
    GymVerificationData,
    GymVerificationDocumentData,
    GymVerificationDownloadData,
    GymVerificationListData,
    GymVerificationReviewData,
    GymVerificationReviewRequest,
    GymVerificationSummaryData,
    GymVerificationUploadData,
    GymVerificationUploadRequest,
    UpdateGymAmenitiesData,
    UpdateGymAmenitiesRequest,
    UpdateGymBasicInformationData,
    UpdateGymBasicInformationRequest,
    UpdateGymBusinessDetailsData,
    UpdateGymBusinessDetailsRequest,
    UpdateGymLocationData,
    UpdateGymLocationRequest,
    UpdateGymOperatingHoursData,
    UpdateGymOperatingHoursRequest,
    UpdateGymPricingData,
    UpdateGymPricingRequest,
)
from app.modules.gyms.slug import slugify
from app.modules.profiles.enums import (
    AccountRole,
    OnboardingStatus,
)
from app.modules.profiles.models import (
    UserAccountRole,
    UserProfile,
)
from app.modules.profiles.repository import (
    UserAccountRoleRepository,
    UserProfileRepository,
)
from app.storage.enums import UploadPurpose, UploadStatus
from app.storage.exceptions import (
    StorageNotConfiguredError,
    StorageObjectNotFoundError,
    StorageObjectSizeMismatchError,
    StorageObjectTypeMismatchError,
    StorageUploadAlreadyCompletedError,
    StorageUploadExpiredError,
    StorageUploadFailedError,
    StorageUploadNotFoundError,
)
from app.storage.keys import (
    ALLOWED_EXTENSION_BY_MIME_TYPE,
    build_gym_photo_key,
    build_gym_verification_key,
)
from app.storage.models import GymPhotoUpload, StorageUpload
from app.storage.repository import GymPhotoUploadRepository, StorageUploadRepository
from app.storage.s3 import S3Storage


class GymService:
    """Application service for gym onboarding and management."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        default_phone_region: str,
        storage: S3Storage | None = None,
    ) -> None:
        self.session = session
        self.default_phone_region = default_phone_region

        self.amenity_repository = AmenityRepository(session)
        self.gym_repository = GymRepository(session)
        self.gym_photo_repository = GymPhotoRepository(session)
        self.operating_hours_repository = GymOperatingHoursRepository(session)
        self.pricing_repository = GymPricingRepository(session)
        self.staff_repository = GymStaffRepository(session)
        self.profile_repository = UserProfileRepository(session)
        self.role_repository = UserAccountRoleRepository(session)
        self.verification_repository = GymVerificationRepository(session)
        self.storage_upload_repository = StorageUploadRepository(session)
        self.gym_photo_upload_repository = GymPhotoUploadRepository(session)
        self.storage = storage
        self.audit_logger = AuthAuditLogger(session)

    async def create_gym(
        self,
        *,
        user: User,
        payload: CreateGymRequest,
    ) -> CreateGymData:
        existing_membership = await self.staff_repository.get_primary_owner_membership(
            user.id
        )

        if existing_membership is not None:
            raise GymAlreadyExistsError(
                "You already have a gym registered as primary owner."
            )

        slug = await self._generate_unique_slug(payload.name)

        phone_number = None

        if payload.phone_number is not None:
            phone_number = normalize_phone_number(
                payload.phone_number,
                default_region=self.default_phone_region,
            )

        gym = Gym(
            name=payload.name.strip(),
            slug=slug,
            description=(
                payload.description.strip() if payload.description is not None else None
            ),
            phone_number=phone_number,
            email=(str(payload.email) if payload.email is not None else None),
            status=GymStatus.DRAFT,
            verification_status=(GymVerificationStatus.NOT_SUBMITTED),
            onboarding_step=GymOnboardingStep.LOCATION,
            onboarding_completed=False,
            is_listed=False,
        )

        self.gym_repository.add(gym)
        await self.session.flush()

        membership = GymStaff(
            gym_id=gym.id,
            user_id=user.id,
            role=GymStaffRole.OWNER,
            status=GymStaffStatus.ACTIVE,
            is_primary_owner=True,
        )

        self.staff_repository.add(membership)

        await self._ensure_gym_owner_role(user_id=user.id)

        await self._advance_profile_onboarding(user_id=user.id)

        await self.session.commit()
        await self.session.refresh(gym)

        return CreateGymData(
            gym=self._build_gym_data(gym),
            onboarding=self._build_onboarding_data(gym),
        )

    async def get_current_gym(
        self,
        *,
        user_id: UUID,
    ) -> GymData:
        membership = await self.staff_repository.get_primary_owner_membership(user_id)

        if membership is None:
            raise GymNotFoundError("No gym is associated with this account.")

        gym = await self.gym_repository.get_by_id(membership.gym_id)

        if gym is None:
            raise GymNotFoundError("The associated gym could not be found.")

        return self._build_gym_data(gym)

    async def get_onboarding(
        self,
        *,
        user_id: UUID,
        gym_id: UUID,
    ) -> GymOnboardingData:
        membership = await self.staff_repository.get_user_membership(
            user_id=user_id,
            gym_id=gym_id,
        )

        if membership is None:
            raise GymAccessDeniedError("You do not have access to this gym.")

        gym = await self.gym_repository.get_by_id(gym_id)

        if gym is None:
            raise GymNotFoundError("The requested gym was not found.")

        return self._build_onboarding_data(gym)

    async def _generate_unique_slug(
        self,
        name: str,
    ) -> str:
        base_slug = slugify(name)

        if not await self.gym_repository.slug_exists(base_slug):
            return base_slug

        for suffix in range(2, 1001):
            candidate = f"{base_slug}-{suffix}"

            if not await self.gym_repository.slug_exists(candidate):
                return candidate

        raise GymSlugConflictError("A unique gym identifier could not be generated.")

    async def _ensure_gym_owner_role(
        self,
        *,
        user_id: UUID,
    ) -> None:
        role = await self.role_repository.get_by_user_and_role(
            user_id=user_id,
            role=AccountRole.GYM_OWNER,
        )

        await self.role_repository.clear_default_roles(user_id)

        if role is None:
            role = UserAccountRole(
                user_id=user_id,
                role=AccountRole.GYM_OWNER,
                is_active=True,
                is_default=True,
            )

            self.role_repository.add(role)
        else:
            role.is_active = True
            role.is_default = True

    async def _advance_profile_onboarding(
        self,
        *,
        user_id: UUID,
    ) -> None:
        profile = await self.profile_repository.get_by_user_id(user_id)

        if profile is None:
            profile = UserProfile(
                user_id=user_id,
            )

            self.profile_repository.add(profile)

        profile.onboarding_status = OnboardingStatus.GYM_SETUP_PENDING
        profile.onboarding_completed = False

    @staticmethod
    def _build_gym_data(
        gym: Gym,
    ) -> GymData:
        return GymData(
            id=gym.id,
            name=gym.name,
            slug=gym.slug,
            description=gym.description,
            phone_number=gym.phone_number,
            email=gym.email,
            legal_business_name=gym.legal_business_name,
            business_type=gym.business_type,
            registration_number=gym.registration_number,
            tax_number=gym.tax_number,
            contact_person_name=gym.contact_person_name,
            contact_person_phone=gym.contact_person_phone,
            address_line=gym.address_line,
            neighbourhood=gym.neighbourhood,
            city=gym.city,
            country_code=gym.country_code,
            latitude=gym.latitude,
            longitude=gym.longitude,
            logo_url=gym.logo_url,
            cover_photo_url=gym.cover_photo_url,
            status=gym.status,
            verification_status=gym.verification_status,
            onboarding_step=gym.onboarding_step,
            onboarding_completed=gym.onboarding_completed,
            is_listed=gym.is_listed,
            created_at=gym.created_at,
            updated_at=gym.updated_at,
        )

    @classmethod
    def _build_onboarding_data(
        cls,
        gym: Gym,
    ) -> GymOnboardingData:
        onboarding_step = gym.onboarding_step
        next_step: str | None = cls._resolve_next_step(onboarding_step)
        if gym.verification_status == GymVerificationStatus.PENDING:
            onboarding_step = GymOnboardingStep.WAITING_FOR_VERIFICATION
            next_step = None
        elif gym.verification_status == GymVerificationStatus.APPROVED:
            onboarding_step = GymOnboardingStep.COMPLETED
            next_step = cls._resolve_next_step(onboarding_step)
        elif gym.verification_status == GymVerificationStatus.REJECTED:
            onboarding_step = GymOnboardingStep.VERIFICATION
            next_step = GymOnboardingStep.VERIFICATION.value
        return GymOnboardingData(
            gym_id=gym.id,
            status=gym.status,
            verification_status=gym.verification_status,
            onboarding_step=onboarding_step,
            onboarding_completed=(
                gym.verification_status == GymVerificationStatus.APPROVED
            ),
            next_step=next_step,
            limited_access=(gym.verification_status != GymVerificationStatus.APPROVED),
            verification_rejection_reason=gym.verification_rejection_reason,
        )

    @staticmethod
    def _resolve_next_step(
        step: GymOnboardingStep,
    ) -> str | None:
        mapping = {
            GymOnboardingStep.BASIC_INFORMATION: ("basic_information"),
            GymOnboardingStep.LOCATION: "location",
            GymOnboardingStep.BUSINESS_DETAILS: ("business_details"),
            GymOnboardingStep.AMENITIES: "amenities",
            GymOnboardingStep.OPERATING_HOURS: ("operating_hours"),
            GymOnboardingStep.PRICING: "pricing",
            GymOnboardingStep.VERIFICATION: ("verification"),
            GymOnboardingStep.WAITING_FOR_VERIFICATION: None,
            GymOnboardingStep.COMPLETED: ("limited_dashboard"),
        }

        return mapping[step]

    async def update_basic_information(
        self,
        *,
        user_id: UUID,
        gym_id: UUID,
        payload: UpdateGymBasicInformationRequest,
    ) -> UpdateGymBasicInformationData:
        """Update registration details without advancing onboarding."""

        membership = await self.staff_repository.get_user_membership(
            user_id=user_id,
            gym_id=gym_id,
        )
        if membership is None:
            raise GymAccessDeniedError("You do not have access to this gym.")
        if membership.role not in {GymStaffRole.OWNER, GymStaffRole.MANAGER}:
            raise GymAccessDeniedError("You do not have permission to update this gym.")

        gym = await self.gym_repository.get_by_id_for_update(gym_id)
        if gym is None:
            raise GymNotFoundError("The requested gym was not found.")

        if "name" in payload.model_fields_set:
            assert payload.name is not None
            gym.name = payload.name.strip()
        if "phone_number" in payload.model_fields_set:
            gym.phone_number = (
                normalize_phone_number(
                    payload.phone_number,
                    default_region=self.default_phone_region,
                )
                if payload.phone_number is not None
                else None
            )
        if "email" in payload.model_fields_set:
            gym.email = str(payload.email) if payload.email is not None else None
        if "description" in payload.model_fields_set:
            gym.description = payload.description

        await self.session.commit()
        await self.session.refresh(gym)

        return UpdateGymBasicInformationData(
            gym=self._build_gym_data(gym),
            onboarding=self._build_onboarding_data(gym),
        )

    async def update_location(
        self,
        *,
        user_id: UUID,
        gym_id: UUID,
        payload: UpdateGymLocationRequest,
    ) -> UpdateGymLocationData:
        """Save gym location and advance the onboarding workflow."""

        membership = await self.staff_repository.get_user_membership(
            user_id=user_id,
            gym_id=gym_id,
        )

        if membership is None:
            raise GymAccessDeniedError("You do not have access to this gym.")

        if membership.role not in {
            GymStaffRole.OWNER,
            GymStaffRole.MANAGER,
        }:
            raise GymAccessDeniedError("You do not have permission to update this gym.")

        gym = await self.gym_repository.get_by_id_for_update(gym_id)

        if gym is None:
            raise GymNotFoundError("The requested gym was not found.")

        gym.address_line = payload.address_line.strip()
        gym.neighbourhood = payload.neighbourhood.strip()
        gym.city = payload.city.strip()
        gym.country_code = payload.country_code.upper()
        gym.latitude = payload.latitude
        gym.longitude = payload.longitude

        if gym.onboarding_step in {
            GymOnboardingStep.BASIC_INFORMATION,
            GymOnboardingStep.LOCATION,
        }:
            gym.onboarding_step = GymOnboardingStep.BUSINESS_DETAILS

        await self.session.commit()
        await self.session.refresh(gym)

        return UpdateGymLocationData(
            gym=self._build_gym_data(gym),
            onboarding=self._build_onboarding_data(gym),
        )

    async def update_business_details(
        self,
        *,
        user_id: UUID,
        gym_id: UUID,
        payload: UpdateGymBusinessDetailsRequest,
    ) -> UpdateGymBusinessDetailsData:
        """Save legal business details and advance onboarding."""

        membership = await self.staff_repository.get_user_membership(
            user_id=user_id,
            gym_id=gym_id,
        )

        if membership is None:
            raise GymAccessDeniedError("You do not have access to this gym.")

        if membership.role not in {
            GymStaffRole.OWNER,
            GymStaffRole.MANAGER,
        }:
            raise GymAccessDeniedError("You do not have permission to update this gym.")

        gym = await self.gym_repository.get_by_id_for_update(gym_id)

        if gym is None:
            raise GymNotFoundError("The requested gym was not found.")

        contact_phone = normalize_phone_number(
            payload.contact_person_phone,
            default_region=self.default_phone_region,
        )

        gym.legal_business_name = payload.legal_business_name.strip()
        gym.business_type = payload.business_type
        gym.registration_number = (
            payload.registration_number.strip().upper()
            if payload.registration_number is not None
            else None
        )
        gym.tax_number = (
            payload.tax_number.strip().upper()
            if payload.tax_number is not None
            else None
        )
        gym.contact_person_name = payload.contact_person_name.strip()
        gym.contact_person_phone = contact_phone

        if gym.onboarding_step in {
            GymOnboardingStep.BASIC_INFORMATION,
            GymOnboardingStep.LOCATION,
            GymOnboardingStep.BUSINESS_DETAILS,
        }:
            gym.onboarding_step = GymOnboardingStep.AMENITIES

        await self.session.commit()
        await self.session.refresh(gym)

        return UpdateGymBusinessDetailsData(
            gym=self._build_gym_data(gym),
            onboarding=self._build_onboarding_data(gym),
        )

    async def list_amenities(
        self,
    ) -> list[AmenityData]:
        """Return active amenities available for selection."""

        amenities = await self.amenity_repository.list_active()

        return [self._build_amenity_data(amenity) for amenity in amenities]

    async def list_gym_amenities(
        self, *, user_id: UUID, gym_id: UUID
    ) -> list[AmenityData]:
        membership = await self.staff_repository.get_user_membership(
            user_id=user_id, gym_id=gym_id
        )
        if membership is None:
            raise GymAccessDeniedError("You do not have access to this gym.")
        gym = await self.gym_repository.get_by_id(gym_id)
        if gym is None:
            raise GymNotFoundError("The requested gym was not found.")
        amenities = await self.amenity_repository.list_for_gym(gym_id)
        return [self._build_amenity_data(amenity) for amenity in amenities]

    async def update_amenities(
        self,
        *,
        user_id: UUID,
        gym_id: UUID,
        payload: UpdateGymAmenitiesRequest,
    ) -> UpdateGymAmenitiesData:
        """Replace selected amenities and advance onboarding."""

        membership = await self.staff_repository.get_user_membership(
            user_id=user_id,
            gym_id=gym_id,
        )

        if membership is None:
            raise GymAccessDeniedError("You do not have access to this gym.")

        if membership.role not in {
            GymStaffRole.OWNER,
            GymStaffRole.MANAGER,
        }:
            raise GymAccessDeniedError("You do not have permission to update this gym.")

        gym = await self.gym_repository.get_by_id_for_update(gym_id)

        if gym is None:
            raise GymNotFoundError("The requested gym was not found.")

        requested_ids = set(payload.amenity_ids)

        amenities = await self.amenity_repository.get_active_by_ids(requested_ids)

        found_ids = {amenity.id for amenity in amenities}

        missing_ids = requested_ids - found_ids

        if missing_ids:
            missing_values = ", ".join(sorted(str(value) for value in missing_ids))

            raise AmenityNotFoundError(
                f"Invalid or inactive amenity IDs: {missing_values}."
            )

        await self.amenity_repository.replace_gym_amenities(
            gym_id=gym.id,
            amenity_ids=requested_ids,
        )

        if gym.onboarding_step in {
            GymOnboardingStep.BASIC_INFORMATION,
            GymOnboardingStep.LOCATION,
            GymOnboardingStep.BUSINESS_DETAILS,
            GymOnboardingStep.AMENITIES,
        }:
            gym.onboarding_step = GymOnboardingStep.OPERATING_HOURS

        await self.session.commit()
        await self.session.refresh(gym)

        return UpdateGymAmenitiesData(
            gym_id=gym.id,
            amenities=[self._build_amenity_data(amenity) for amenity in amenities],
            onboarding=self._build_onboarding_data(gym),
        )

    @staticmethod
    def _build_amenity_data(
        amenity: Amenity,
    ) -> AmenityData:
        return AmenityData(
            id=amenity.id,
            name=amenity.name,
            slug=amenity.slug,
            description=amenity.description,
            icon=amenity.icon,
            display_order=amenity.display_order,
        )

    async def get_operating_hours(
        self,
        *,
        user_id: UUID,
        gym_id: UUID,
    ) -> list[GymOperatingHoursData]:
        """Return the current weekly gym schedule."""

        membership = await self.staff_repository.get_user_membership(
            user_id=user_id,
            gym_id=gym_id,
        )

        if membership is None:
            raise GymAccessDeniedError("You do not have access to this gym.")

        schedules = await self.operating_hours_repository.list_by_gym_id(gym_id)

        return [self._build_operating_hours_data(schedule) for schedule in schedules]

    async def update_operating_hours(
        self,
        *,
        user_id: UUID,
        gym_id: UUID,
        payload: UpdateGymOperatingHoursRequest,
    ) -> UpdateGymOperatingHoursData:
        """Replace weekly operating hours and advance onboarding."""

        membership = await self.staff_repository.get_user_membership(
            user_id=user_id,
            gym_id=gym_id,
        )

        if membership is None:
            raise GymAccessDeniedError("You do not have access to this gym.")

        if membership.role not in {
            GymStaffRole.OWNER,
            GymStaffRole.MANAGER,
        }:
            raise GymAccessDeniedError("You do not have permission to update this gym.")

        gym = await self.gym_repository.get_by_id_for_update(gym_id)

        if gym is None:
            raise GymNotFoundError("The requested gym was not found.")

        ordered_schedules = sorted(
            payload.operating_hours,
            key=lambda schedule: schedule.day_of_week,
        )

        await self.operating_hours_repository.replace_schedule(
            gym_id=gym.id,
            schedules=ordered_schedules,
        )

        if gym.onboarding_step in {
            GymOnboardingStep.BASIC_INFORMATION,
            GymOnboardingStep.LOCATION,
            GymOnboardingStep.BUSINESS_DETAILS,
            GymOnboardingStep.AMENITIES,
            GymOnboardingStep.OPERATING_HOURS,
        }:
            gym.onboarding_step = GymOnboardingStep.PRICING

        await self.session.flush()

        saved_schedules = await self.operating_hours_repository.list_by_gym_id(gym.id)

        await self.session.commit()
        await self.session.refresh(gym)

        return UpdateGymOperatingHoursData(
            gym_id=gym.id,
            operating_hours=[
                self._build_operating_hours_data(schedule)
                for schedule in saved_schedules
            ],
            onboarding=self._build_onboarding_data(gym),
        )

    @staticmethod
    def _build_operating_hours_data(
        schedule: GymOperatingHours,
    ) -> GymOperatingHoursData:
        return GymOperatingHoursData(
            id=schedule.id,
            day_of_week=schedule.day_of_week,
            is_closed=schedule.is_closed,
            is_24_hours=schedule.is_24_hours,
            opens_at=schedule.opens_at,
            closes_at=schedule.closes_at,
        )

    async def get_pricing(
        self,
        *,
        user_id: UUID,
        gym_id: UUID,
    ) -> GymPricingData:
        """Return the gym's current pricing options."""

        membership = await self.staff_repository.get_user_membership(
            user_id=user_id,
            gym_id=gym_id,
        )

        if membership is None:
            raise GymAccessDeniedError("You do not have access to this gym.")

        day_passes = await self.pricing_repository.list_day_passes(gym_id)

        membership_plans = await self.pricing_repository.list_membership_plans(gym_id)

        return GymPricingData(
            gym_id=gym_id,
            day_passes=[self._build_day_pass_data(item) for item in day_passes],
            membership_plans=[
                self._build_membership_plan_data(item) for item in membership_plans
            ],
        )

    async def update_pricing(
        self,
        *,
        user_id: UUID,
        gym_id: UUID,
        payload: UpdateGymPricingRequest,
    ) -> UpdateGymPricingData:
        """Replace gym pricing and advance onboarding."""

        membership = await self.staff_repository.get_user_membership(
            user_id=user_id,
            gym_id=gym_id,
        )

        if membership is None:
            raise GymAccessDeniedError("You do not have access to this gym.")

        if membership.role not in {
            GymStaffRole.OWNER,
            GymStaffRole.MANAGER,
        }:
            raise GymAccessDeniedError("You do not have permission to update this gym.")

        gym = await self.gym_repository.get_by_id_for_update(gym_id)

        if gym is None:
            raise GymNotFoundError("The requested gym was not found.")

        gym_id_value = gym.id

        await self.pricing_repository.replace_pricing(
            gym_id=gym_id_value,
            day_passes=payload.day_passes,
            membership_plans=payload.membership_plans,
        )

        if gym.onboarding_step in {
            GymOnboardingStep.BASIC_INFORMATION,
            GymOnboardingStep.LOCATION,
            GymOnboardingStep.BUSINESS_DETAILS,
            GymOnboardingStep.AMENITIES,
            GymOnboardingStep.OPERATING_HOURS,
            GymOnboardingStep.PRICING,
        }:
            gym.onboarding_step = GymOnboardingStep.VERIFICATION

        await self.session.commit()

        day_passes = await self.pricing_repository.list_day_passes(gym_id_value)

        membership_plans = await self.pricing_repository.list_membership_plans(
            gym_id_value
        )

        gym = await self.gym_repository.get_by_id(gym_id_value)

        if gym is None:
            raise GymNotFoundError("The requested gym was not found.")

        return UpdateGymPricingData(
            gym_id=gym_id_value,
            day_passes=[self._build_day_pass_data(item) for item in day_passes],
            membership_plans=[
                self._build_membership_plan_data(item) for item in membership_plans
            ],
            onboarding=self._build_onboarding_data(gym),
        )

    @staticmethod
    def _build_day_pass_data(
        item: GymDayPass,
    ) -> GymDayPassData:
        return GymDayPassData(
            id=item.id,
            name=item.name,
            description=item.description,
            amount=item.amount,
            currency=item.currency,
            validity_hours=item.validity_hours,
            is_active=item.is_active,
            display_order=item.display_order,
        )

    @staticmethod
    def _build_membership_benefit_data(
        item: GymMembershipPlanBenefit,
    ) -> GymMembershipBenefitData:
        return GymMembershipBenefitData(
            id=item.id,
            name=item.name,
            display_order=item.display_order,
        )

    @classmethod
    def _build_membership_plan_data(
        cls,
        item: GymMembershipPlan,
    ) -> GymMembershipPlanData:
        return GymMembershipPlanData(
            id=item.id,
            name=item.name,
            description=item.description,
            amount=item.amount,
            currency=item.currency,
            billing_period=item.billing_period,
            access_days=item.access_days,
            visit_limit=item.visit_limit,
            is_active=item.is_active,
            is_featured=item.is_featured,
            display_order=item.display_order,
            benefits=[
                cls._build_membership_benefit_data(benefit) for benefit in item.benefits
            ],
        )

    async def create_verification_document(
        self,
        *,
        user_id: UUID,
        gym_id: UUID,
        document_type: GymVerificationDocumentType,
        payload: CreateGymVerificationDocumentRequest,
    ) -> GymVerificationDocumentData:
        """Register or replace a verification document."""

        membership = await self.staff_repository.get_user_membership(
            user_id=user_id,
            gym_id=gym_id,
        )

        if membership is None:
            raise GymVerificationAccessDeniedError(
                "You do not have access to this gym verification."
            )

        if membership.role not in {
            GymStaffRole.OWNER,
            GymStaffRole.MANAGER,
        }:
            raise GymVerificationAccessDeniedError(
                "Only an owner or manager may update verification documents."
            )

        gym = await self.gym_repository.get_by_id_for_update(gym_id)

        if gym is None:
            raise GymNotFoundError("The requested gym was not found.")

        if gym.verification_status == GymVerificationStatus.PENDING:
            raise GymVerificationReviewInProgressError(
                "Verification documents cannot be changed "
                "while the gym is under review."
            )
        if gym.verification_status == GymVerificationStatus.APPROVED:
            raise GymVerificationAlreadyApprovedError(
                "Approved verification documents cannot be changed."
            )
        if payload.mime_type not in ALLOWED_GYM_VERIFICATION_MIME_TYPES:
            raise GymVerificationDocumentInvalidError(
                "The document MIME type is not supported."
            )
        if not 1 <= payload.file_size_bytes <= MAX_GYM_VERIFICATION_FILE_SIZE_BYTES:
            raise GymVerificationDocumentInvalidError(
                "The document file size must be between 1 byte and 10 MB."
            )

        document = await self.verification_repository.create_or_replace_document(
            gym_id=gym.id,
            user_id=user_id,
            document_type=document_type,
            payload=payload,
        )

        self.audit_logger.record(
            event_type=AuthEventType.GYM_VERIFICATION_DOCUMENT_REGISTERED,
            outcome=AuthEventOutcome.SUCCESS,
            user_id=user_id,
            metadata={"gym_id": str(gym.id), "document_type": document_type.value},
        )

        await self.session.commit()
        await self.session.refresh(document)

        return self._build_verification_document_data(document)

    async def initiate_verification_upload(
        self,
        *,
        user_id: UUID,
        gym_id: UUID,
        document_type: GymVerificationDocumentType,
        payload: GymVerificationUploadRequest,
    ) -> GymVerificationUploadData:
        """Create an upload intent and a private, short-lived S3 PUT URL."""

        gym = await self._require_verification_manager(
            user_id=user_id, gym_id=gym_id, lock=True
        )
        self._validate_upload_metadata(
            payload.filename, payload.mime_type, payload.file_size_bytes
        )
        storage = self._require_storage()
        upload_id = uuid4()
        key = build_gym_verification_key(
            gym_id=gym.id,
            document_type=document_type,
            upload_id=upload_id,
            mime_type=payload.mime_type,
        )
        presigned = await storage.create_upload_url(
            key=key, mime_type=payload.mime_type
        )
        upload = StorageUpload(
            id=upload_id,
            bucket=storage.bucket,
            storage_key=key,
            purpose=UploadPurpose.GYM_VERIFICATION_DOCUMENT,
            owner_user_id=user_id,
            gym_id=gym.id,
            document_type=document_type,
            original_filename=payload.filename,
            declared_mime_type=payload.mime_type,
            declared_size_bytes=payload.file_size_bytes,
            status=UploadStatus.PENDING,
            expires_at=datetime.now(UTC) + timedelta(minutes=15),
        )
        self.storage_upload_repository.add(upload)
        self.audit_logger.record(
            event_type=AuthEventType.STORAGE_UPLOAD_INITIATED,
            outcome=AuthEventOutcome.SUCCESS,
            user_id=user_id,
            metadata={
                "upload_id": str(upload_id),
                "gym_id": str(gym.id),
                "document_type": document_type.value,
                "storage_key": key,
                "declared_size": payload.file_size_bytes,
            },
        )
        await self.session.commit()
        return GymVerificationUploadData(
            upload_id=upload_id,
            upload_url=presigned.url,
            required_headers={"Content-Type": payload.mime_type},
            expires_at=presigned.expires_at,
            storage_key=key,
        )

    async def initiate_gym_photo_upload(
        self,
        *,
        user_id: UUID,
        gym_id: UUID,
        payload: GymPhotoUploadRequest,
    ) -> GymPhotoUploadData:
        membership = await self.staff_repository.get_user_membership(
            user_id=user_id, gym_id=gym_id
        )
        if membership is None or membership.role not in {
            GymStaffRole.OWNER,
            GymStaffRole.MANAGER,
        }:
            raise GymAccessDeniedError("You do not have permission to update this gym.")
        gym = await self.gym_repository.get_by_id_for_update(gym_id)
        if gym is None:
            raise GymNotFoundError("The requested gym was not found.")
        filename = PurePosixPath(payload.filename.replace("\\", "/")).name
        if not filename or filename in {".", ".."}:
            raise GymPhotoUploadInvalidError("The photo filename is invalid.")
        if payload.mime_type not in ALLOWED_GYM_PHOTO_MIME_TYPES:
            raise GymPhotoUploadInvalidError("The photo type is not supported.")
        if payload.file_size > MAX_GYM_PHOTO_FILE_SIZE_BYTES:
            raise GymPhotoUploadInvalidError("The photo is too large.")
        completed = await self.gym_photo_repository.count_for_gym(gym_id)
        pending = await self.gym_photo_upload_repository.count_active_pending(
            gym_id, datetime.now(UTC)
        )
        if completed + pending >= MAX_GYM_PHOTOS:
            raise GymPhotoLimitReachedError("The gym photo limit has been reached.")
        storage = self._require_storage()
        upload_id = uuid4()
        key = build_gym_photo_key(
            gym_id=gym_id, upload_id=upload_id, mime_type=payload.mime_type
        )
        presigned = await storage.create_upload_url(
            key=key, mime_type=payload.mime_type
        )
        upload = GymPhotoUpload(
            id=upload_id,
            gym_id=gym_id,
            owner_user_id=user_id,
            purpose=GymPhotoUploadPurpose.GYM_PHOTO,
            storage_key=key,
            original_filename=filename,
            declared_mime_type=payload.mime_type,
            declared_size_bytes=payload.file_size,
            status=UploadStatus.PENDING,
            expires_at=presigned.expires_at,
        )
        self.gym_photo_upload_repository.add(upload)
        await self.session.commit()
        return GymPhotoUploadData(
            upload_id=upload_id,
            upload_url=presigned.url,
            storage_key=key,
            expires_at=presigned.expires_at,
        )

    async def complete_gym_photo_upload(
        self,
        *,
        user_id: UUID,
        gym_id: UUID,
        upload_id: UUID,
    ) -> GymPhotoUploadCompletionData:
        membership = await self.staff_repository.get_user_membership(
            user_id=user_id, gym_id=gym_id
        )
        if membership is None or membership.role not in {
            GymStaffRole.OWNER,
            GymStaffRole.MANAGER,
        }:
            raise GymAccessDeniedError("You do not have permission to update this gym.")
        gym = await self.gym_repository.get_by_id_for_update(gym_id)
        if gym is None:
            raise GymNotFoundError("The requested gym was not found.")
        upload = await self.gym_photo_upload_repository.get_for_update(upload_id)
        if upload is None or upload.gym_id != gym_id:
            raise StorageUploadNotFoundError("The upload intent was not found.")
        if upload.purpose != GymPhotoUploadPurpose.GYM_PHOTO:
            raise StorageUploadNotFoundError("The upload intent was not found.")
        if upload.status == UploadStatus.COMPLETED:
            existing = await self.gym_photo_repository.get_by_storage_key(
                upload.storage_key
            )
            if existing is None:
                raise StorageUploadAlreadyCompletedError(
                    "The upload has already been completed."
                )
            return GymPhotoUploadCompletionData(
                photo=self._build_gym_photo_data(existing),
                upload_id=upload.id,
                status=upload.status.value,
                completed_at=upload.completed_at,
            )
        if upload.status != UploadStatus.PENDING:
            raise StorageUploadFailedError("This upload can no longer be completed.")
        if upload.expires_at < datetime.now(UTC):
            upload.status = UploadStatus.EXPIRED
            await self.session.commit()
            raise StorageUploadExpiredError("This upload intent has expired.")

        metadata = await self._require_storage().head_object(key=upload.storage_key)
        actual_type = metadata.content_type.split(";", 1)[0].strip().lower()
        if metadata.content_length != upload.declared_size_bytes:
            raise StorageUploadFailedError("The uploaded object size does not match.")
        if not actual_type or actual_type != upload.declared_mime_type.lower():
            raise StorageUploadFailedError("The uploaded object type does not match.")
        if metadata.content_length <= 0:
            raise StorageUploadFailedError("The uploaded object metadata is invalid.")

        if await self.gym_photo_repository.count_for_gym(gym_id) >= MAX_GYM_PHOTOS:
            raise GymPhotoLimitReachedError("The gym photo limit has been reached.")
        order = await self.gym_photo_repository.next_display_order(gym_id)
        is_cover = order == 0
        photo = GymPhoto(
            gym_id=gym_id,
            storage_key=upload.storage_key,
            original_filename=upload.original_filename,
            mime_type=upload.declared_mime_type,
            file_size=upload.declared_size_bytes,
            display_order=order,
            is_cover=is_cover,
        )
        self.gym_photo_repository.add(photo)
        if is_cover:
            gym.cover_photo_url = upload.storage_key
        upload.status = UploadStatus.COMPLETED
        upload.completed_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(photo)
        return GymPhotoUploadCompletionData(
            photo=self._build_gym_photo_data(photo),
            upload_id=upload.id,
            status=upload.status.value,
            completed_at=upload.completed_at,
        )

    async def list_gym_photos(self, *, user_id: UUID, gym_id: UUID) -> GymPhotoListData:
        membership = await self.staff_repository.get_user_membership(
            user_id=user_id, gym_id=gym_id
        )
        if membership is None or membership.role not in {
            GymStaffRole.OWNER,
            GymStaffRole.MANAGER,
        }:
            raise GymAccessDeniedError("You do not have permission to view this gym.")
        gym = await self.gym_repository.get_by_id(gym_id)
        if gym is None:
            raise GymNotFoundError("The requested gym was not found.")
        storage = self._require_storage()
        photos = await self.gym_photo_repository.list_for_gym(gym_id)
        responses: list[GymPhotoResponse] = []
        for photo in photos:
            signed = await storage.create_download_url(key=photo.storage_key)
            responses.append(
                GymPhotoResponse(
                    id=photo.id,
                    gym_id=photo.gym_id,
                    url=signed.url,
                    original_filename=photo.original_filename,
                    mime_type=photo.mime_type,
                    file_size=photo.file_size,
                    display_order=photo.display_order,
                    is_cover=photo.is_cover,
                    created_at=photo.created_at,
                )
            )
        return GymPhotoListData(photos=responses)

    async def delete_gym_photo(
        self, *, user_id: UUID, gym_id: UUID, photo_id: UUID
    ) -> GymPhotoDeleteData:
        membership = await self.staff_repository.get_user_membership(
            user_id=user_id, gym_id=gym_id
        )
        if membership is None or membership.role not in {
            GymStaffRole.OWNER,
            GymStaffRole.MANAGER,
        }:
            raise GymAccessDeniedError("You do not have permission to update this gym.")
        gym = await self.gym_repository.get_by_id_for_update(gym_id)
        if gym is None:
            raise GymNotFoundError("The requested gym was not found.")
        photo = await self.gym_photo_repository.get_for_update(photo_id)
        if photo is None or photo.gym_id != gym_id:
            raise GymNotFoundError("The requested gym photo was not found.")

        try:
            await self._require_storage().delete_object(key=photo.storage_key)
        except StorageObjectNotFoundError:
            # Deletion is idempotent for an object that has already disappeared.
            pass

        was_cover = photo.is_cover
        await self.gym_photo_repository.delete(photo)
        replacement_id: UUID | None = None
        if was_cover:
            replacement = await self.gym_photo_repository.get_next_cover(
                gym_id, excluding_id=photo_id
            )
            if replacement is None:
                gym.cover_photo_url = None
            else:
                replacement.is_cover = True
                gym.cover_photo_url = replacement.storage_key
                replacement_id = replacement.id
        await self.session.commit()
        return GymPhotoDeleteData(
            deleted_photo_id=photo_id,
            cover_photo_id=replacement_id,
            cover_photo_url=gym.cover_photo_url,
        )

    @staticmethod
    def _build_gym_photo_data(photo: GymPhoto) -> GymPhotoData:
        return GymPhotoData(
            id=photo.id,
            gym_id=photo.gym_id,
            storage_key=photo.storage_key,
            original_filename=photo.original_filename,
            mime_type=photo.mime_type,
            file_size=photo.file_size,
            display_order=photo.display_order,
            is_cover=photo.is_cover,
            created_at=photo.created_at,
            updated_at=photo.updated_at,
        )

    async def complete_verification_upload(
        self,
        *,
        user_id: UUID,
        gym_id: UUID,
        document_type: GymVerificationDocumentType,
        upload_id: UUID,
    ) -> GymVerificationDocumentData:
        storage = self._require_storage()
        upload = await self.storage_upload_repository.get_for_update(upload_id)
        if upload is None:
            raise StorageUploadNotFoundError("The upload intent was not found.")
        if upload.gym_id != gym_id or upload.document_type != document_type:
            raise StorageUploadNotFoundError("The upload intent was not found.")
        await self._require_verification_manager(
            user_id=user_id, gym_id=gym_id, lock=True
        )
        if upload.status == UploadStatus.COMPLETED:
            document = await self.verification_repository.get_document_by_type(
                gym_id=gym_id, document_type=document_type
            )
            if document is None:
                raise StorageUploadAlreadyCompletedError(
                    "The upload is already completed."
                )
            return self._build_verification_document_data(document)
        if upload.status != UploadStatus.PENDING:
            raise StorageUploadFailedError("This upload can no longer be completed.")
        if upload.expires_at < datetime.now(UTC):
            upload.status = UploadStatus.EXPIRED
            await self.session.commit()
            raise StorageUploadExpiredError("This upload intent has expired.")
        try:
            metadata = await storage.head_object(key=upload.storage_key)
            if metadata.content_length != upload.declared_size_bytes:
                raise StorageObjectSizeMismatchError(
                    "The uploaded object size does not match."
                )
            if metadata.content_type != upload.declared_mime_type:
                raise StorageObjectTypeMismatchError(
                    "The uploaded object type does not match."
                )
            self._validate_upload_metadata(
                upload.original_filename, metadata.content_type, metadata.content_length
            )
        except (
            StorageObjectNotFoundError,
            StorageObjectSizeMismatchError,
            StorageObjectTypeMismatchError,
            StorageUploadFailedError,
            GymVerificationDocumentInvalidError,
        ):
            upload.status = UploadStatus.FAILED
            try:
                await storage.delete_object(key=upload.storage_key)
            except Exception:
                pass
            await self.session.commit()
            raise
        (
            document,
            old_key,
        ) = await self.verification_repository.create_or_replace_document_from_storage(
            gym_id=gym_id,
            user_id=user_id,
            document_type=document_type,
            document_name=upload.original_filename,
            bucket=storage.bucket,
            storage_key=upload.storage_key,
            mime_type=metadata.content_type,
            file_size_bytes=metadata.content_length,
            etag=metadata.etag,
        )
        upload.status = UploadStatus.COMPLETED
        upload.etag = metadata.etag
        upload.verified_mime_type = metadata.content_type
        upload.verified_size_bytes = metadata.content_length
        upload.completed_at = datetime.now(UTC)
        self.audit_logger.record(
            event_type=AuthEventType.STORAGE_UPLOAD_COMPLETED,
            outcome=AuthEventOutcome.SUCCESS,
            user_id=user_id,
            metadata={
                "upload_id": str(upload.id),
                "gym_id": str(gym_id),
                "document_type": document_type.value,
                "storage_key": upload.storage_key,
                "verified_size": metadata.content_length,
            },
        )
        await self.session.commit()
        await self.session.refresh(document)
        if old_key and old_key != upload.storage_key:
            try:
                await storage.delete_object(key=old_key)
            except Exception:
                pass
        return self._build_verification_document_data(document)

    async def get_verification_download(
        self, *, user: User, gym_id: UUID, document_type: GymVerificationDocumentType
    ) -> GymVerificationDownloadData:
        await self.get_verification(user=user, gym_id=gym_id)
        document = await self.verification_repository.get_document_by_type(
            gym_id=gym_id, document_type=document_type
        )
        if document is None:
            from app.modules.gyms.exceptions import GymVerificationDocumentNotFoundError

            raise GymVerificationDocumentNotFoundError(
                "The verification document was not found."
            )
        storage = self._require_storage()
        if document.storage_bucket != storage.bucket:
            raise StorageUploadFailedError(
                "The document storage location is unavailable."
            )
        download = await storage.create_download_url(key=document.storage_key)
        self.audit_logger.record(
            event_type=AuthEventType.VERIFICATION_DOCUMENT_DOWNLOAD_REQUESTED,
            outcome=AuthEventOutcome.SUCCESS,
            user_id=user.id,
            metadata={
                "gym_id": str(gym_id),
                "document_type": document_type.value,
                "storage_key": document.storage_key,
            },
        )
        await self.session.commit()
        return GymVerificationDownloadData(
            download_url=download.url, expires_at=download.expires_at
        )

    async def get_development_upload_data(
        self, upload_id: UUID
    ) -> DevelopmentStorageUploadData:
        upload = await self.storage_upload_repository.get(upload_id)
        if upload is None:
            raise StorageUploadNotFoundError("The upload intent was not found.")
        return DevelopmentStorageUploadData(
            upload_id=upload.id,
            status=upload.status.value,
            storage_bucket=upload.bucket,
            storage_key=upload.storage_key,
            original_filename=upload.original_filename,
            declared_mime_type=upload.declared_mime_type,
            declared_size_bytes=upload.declared_size_bytes,
            verified_mime_type=upload.verified_mime_type,
            verified_size_bytes=upload.verified_size_bytes,
            etag=upload.etag,
            created_at=upload.created_at,
            completed_at=upload.completed_at,
        )

    async def fail_verification_upload(self, upload_id: UUID) -> None:
        """Mark a pending transport failure without registering a document."""

        upload = await self.storage_upload_repository.get_for_update(upload_id)
        if upload is None or upload.status != UploadStatus.PENDING:
            return
        upload.status = UploadStatus.FAILED
        storage = self._require_storage()
        try:
            await storage.delete_object(key=upload.storage_key)
        except Exception:
            pass
        await self.session.commit()

    def _require_storage(self) -> S3Storage:
        if self.storage is None:
            raise StorageNotConfiguredError("Private S3 uploads are not configured.")
        return self.storage

    @staticmethod
    def _validate_upload_metadata(filename: str, mime_type: str, size: int) -> None:
        if not filename.strip() or mime_type not in ALLOWED_EXTENSION_BY_MIME_TYPE:
            raise GymVerificationDocumentInvalidError(
                "The document metadata is invalid."
            )
        if not 1 <= size <= MAX_GYM_VERIFICATION_FILE_SIZE_BYTES:
            raise GymVerificationDocumentInvalidError(
                "The document file size is invalid."
            )

    async def _require_verification_manager(
        self, *, user_id: UUID, gym_id: UUID, lock: bool
    ) -> Gym:
        membership = await self.staff_repository.get_user_membership(
            user_id=user_id, gym_id=gym_id
        )
        if membership is None or membership.role not in {
            GymStaffRole.OWNER,
            GymStaffRole.MANAGER,
        }:
            raise GymVerificationAccessDeniedError(
                "Only an owner or manager may manage verification documents."
            )
        gym = await (
            self.gym_repository.get_by_id_for_update(gym_id)
            if lock
            else self.gym_repository.get_by_id(gym_id)
        )
        if gym is None:
            raise GymNotFoundError("The requested gym was not found.")
        if gym.verification_status == GymVerificationStatus.PENDING:
            raise GymVerificationReviewInProgressError(
                "Verification documents cannot be changed "
                "while the gym is under review."
            )
        if gym.verification_status == GymVerificationStatus.APPROVED:
            raise GymVerificationAlreadyApprovedError(
                "Approved verification documents cannot be changed."
            )
        return gym

    async def get_verification(
        self,
        *,
        user: User,
        gym_id: UUID,
    ) -> GymVerificationData:
        """Return verification status and uploaded documents."""

        membership = await self.staff_repository.get_user_membership(
            user_id=user.id,
            gym_id=gym_id,
        )

        is_platform_reviewer = user.role in {UserRole.ADMIN, UserRole.SUPER_ADMIN}
        is_owner_or_manager = membership is not None and membership.role in {
            GymStaffRole.OWNER,
            GymStaffRole.MANAGER,
        }
        if not is_platform_reviewer and not is_owner_or_manager:
            raise GymVerificationAccessDeniedError(
                "You do not have access to this gym verification."
            )

        gym = await self.gym_repository.get_by_id(gym_id)

        if gym is None:
            raise GymNotFoundError("The requested gym was not found.")

        return await self._build_verification_data(gym)

    async def submit_verification(
        self,
        *,
        user_id: UUID,
        gym_id: UUID,
    ) -> GymVerificationData:
        """Submit the gym for administrative verification."""

        membership = await self.staff_repository.get_user_membership(
            user_id=user_id,
            gym_id=gym_id,
        )

        if membership is None:
            raise GymVerificationAccessDeniedError(
                "You do not have access to this gym."
            )

        if membership.role not in {
            GymStaffRole.OWNER,
            GymStaffRole.MANAGER,
        }:
            raise GymVerificationAccessDeniedError(
                "You do not have permission to submit this gym."
            )

        gym = await self.gym_repository.get_by_id_for_update(gym_id)

        if gym is None:
            raise GymNotFoundError("The requested gym was not found.")

        if gym.verification_status == GymVerificationStatus.PENDING:
            raise GymVerificationAlreadyPendingError(
                "This gym is already under review."
            )

        if gym.verification_status == GymVerificationStatus.APPROVED:
            raise GymVerificationAlreadyApprovedError(
                "This gym has already been approved."
            )

        # Every profile step (location, business details, amenities, hours,
        # pricing) must be finished before review; a rejected gym returns to
        # the verification step, so resubmission is allowed.
        if gym.onboarding_step != GymOnboardingStep.VERIFICATION:
            raise GymProfileIncompleteError(
                self._resolve_next_step(gym.onboarding_step) or "verification"
            )

        documents = await self.verification_repository.list_documents(gym.id)

        submitted_document_types = {
            document.document_type for document in documents if document.is_active
        }

        missing_document_types = (
            REQUIRED_GYM_VERIFICATION_DOCUMENT_TYPES - submitted_document_types
        )

        if missing_document_types:
            raise GymVerificationRequirementsError(
                sorted(item.value for item in missing_document_types)
            )

        now = datetime.now(UTC)

        gym.verification_status = GymVerificationStatus.PENDING
        gym.verification_submitted_at = now
        gym.verification_reviewed_at = None
        gym.verification_rejection_reason = None
        gym.onboarding_step = GymOnboardingStep.WAITING_FOR_VERIFICATION
        gym.onboarding_completed = False

        self.audit_logger.record(
            event_type=AuthEventType.GYM_VERIFICATION_SUBMITTED,
            outcome=AuthEventOutcome.SUCCESS,
            user_id=user_id,
            metadata={"gym_id": str(gym.id)},
        )

        await self.session.commit()
        await self.session.refresh(gym)

        return await self._build_verification_data(gym)

    async def review_verification(
        self,
        *,
        reviewer: User,
        gym_id: UUID,
        payload: GymVerificationReviewRequest,
    ) -> GymVerificationData:
        """Approve or reject a gym verification submission."""

        if reviewer.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            raise GymVerificationAccessDeniedError(
                "Only platform administrators can review gym verification."
            )

        gym = await self.gym_repository.get_by_id_for_update(gym_id)

        if gym is None:
            raise GymNotFoundError("The requested gym was not found.")

        if gym.verification_status != GymVerificationStatus.PENDING:
            raise GymVerificationNotPendingError(
                "Only pending verification submissions can be reviewed."
            )

        if (
            payload.decision == GymVerificationDecision.REJECT
            and not payload.rejection_reason
        ):
            raise GymVerificationRejectionReasonRequiredError(
                "A rejection reason is required."
            )

        now = datetime.now(UTC)

        review = await self.verification_repository.create_review(
            gym_id=gym.id,
            reviewer_user_id=reviewer.id,
            decision=payload.decision,
            notes=payload.notes,
            rejection_reason=payload.rejection_reason,
        )
        await self.session.flush()

        if payload.decision == GymVerificationDecision.APPROVE:
            gym.verification_status = GymVerificationStatus.APPROVED
            gym.status = GymStatus.ACTIVE
            gym.onboarding_step = GymOnboardingStep.COMPLETED
            gym.onboarding_completed = True
            gym.verification_rejection_reason = None
            # Approval is what makes a gym discoverable to members.
            gym.is_listed = True
            event_type = AuthEventType.GYM_VERIFICATION_APPROVED
        else:
            gym.verification_status = GymVerificationStatus.REJECTED
            gym.status = GymStatus.DRAFT
            gym.onboarding_step = GymOnboardingStep.VERIFICATION
            gym.onboarding_completed = False
            gym.is_listed = False
            gym.verification_rejection_reason = payload.rejection_reason
            event_type = AuthEventType.GYM_VERIFICATION_REJECTED

        gym.verification_reviewed_at = now

        self.audit_logger.record(
            event_type=event_type,
            outcome=AuthEventOutcome.SUCCESS,
            user_id=reviewer.id,
            metadata={
                "gym_id": str(gym.id),
                "decision": payload.decision.value,
                "review_id": str(review.id),
            },
        )

        await self.session.commit()
        await self.session.refresh(gym)
        return await self._build_verification_data(gym)

    async def list_verifications(
        self,
        *,
        reviewer: User,
        status: GymVerificationStatus,
        limit: int,
        offset: int,
    ) -> GymVerificationListData:
        if reviewer.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            raise GymVerificationAccessDeniedError(
                "Only platform administrators can list gym verification submissions."
            )
        gyms, total = await self.verification_repository.list_gyms_by_status(
            status=status, limit=limit, offset=offset
        )
        summaries: list[GymVerificationSummaryData] = []
        for gym in gyms:
            documents = await self.verification_repository.list_documents(gym.id)
            present = {document.document_type for document in documents}
            missing = sorted(
                REQUIRED_GYM_VERIFICATION_DOCUMENT_TYPES - present,
                key=lambda item: item.value,
            )
            summaries.append(
                GymVerificationSummaryData(
                    gym_id=gym.id,
                    gym_name=gym.name,
                    verification_status=gym.verification_status,
                    verification_submitted_at=gym.verification_submitted_at,
                    verification_reviewed_at=gym.verification_reviewed_at,
                    missing_required_document_types=missing,
                )
            )
        return GymVerificationListData(
            gyms=summaries, total=total, limit=limit, offset=offset
        )

    async def _build_verification_data(self, gym: Gym) -> GymVerificationData:
        documents = await self.verification_repository.list_documents(gym.id)
        reviews = await self.verification_repository.list_reviews(gym.id)
        present = {document.document_type for document in documents}
        return GymVerificationData(
            gym_id=gym.id,
            verification_status=gym.verification_status,
            verification_submitted_at=gym.verification_submitted_at,
            verification_reviewed_at=gym.verification_reviewed_at,
            verification_rejection_reason=gym.verification_rejection_reason,
            required_document_types=sorted(
                REQUIRED_GYM_VERIFICATION_DOCUMENT_TYPES,
                key=lambda item: item.value,
            ),
            missing_required_document_types=sorted(
                REQUIRED_GYM_VERIFICATION_DOCUMENT_TYPES - present,
                key=lambda item: item.value,
            ),
            documents=[
                self._build_verification_document_data(item) for item in documents
            ],
            review_history=[self._build_review_data(item) for item in reviews],
            onboarding=self._build_onboarding_data(gym),
        )

    @staticmethod
    def _build_review_data(review: GymVerificationReview) -> GymVerificationReviewData:
        return GymVerificationReviewData(
            id=review.id,
            gym_id=review.gym_id,
            decision=review.decision,
            notes=review.notes,
            rejection_reason=review.rejection_reason,
            reviewed_by_user_id=review.reviewed_by_user_id,
            reviewed_at=review.reviewed_at,
        )

    @staticmethod
    def _build_verification_document_data(
        document: GymVerificationDocument,
    ) -> GymVerificationDocumentData:
        return GymVerificationDocumentData(
            id=document.id,
            document_type=document.document_type,
            document_name=document.document_name,
            storage_bucket=document.storage_bucket,
            storage_key=document.storage_key,
            mime_type=document.mime_type,
            file_size_bytes=document.file_size_bytes,
            etag=document.etag,
            is_active=document.is_active,
            uploaded_by_user_id=(document.uploaded_by_user_id),
            created_at=document.created_at,
            updated_at=document.updated_at,
        )
