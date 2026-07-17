from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.database.session import get_db_session
from app.modules.auth.dependencies import CurrentUser
from app.modules.gyms.enums import GymVerificationDocumentType
from app.modules.gyms.schemas import (
    AmenityData,
    CreateGymData,
    CreateGymRequest,
    GymData,
    GymOnboardingData,
    GymOperatingHoursData,
    GymPricingData,
    GymVerificationData,
    GymVerificationDocumentData,
    GymVerificationDownloadData,
    GymVerificationUploadData,
    GymVerificationUploadRequest,
    UpdateGymAmenitiesData,
    UpdateGymAmenitiesRequest,
    UpdateGymBusinessDetailsData,
    UpdateGymBusinessDetailsRequest,
    UpdateGymLocationData,
    UpdateGymLocationRequest,
    UpdateGymOperatingHoursData,
    UpdateGymOperatingHoursRequest,
    UpdateGymPricingData,
    UpdateGymPricingRequest,
)
from app.modules.gyms.service import GymService
from app.shared.responses import APIResponse
from app.storage.s3 import S3Storage

router = APIRouter(
    prefix="/gyms",
    tags=["Gyms"],
)


DatabaseSession = Annotated[
    AsyncSession,
    Depends(get_db_session),
]

ApplicationSettings = Annotated[
    Settings,
    Depends(get_settings),
]


@router.post(
    "",
    response_model=APIResponse[CreateGymData],
    status_code=status.HTTP_201_CREATED,
)
async def create_gym(
    payload: CreateGymRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
    settings: ApplicationSettings,
) -> APIResponse[CreateGymData]:
    """Register a gym and assign the current user as owner."""

    service = GymService(
        session=session,
        default_phone_region=settings.default_phone_region,
    )

    data = await service.create_gym(
        user=current_user,
        payload=payload,
    )

    return APIResponse(data=data)


@router.get(
    "/current",
    response_model=APIResponse[GymData],
)
async def get_current_gym(
    current_user: CurrentUser,
    session: DatabaseSession,
    settings: ApplicationSettings,
) -> APIResponse[GymData]:
    """Return the current primary-owner gym."""

    service = GymService(
        session=session,
        default_phone_region=settings.default_phone_region,
    )

    data = await service.get_current_gym(
        user_id=current_user.id,
    )

    return APIResponse(data=data)


@router.get(
    "/amenities",
    response_model=APIResponse[list[AmenityData]],
)
async def list_amenities(
    session: DatabaseSession,
    settings: ApplicationSettings,
) -> APIResponse[list[AmenityData]]:
    """Return active amenities available during onboarding."""

    service = GymService(
        session=session,
        default_phone_region=settings.default_phone_region,
    )

    data = await service.list_amenities()

    return APIResponse(data=data)


@router.get(
    "/{gym_id}/onboarding",
    response_model=APIResponse[GymOnboardingData],
)
async def get_gym_onboarding(
    gym_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
    settings: ApplicationSettings,
) -> APIResponse[GymOnboardingData]:
    """Return onboarding progress for an accessible gym."""

    service = GymService(
        session=session,
        default_phone_region=settings.default_phone_region,
    )

    data = await service.get_onboarding(
        user_id=current_user.id,
        gym_id=gym_id,
    )

    return APIResponse(data=data)


@router.patch(
    "/{gym_id}/location",
    response_model=APIResponse[UpdateGymLocationData],
)
async def update_gym_location(
    gym_id: UUID,
    payload: UpdateGymLocationRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
    settings: ApplicationSettings,
) -> APIResponse[UpdateGymLocationData]:
    """Save the gym location and advance onboarding."""

    service = GymService(
        session=session,
        default_phone_region=settings.default_phone_region,
    )

    data = await service.update_location(
        user_id=current_user.id,
        gym_id=gym_id,
        payload=payload,
    )

    return APIResponse(data=data)


@router.patch(
    "/{gym_id}/business-details",
    response_model=APIResponse[UpdateGymBusinessDetailsData],
)
async def update_gym_business_details(
    gym_id: UUID,
    payload: UpdateGymBusinessDetailsRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
    settings: ApplicationSettings,
) -> APIResponse[UpdateGymBusinessDetailsData]:
    """Save the gym's legal and operational business details."""

    service = GymService(
        session=session,
        default_phone_region=settings.default_phone_region,
    )

    data = await service.update_business_details(
        user_id=current_user.id,
        gym_id=gym_id,
        payload=payload,
    )

    return APIResponse(data=data)


@router.put(
    "/{gym_id}/amenities",
    response_model=APIResponse[UpdateGymAmenitiesData],
)
async def update_gym_amenities(
    gym_id: UUID,
    payload: UpdateGymAmenitiesRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
    settings: ApplicationSettings,
) -> APIResponse[UpdateGymAmenitiesData]:
    """Replace the gym's selected amenities."""

    service = GymService(
        session=session,
        default_phone_region=settings.default_phone_region,
    )

    data = await service.update_amenities(
        user_id=current_user.id,
        gym_id=gym_id,
        payload=payload,
    )

    return APIResponse(data=data)


