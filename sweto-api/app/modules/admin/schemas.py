from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.modules.auth.enums import UserRole, UserStatus
from app.modules.auth.security import normalize_email


class CreateAdminRequest(BaseModel):
    email: EmailStr
    temporary_password: str = Field(min_length=1, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_admin_email(cls, value: object) -> object:
        return normalize_email(value) if isinstance(value, str) else value


class AdminUserData(BaseModel):
    id: UUID
    email: EmailStr | None
    phone_number: str | None
    role: UserRole
    status: UserStatus
    must_change_password: bool
    is_system_protected: bool
    created_at: datetime
    updated_at: datetime


class AdminUserListData(BaseModel):
    users: list[AdminUserData]
    total: int
    limit: int
    offset: int


class UpdateAdminStatusRequest(BaseModel):
    status: UserStatus


class DemoteAdminRequest(BaseModel):
    role: UserRole
