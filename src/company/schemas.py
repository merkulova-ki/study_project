import uuid

from pydantic import BaseModel, ConfigDict, Field

from src.company.models import CompanyRole, InvitationStatus


class CompanyBaseSchema(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4096)


class CompanyCreateSchema(CompanyBaseSchema):
    pass


class CompanyUpdateSchema(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4096)


class CompanyTasksResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    company_id: uuid.UUID
    tasks: list[dict]


class CompanyWalletResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    company_id: uuid.UUID
    wallet: dict


class CompanyResponseSchema(CompanyBaseSchema):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    company_tasks: CompanyTasksResponseSchema | None = None
    company_wallet: CompanyWalletResponseSchema | None = None


class CompanyMemberResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    user_id: uuid.UUID
    role: CompanyRole


class CompanyInviteRequestSchema(BaseModel):
    user_email: str = Field(
        pattern=r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    )
    role: CompanyRole


class CompanyMemberRoleUpdateSchema(BaseModel):
    role: CompanyRole


class CompanyInvitationResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    invited_user_id: uuid.UUID
    invited_by_user_id: uuid.UUID
    role: CompanyRole
    status: InvitationStatus


class CompanyPermissionResponseSchema(BaseModel):
    company_id: uuid.UUID
    user_id: uuid.UUID
    role: CompanyRole | None = None
    can_view: bool
    can_admin: bool
    can_full_access: bool