@router.get(
    "/{gym_id}/operating-hours",
    response_model=APIResponse[list[GymOperatingHoursData]],
)
async def get_gym_operating_hours(
    gym_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
    settings: ApplicationSettings,
) -> APIResponse[list[GymOperatingHoursData]]:
    """Return the gym's weekly operating schedule."""

    service = GymService(
        session=session,
        default_phone_region=settings.default_phone_region,
    )

    data = await service.get_operating_hours(
        user_id=current_user.id,
        gym_id=gym_id,
    )

    return APIResponse(data=data)


@router.put(
    "/{gym_id}/operating-hours",
    response_model=APIResponse[UpdateGymOperatingHoursData],
)
async def update_gym_operating_hours(
    gym_id: UUID,
    payload: UpdateGymOperatingHoursRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
    settings: ApplicationSettings,
) -> APIResponse[UpdateGymOperatingHoursData]:
    """Replace the gym's complete weekly schedule."""

    service = GymService(
        session=session,
        default_phone_region=settings.default_phone_region,
    )

    data = await service.update_operating_hours(
        user_id=current_user.id,
        gym_id=gym_id,
        payload=payload,
    )

    return APIResponse(data=data)


@router.get(
    "/{gym_id}/pricing",
    response_model=APIResponse[GymPricingData],
)
async def get_gym_pricing(
    gym_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
    settings: ApplicationSettings,
) -> APIResponse[GymPricingData]:
    """Return gym day passes and membership plans."""

    service = GymService(
        session=session,
        default_phone_region=settings.default_phone_region,
    )

    data = await service.get_pricing(
        user_id=current_user.id,
        gym_id=gym_id,
    )

    return APIResponse(data=data)


@router.put(
    "/{gym_id}/pricing",
    response_model=APIResponse[UpdateGymPricingData],
)
async def update_gym_pricing(
    gym_id: UUID,
    payload: UpdateGymPricingRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
    settings: ApplicationSettings,
) -> APIResponse[UpdateGymPricingData]:
    """Replace gym day passes and membership plans."""

    service = GymService(
        session=session,
        default_phone_region=settings.default_phone_region,
    )

    data = await service.update_pricing(
        user_id=current_user.id,
        gym_id=gym_id,
        payload=payload,
    )

    return APIResponse(data=data)


@router.post(
    "/{gym_id}/verification/documents/{document_type}/upload",
    response_model=APIResponse[GymVerificationUploadData],
)
async def initiate_verification_document_upload(
    gym_id: UUID,
    document_type: GymVerificationDocumentType,
    payload: GymVerificationUploadRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
    settings: ApplicationSettings,
) -> APIResponse[GymVerificationUploadData]:
    service = GymService(
        session=session,
        default_phone_region=settings.default_phone_region,
        storage=S3Storage(settings),
    )
    return APIResponse(
        data=await service.initiate_verification_upload(
            user_id=current_user.id,
            gym_id=gym_id,
            document_type=document_type,
            payload=payload,
        )
    )


@router.post(
    "/{gym_id}/verification/documents/{document_type}/upload/{upload_id}/complete",
    response_model=APIResponse[GymVerificationDocumentData],
)
async def complete_verification_document_upload(
    gym_id: UUID,
    document_type: GymVerificationDocumentType,
    upload_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
    settings: ApplicationSettings,
) -> APIResponse[GymVerificationDocumentData]:
    service = GymService(
        session=session,
        default_phone_region=settings.default_phone_region,
        storage=S3Storage(settings),
    )
    return APIResponse(
        data=await service.complete_verification_upload(
            user_id=current_user.id,
            gym_id=gym_id,
            document_type=document_type,
            upload_id=upload_id,
        )
    )


@router.get(
    "/{gym_id}/verification/documents/{document_type}/download",
    response_model=APIResponse[GymVerificationDownloadData],
)
async def download_verification_document(
    gym_id: UUID,
    document_type: GymVerificationDocumentType,
    current_user: CurrentUser,
    session: DatabaseSession,
    settings: ApplicationSettings,
) -> APIResponse[GymVerificationDownloadData]:
    service = GymService(
        session=session,
        default_phone_region=settings.default_phone_region,
        storage=S3Storage(settings),
    )
    return APIResponse(
        data=await service.get_verification_download(
            user=current_user, gym_id=gym_id, document_type=document_type
        )
    )


@router.get(
    "/{gym_id}/verification",
    response_model=APIResponse[GymVerificationData],
)
async def get_gym_verification(
    gym_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
    settings: ApplicationSettings,
) -> APIResponse[GymVerificationData]:
    service = GymService(
        session=session, default_phone_region=settings.default_phone_region
    )
    return APIResponse(
        data=await service.get_verification(user=current_user, gym_id=gym_id)
    )


@router.post(
    "/{gym_id}/verification/submit",
    response_model=APIResponse[GymVerificationData],
)
async def submit_gym_verification(
    gym_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
    settings: ApplicationSettings,
) -> APIResponse[GymVerificationData]:
    service = GymService(
        session=session, default_phone_region=settings.default_phone_region
    )
    return APIResponse(
        data=await service.submit_verification(user_id=current_user.id, gym_id=gym_id)
    )
