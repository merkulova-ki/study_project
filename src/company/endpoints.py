import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import scoped_session

from src.auth.security import manager
from src.company.models import (
    Company,
    CompanyInvitation,
    CompanyMember,
    CompanyRole,
    CompanyTasks,
    CompanyWallet,
    InvitationStatus,
)
from src.company.schemas import (
    CompanyCreateSchema,
    CompanyInvitationResponseSchema,
    CompanyInviteRequestSchema,
    CompanyMemberResponseSchema,
    CompanyMemberRoleUpdateSchema,
    CompanyPermissionResponseSchema,
    CompanyResponseSchema,
    CompanyUpdateSchema,
    CompanyWalletResponseSchema,
    CompanyTasksResponseSchema,
)
from src.core.database import get_session
from src.user.models import User

router = APIRouter()

ROLE_PRIORITY: dict[CompanyRole, int] = {
    CompanyRole.viewer: 1,
    CompanyRole.admin: 2,
    CompanyRole.full_access: 3,
}


def api_error(status_code: int, code: str, message: str) -> None:
    raise HTTPException(status_code=status_code, detail={"code": code, "message": message})


def get_company_or_404(db: scoped_session, company_id: uuid.UUID) -> Company:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        api_error(404, "COMPANY_NOT_FOUND", "Company not found.")
    return company


def get_member(
    db: scoped_session,
    company_id: uuid.UUID,
    user_id: uuid.UUID,
) -> CompanyMember | None:
    return (
        db.query(CompanyMember)
        .filter(CompanyMember.company_id == company_id, CompanyMember.user_id == user_id)
        .first()
    )


def require_role(
    db: scoped_session,
    company_id: uuid.UUID,
    user_id: uuid.UUID,
    min_role: CompanyRole,
) -> CompanyMember:
    member = get_member(db=db, company_id=company_id, user_id=user_id)
    if not member:
        api_error(403, "NO_COMPANY_ACCESS", "User has no access to this company.")
    if ROLE_PRIORITY[member.role] < ROLE_PRIORITY[min_role]:
        api_error(403, "INSUFFICIENT_ROLE", "Insufficient company permissions.")
    return member


def build_company_response(db: scoped_session, company: Company) -> CompanyResponseSchema:
    company_tasks = (
        db.query(CompanyTasks).filter(CompanyTasks.company_id == company.id).first()
    )
    company_wallet = (
        db.query(CompanyWallet).filter(CompanyWallet.company_id == company.id).first()
    )
    return CompanyResponseSchema(
        id=company.id,
        user_id=company.user_id,
        name=company.name,
        description=company.description,
        company_tasks=(
            CompanyTasksResponseSchema.model_validate(company_tasks)
            if company_tasks
            else None
        ),
        company_wallet=(
            CompanyWalletResponseSchema.model_validate(company_wallet)
            if company_wallet
            else None
        ),
    )


@router.post("", response_model=CompanyResponseSchema, status_code=201)
def create_company(
    payload: CompanyCreateSchema,
    db: Annotated[scoped_session, Depends(get_session)],
    current_user: Annotated[User, Depends(manager)],
):
    company = Company(
        user_id=current_user.id,
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
    )
    db.add(company)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        api_error(400, "COMPANY_EXISTS", "Company with this name already exists.")

    company_wallet = CompanyWallet(user_id=current_user.id, company_id=company.id)
    company_tasks = CompanyTasks(user_id=current_user.id, company_id=company.id, tasks=[])
    owner_member = CompanyMember(
        company_id=company.id,
        user_id=current_user.id,
        role=CompanyRole.full_access,
    )
    db.add(company_wallet)
    db.add(company_tasks)
    db.add(owner_member)
    db.commit()
    db.refresh(company)
    return build_company_response(db=db, company=company)


@router.get("/{company_id}", response_model=CompanyResponseSchema)
def get_company(
    company_id: uuid.UUID,
    db: Annotated[scoped_session, Depends(get_session)],
    _: Annotated[User, Depends(manager)],
):
    company = get_company_or_404(db=db, company_id=company_id)
    return build_company_response(db=db, company=company)


