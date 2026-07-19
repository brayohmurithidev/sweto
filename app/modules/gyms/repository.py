from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.gyms.enums import (
    GymStaffRole,
    GymStaffStatus,
    GymVerificationDecision,
    GymVerificationDocumentType,
    GymVerificationStatus,
)
from app.modules.gyms.models import (
    Amenity,
    Gym,
    GymAmenity,
    GymDayPass,
    GymMembershipPlan,
    GymMembershipPlanBenefit,
    GymOperatingHours,
    GymPhoto,
    GymStaff,
    GymVerificationDocument,
    GymVerificationReview,
)
from app.modules.gyms.schemas import (
    CreateGymVerificationDocumentRequest,
    GymDayPassInput,
    GymMembershipPlanInput,
    GymOperatingHoursInput,
)


class GymRepository:
    """Database operations for gyms."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(
        self,
        gym_id: UUID,
    ) -> Gym | None:
        statement = select(Gym).where(Gym.id == gym_id)

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def slug_exists(
        self,
        slug: str,
    ) -> bool:
        statement = select(Gym.id).where(Gym.slug == slug)

        result = await self.session.execute(statement)

        return result.scalar_one_or_none() is not None

    def add(self, gym: Gym) -> None:
        self.session.add(gym)

    async def get_by_id_for_update(
        self,
        gym_id: UUID,
    ) -> Gym | None:
        """Lock and return a gym for an update transaction."""

        statement = select(Gym).where(Gym.id == gym_id).with_for_update()

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()


class GymPhotoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def add(self, photo: GymPhoto) -> None:
        self.session.add(photo)

    async def get_by_id(self, photo_id: UUID) -> GymPhoto | None:
        result = await self.session.execute(
            select(GymPhoto).where(GymPhoto.id == photo_id)
        )
        return result.scalar_one_or_none()

    async def get_by_storage_key(self, storage_key: str) -> GymPhoto | None:
        result = await self.session.execute(
            select(GymPhoto).where(GymPhoto.storage_key == storage_key)
        )
        return result.scalar_one_or_none()

    async def list_for_gym(self, gym_id: UUID) -> list[GymPhoto]:
        result = await self.session.execute(
            select(GymPhoto)
            .where(GymPhoto.gym_id == gym_id)
            .order_by(GymPhoto.display_order, GymPhoto.created_at, GymPhoto.id)
        )
        return list(result.scalars())

    async def count_for_gym(self, gym_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(GymPhoto).where(GymPhoto.gym_id == gym_id)
        )
        return int(result.scalar_one())

    async def get_cover(self, gym_id: UUID) -> GymPhoto | None:
        result = await self.session.execute(
            select(GymPhoto).where(
                GymPhoto.gym_id == gym_id, GymPhoto.is_cover.is_(True)
            )
        )
        return result.scalar_one_or_none()

    async def next_display_order(self, gym_id: UUID) -> int:
        result = await self.session.execute(
            select(func.coalesce(func.max(GymPhoto.display_order), -1) + 1).where(
                GymPhoto.gym_id == gym_id
            )
        )
        return int(result.scalar_one())

    async def get_for_update(self, photo_id: UUID) -> GymPhoto | None:
        result = await self.session.execute(
            select(GymPhoto).where(GymPhoto.id == photo_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_next_cover(self, gym_id: UUID, excluding_id: UUID) -> GymPhoto | None:
        result = await self.session.execute(
            select(GymPhoto)
            .where(GymPhoto.gym_id == gym_id, GymPhoto.id != excluding_id)
            .order_by(GymPhoto.display_order, GymPhoto.created_at, GymPhoto.id)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def delete(self, photo: GymPhoto) -> None:
        await self.session.delete(photo)


class GymStaffRepository:
    """Database operations for gym staff relationships."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_primary_owner_membership(
        self,
        user_id: UUID,
    ) -> GymStaff | None:
        statement = select(GymStaff).where(
            GymStaff.user_id == user_id,
            GymStaff.role == GymStaffRole.OWNER,
            GymStaff.status == GymStaffStatus.ACTIVE,
            GymStaff.is_primary_owner.is_(True),
        )

        result = await self.session.execute(statement)

        return result.scalars().first()

    async def get_user_membership(
        self,
        *,
        user_id: UUID,
        gym_id: UUID,
    ) -> GymStaff | None:
        statement = select(GymStaff).where(
            GymStaff.user_id == user_id,
            GymStaff.gym_id == gym_id,
            GymStaff.status == GymStaffStatus.ACTIVE,
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    def add(self, membership: GymStaff) -> None:
        self.session.add(membership)


class AmenityRepository:
    """Database operations for amenities."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_active(self) -> Sequence[Amenity]:
        statement = (
            select(Amenity)
            .where(Amenity.is_active.is_(True))
            .order_by(
                Amenity.display_order.asc(),
                Amenity.name.asc(),
            )
        )

        result = await self.session.execute(statement)

        return result.scalars().all()

    async def get_active_by_ids(
        self,
        amenity_ids: set[UUID],
    ) -> Sequence[Amenity]:
        if not amenity_ids:
            return []

        statement = (
            select(Amenity)
            .where(
                Amenity.id.in_(amenity_ids),
                Amenity.is_active.is_(True),
            )
            .order_by(
                Amenity.display_order.asc(),
                Amenity.name.asc(),
            )
        )

        result = await self.session.execute(statement)

        return result.scalars().all()

    async def list_for_gym(self, gym_id: UUID) -> Sequence[Amenity]:
        statement = (
            select(Amenity)
            .join(GymAmenity, GymAmenity.amenity_id == Amenity.id)
            .where(GymAmenity.gym_id == gym_id)
            .order_by(Amenity.display_order.asc(), Amenity.name.asc())
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def replace_gym_amenities(
        self,
        *,
        gym_id: UUID,
        amenity_ids: set[UUID],
    ) -> None:
        await self.session.execute(
            delete(GymAmenity).where(GymAmenity.gym_id == gym_id)
        )

        self.session.add_all(
            [
                GymAmenity(
                    gym_id=gym_id,
                    amenity_id=amenity_id,
                )
                for amenity_id in amenity_ids
            ]
        )


class GymOperatingHoursRepository:
    """Database operations for gym operating hours."""

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def list_by_gym_id(
        self,
        gym_id: UUID,
    ) -> Sequence[GymOperatingHours]:
        statement = (
            select(GymOperatingHours)
            .where(GymOperatingHours.gym_id == gym_id)
            .order_by(GymOperatingHours.day_of_week.asc())
        )

        result = await self.session.execute(statement)

        return result.scalars().all()

    async def replace_schedule(
        self,
        *,
        gym_id: UUID,
        schedules: list[GymOperatingHoursInput],
    ) -> None:
        await self.session.execute(
            delete(GymOperatingHours).where(GymOperatingHours.gym_id == gym_id)
        )

        self.session.add_all(
            [
                GymOperatingHours(
                    gym_id=gym_id,
                    day_of_week=schedule.day_of_week,
                    is_closed=schedule.is_closed,
                    is_24_hours=schedule.is_24_hours,
                    opens_at=schedule.opens_at,
                    closes_at=schedule.closes_at,
                )
                for schedule in schedules
            ]
        )


class GymPricingRepository:
    """Database operations for gym pricing."""

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def list_day_passes(
        self,
        gym_id: UUID,
    ) -> Sequence[GymDayPass]:
        statement = (
            select(GymDayPass)
            .where(GymDayPass.gym_id == gym_id)
            .order_by(
                GymDayPass.display_order.asc(),
                GymDayPass.name.asc(),
            )
        )

        result = await self.session.execute(statement)

        return result.scalars().all()

    async def list_membership_plans(
        self,
        gym_id: UUID,
    ) -> Sequence[GymMembershipPlan]:
        statement = (
            select(GymMembershipPlan)
            .options(selectinload(GymMembershipPlan.benefits))
            .where(GymMembershipPlan.gym_id == gym_id)
            .order_by(
                GymMembershipPlan.display_order.asc(),
                GymMembershipPlan.name.asc(),
            )
        )

        result = await self.session.execute(statement)

        return result.scalars().unique().all()

    async def replace_pricing(
        self,
        *,
        gym_id: UUID,
        day_passes: list[GymDayPassInput],
        membership_plans: list[GymMembershipPlanInput],
    ) -> None:
        await self.session.execute(
            delete(GymDayPass).where(GymDayPass.gym_id == gym_id)
        )

        await self.session.execute(
            delete(GymMembershipPlan).where(GymMembershipPlan.gym_id == gym_id)
        )

        self.session.add_all(
            [
                GymDayPass(
                    gym_id=gym_id,
                    name=item.name,
                    description=item.description,
                    amount=item.amount,
                    currency=item.currency,
                    validity_hours=item.validity_hours,
                    is_active=item.is_active,
                    display_order=item.display_order,
                )
                for item in day_passes
            ]
        )

        for item in membership_plans:
            plan = GymMembershipPlan(
                gym_id=gym_id,
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
            )

            plan.benefits = [
                GymMembershipPlanBenefit(
                    name=benefit.name,
                    display_order=benefit.display_order,
                )
                for benefit in item.benefits
            ]

            self.session.add(plan)


class GymVerificationRepository:
    """Database operations for gym verification."""

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def list_documents(
        self,
        gym_id: UUID,
    ) -> Sequence[GymVerificationDocument]:
        statement = (
            select(GymVerificationDocument)
            .where(
                GymVerificationDocument.gym_id == gym_id,
                GymVerificationDocument.is_active.is_(True),
            )
            .order_by(GymVerificationDocument.document_type.asc())
        )

        result = await self.session.execute(statement)

        return result.scalars().all()

    async def get_document_by_type(
        self,
        *,
        gym_id: UUID,
        document_type: GymVerificationDocumentType,
    ) -> GymVerificationDocument | None:
        statement = select(GymVerificationDocument).where(
            GymVerificationDocument.gym_id == gym_id,
            GymVerificationDocument.document_type == document_type,
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def create_or_replace_document(
        self,
        *,
        gym_id: UUID,
        user_id: UUID,
        document_type: GymVerificationDocumentType,
        payload: CreateGymVerificationDocumentRequest,
    ) -> GymVerificationDocument:
        document = await self.get_document_by_type(
            gym_id=gym_id,
            document_type=document_type,
        )

        if document is None:
            document = GymVerificationDocument(
                gym_id=gym_id,
                uploaded_by_user_id=user_id,
                document_type=document_type,
                document_name=payload.document_name,
                storage_key=payload.storage_key,
                file_url=payload.file_url,
                mime_type=payload.mime_type,
                file_size_bytes=payload.file_size_bytes,
                is_active=True,
            )

            self.session.add(document)

            return document

        document.document_name = payload.document_name
        document.storage_key = payload.storage_key
        document.file_url = payload.file_url
        document.mime_type = payload.mime_type
        document.file_size_bytes = payload.file_size_bytes
        document.uploaded_by_user_id = user_id
        document.is_active = True

        return document

    async def create_or_replace_document_from_storage(
        self,
        *,
        gym_id: UUID,
        user_id: UUID,
        document_type: GymVerificationDocumentType,
        document_name: str,
        bucket: str,
        storage_key: str,
        mime_type: str,
        file_size_bytes: int,
        etag: str | None,
    ) -> tuple[GymVerificationDocument, str | None]:
        document = await self.get_document_by_type(
            gym_id=gym_id, document_type=document_type
        )
        old_key = document.storage_key if document is not None else None
        if document is None:
            document = GymVerificationDocument(
                gym_id=gym_id,
                uploaded_by_user_id=user_id,
                document_type=document_type,
                document_name=document_name,
                storage_bucket=bucket,
                storage_key=storage_key,
                mime_type=mime_type,
                file_size_bytes=file_size_bytes,
                etag=etag,
                is_active=True,
            )
            self.session.add(document)
        else:
            document.document_name = document_name
            document.storage_bucket = bucket
            document.storage_key = storage_key
            document.file_url = None
            document.mime_type = mime_type
            document.file_size_bytes = file_size_bytes
            document.etag = etag
            document.uploaded_by_user_id = user_id
            document.is_active = True
        return document, old_key

    async def get_document(
        self,
        *,
        gym_id: UUID,
        document_id: UUID,
    ) -> GymVerificationDocument | None:
        statement = select(GymVerificationDocument).where(
            GymVerificationDocument.id == document_id,
            GymVerificationDocument.gym_id == gym_id,
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def create_review(
        self,
        *,
        gym_id: UUID,
        reviewer_user_id: UUID,
        decision: GymVerificationDecision,
        notes: str | None,
        rejection_reason: str | None,
    ) -> GymVerificationReview:
        review = GymVerificationReview(
            gym_id=gym_id,
            reviewed_by_user_id=reviewer_user_id,
            decision=decision,
            notes=notes,
            rejection_reason=rejection_reason,
        )

        self.session.add(review)

        return review

    async def list_reviews(self, gym_id: UUID) -> Sequence[GymVerificationReview]:
        statement = (
            select(GymVerificationReview)
            .where(GymVerificationReview.gym_id == gym_id)
            .order_by(GymVerificationReview.reviewed_at.asc())
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def list_gyms_by_status(
        self, *, status: GymVerificationStatus, limit: int, offset: int
    ) -> tuple[list[Gym], int]:
        statement = select(Gym).where(Gym.verification_status == status)
        items_result = await self.session.execute(
            statement.order_by(Gym.verification_submitted_at.desc().nullslast())
            .limit(limit)
            .offset(offset)
        )
        total_result = await self.session.execute(
            select(func.count())
            .select_from(Gym)
            .where(Gym.verification_status == status)
        )
        return list(items_result.scalars().all()), int(total_result.scalar_one())
