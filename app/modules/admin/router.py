from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.modules.admin.dependencies import SuperAdminUser
from app.modules.admin.exceptions import InvalidAdminRoleChangeError
from app.modules.admin.schemas import (
    AdminUserData,
    AdminUserListData,
    CreateAdminRequest,
    DemoteAdminRequest,
    UpdateAdminStatusRequest,
)
from app.modules.admin.service import AdminService
from app.modules.auth.enums import UserRole
from app.shared.responses import APIResponse

router = APIRouter(prefix="/admin/users", tags=["Platform Administration"])
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post("", response_model=APIResponse[AdminUserData], status_code=201)
async def create_admin(
    payload: CreateAdminRequest,
    actor: SuperAdminUser,
    session: DatabaseSession,
) -> APIResponse[AdminUserData]:
    data = await AdminService(session).create_admin(
        actor=actor,
        email=str(payload.email),
        temporary_password=payload.temporary_password,
    )
    return APIResponse(data=data)


@router.get("", response_model=APIResponse[AdminUserListData])
async def list_admins(
    actor: SuperAdminUser,
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> APIResponse[AdminUserListData]:
    return APIResponse(
        data=await AdminService(session).list_admins(
            actor=actor, limit=limit, offset=offset
        )
    )


@router.get("/{user_id}", response_model=APIResponse[AdminUserData])
async def get_admin(
    user_id: UUID, actor: SuperAdminUser, session: DatabaseSession
) -> APIResponse[AdminUserData]:
    return APIResponse(
        data=await AdminService(session).get_admin(actor=actor, user_id=user_id)
    )


@router.patch("/{user_id}/status", response_model=APIResponse[AdminUserData])
async def update_admin_status(
    user_id: UUID,
    payload: UpdateAdminStatusRequest,
    actor: SuperAdminUser,
    session: DatabaseSession,
) -> APIResponse[AdminUserData]:
    return APIResponse(
        data=await AdminService(session).update_status(
            actor=actor, user_id=user_id, status=payload.status
        )
    )


@router.patch("/{user_id}/role", response_model=APIResponse[AdminUserData])
async def demote_admin(
    user_id: UUID,
    payload: DemoteAdminRequest,
    actor: SuperAdminUser,
    session: DatabaseSession,
) -> APIResponse[AdminUserData]:
    if payload.role != UserRole.USER:
        raise InvalidAdminRoleChangeError("Only Admin to User demotion is supported.")
    return APIResponse(
        data=await AdminService(session).demote_admin(actor=actor, user_id=user_id)
    )