@router.patch("/{company_id}", response_model=CompanyResponseSchema)
def update_company(
    company_id: uuid.UUID,
    payload: CompanyUpdateSchema,
    db: Annotated[scoped_session, Depends(get_session)],
    current_user: Annotated[User, Depends(manager)],
):
    require_role(
        db=db,
        company_id=company_id,
        user_id=current_user.id,
        min_role=CompanyRole.admin,
    )
    company = get_company_or_404(db=db, company_id=company_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        if key in {"name", "description"} and isinstance(value, str):
            value = value.strip()
            if key == "name" and not value:
                api_error(422, "INVALID_COMPANY_NAME", "Company name cannot be empty.")
            if key == "description":
                value = value or None
        setattr(company, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        api_error(400, "COMPANY_EXISTS", "Company with this name already exists.")
    db.refresh(company)
    return build_company_response(db=db, company=company)


@router.delete("/{company_id}", status_code=204)
def delete_company(
    company_id: uuid.UUID,
    db: Annotated[scoped_session, Depends(get_session)],
    current_user: Annotated[User, Depends(manager)],
):
    require_role(
        db=db,
        company_id=company_id,
        user_id=current_user.id,
        min_role=CompanyRole.full_access,
    )
    company = get_company_or_404(db=db, company_id=company_id)
    db.delete(company)
    db.commit()
    return None


@router.get("/{company_id}/members", response_model=list[CompanyMemberResponseSchema])
def list_company_members(
    company_id: uuid.UUID,
    db: Annotated[scoped_session, Depends(get_session)],
    current_user: Annotated[User, Depends(manager)],
):
    require_role(
        db=db,
        company_id=company_id,
        user_id=current_user.id,
        min_role=CompanyRole.viewer,
    )
    return db.query(CompanyMember).filter(CompanyMember.company_id == company_id).all()


@router.patch(
    "/{company_id}/members/{member_user_id}",
    response_model=CompanyMemberResponseSchema,
)
def update_company_member_role(
    company_id: uuid.UUID,
    member_user_id: uuid.UUID,
    payload: CompanyMemberRoleUpdateSchema,
    db: Annotated[scoped_session, Depends(get_session)],
    current_user: Annotated[User, Depends(manager)],
):
    requester = require_role(
        db=db,
        company_id=company_id,
        user_id=current_user.id,
        min_role=CompanyRole.admin,
    )
    target_member = get_member(db=db, company_id=company_id, user_id=member_user_id)
    if not target_member:
        api_error(404, "MEMBER_NOT_FOUND", "Company member not found.")
    if target_member.user_id == current_user.id:
        api_error(400, "SELF_ROLE_CHANGE_FORBIDDEN", "You cannot change your own role.")
    if requester.role != CompanyRole.full_access and payload.role == CompanyRole.full_access:
        api_error(403, "ONLY_OWNER_CAN_GRANT_FULL_ACCESS", "Only owner can grant full access.")
    target_member.role = payload.role
    db.commit()
    db.refresh(target_member)
    return target_member


@router.delete("/{company_id}/members/{member_user_id}", status_code=204)
def remove_company_member(
    company_id: uuid.UUID,
    member_user_id: uuid.UUID,
    db: Annotated[scoped_session, Depends(get_session)],
    current_user: Annotated[User, Depends(manager)],
):
    requester = require_role(
        db=db,
        company_id=company_id,
        user_id=current_user.id,
        min_role=CompanyRole.admin,
    )
    target_member = get_member(db=db, company_id=company_id, user_id=member_user_id)
    if not target_member:
        api_error(404, "MEMBER_NOT_FOUND", "Company member not found.")
    if target_member.user_id == current_user.id:
        api_error(400, "SELF_REMOVE_FORBIDDEN", "You cannot remove yourself.")
    if (
        requester.role != CompanyRole.full_access
        and target_member.role == CompanyRole.full_access
    ):
        api_error(403, "ONLY_OWNER_CAN_REMOVE_OWNER", "Only owner can remove owner.")
    db.delete(target_member)
    db.commit()
    return None


@router.post(
    "/{company_id}/invitations",
    response_model=CompanyInvitationResponseSchema,
    status_code=201,
)
def invite_user_to_company(
    company_id: uuid.UUID,
    payload: CompanyInviteRequestSchema,
    db: Annotated[scoped_session, Depends(get_session)],
    current_user: Annotated[User, Depends(manager)],
):
    requester = require_role(
        db=db,
        company_id=company_id,
        user_id=current_user.id,
        min_role=CompanyRole.admin,
    )
    if requester.role != CompanyRole.full_access and payload.role == CompanyRole.full_access:
        api_error(403, "ONLY_OWNER_CAN_INVITE_OWNER", "Only owner can invite with full access.")

    invited_user = db.query(User).filter(User.email == payload.user_email).first()
    if not invited_user:
        api_error(404, "INVITED_USER_NOT_FOUND", "Invited user not found.")
    if get_member(db=db, company_id=company_id, user_id=invited_user.id):
        api_error(400, "ALREADY_MEMBER", "User is already a company member.")

    invitation = CompanyInvitation(
        company_id=company_id,
        invited_user_id=invited_user.id,
        invited_by_user_id=current_user.id,
        role=payload.role,
        status=InvitationStatus.pending,
    )
    db.add(invitation)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        api_error(400, "INVITATION_EXISTS", "Pending invitation already exists.")
    db.refresh(invitation)
    return invitation


@router.post(
    "/invitations/{invitation_id}/accept",
    response_model=CompanyMemberResponseSchema,
)
def accept_company_invitation(
    invitation_id: uuid.UUID,
    db: Annotated[scoped_session, Depends(get_session)],
    current_user: Annotated[User, Depends(manager)],
):
    invitation = (
        db.query(CompanyInvitation)
        .filter(
            CompanyInvitation.id == invitation_id,
            CompanyInvitation.invited_user_id == current_user.id,
            CompanyInvitation.status == InvitationStatus.pending,
        )
        .first()
    )
    if not invitation:
        api_error(404, "INVITATION_NOT_FOUND", "Pending invitation not found.")

    member = get_member(
        db=db,
        company_id=invitation.company_id,
        user_id=current_user.id,
    )
    if member is None:
        member = CompanyMember(
            company_id=invitation.company_id,
            user_id=current_user.id,
            role=invitation.role,
        )
        db.add(member)
    else:
        member.role = invitation.role

    invitation.status = InvitationStatus.accepted
    db.commit()
    db.refresh(member)
    return member


@router.post(
    "/invitations/{invitation_id}/decline",
    response_model=CompanyInvitationResponseSchema,
)
def decline_company_invitation(
    invitation_id: uuid.UUID,
    db: Annotated[scoped_session, Depends(get_session)],
    current_user: Annotated[User, Depends(manager)],
):
    invitation = (
        db.query(CompanyInvitation)
        .filter(
            CompanyInvitation.id == invitation_id,
            CompanyInvitation.invited_user_id == current_user.id,
            CompanyInvitation.status == InvitationStatus.pending,
        )
        .first()
    )
    if not invitation:
        api_error(404, "INVITATION_NOT_FOUND", "Pending invitation not found.")
    invitation.status = InvitationStatus.declined
    db.commit()
    db.refresh(invitation)
    return invitation


@router.get("/{company_id}/permissions/me", response_model=CompanyPermissionResponseSchema)
def check_my_company_permissions(
    company_id: uuid.UUID,
    db: Annotated[scoped_session, Depends(get_session)],
    current_user: Annotated[User, Depends(manager)],
):
    member = get_member(db=db, company_id=company_id, user_id=current_user.id)
    role = member.role if member else None
    return CompanyPermissionResponseSchema(
        company_id=company_id,
        user_id=current_user.id,
        role=role,
        can_view=role is not None,
        can_admin=role in {CompanyRole.admin, CompanyRole.full_access},
        can_full_access=role == CompanyRole.full_access,
    )
