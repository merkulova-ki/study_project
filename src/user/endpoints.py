import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import scoped_session

from src.auth.security import manager
from src.core.database import get_session
from src.user.models import User, UserContacts, UserExperience
from src.user.schemas import (
    UserContactsResponseSchema,
    UserProfileCreateSchema,
    UserProfileResponseSchema,
    UserProfileUpdateSchema,
    UserExperienceResponseSchema,
)

router = APIRouter()


def api_error(status_code: int, code: str, message: str) -> None:
    raise HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized if normalized else None


def profile_exists(db: scoped_session, user_id: uuid.UUID) -> bool:
    contacts_exists = db.query(UserContacts).filter(UserContacts.user_id == user_id).first()
    experience_exists = (
        db.query(UserExperience).filter(UserExperience.user_id == user_id).first()
    )
    return bool(contacts_exists and experience_exists)


def get_user_profile_response(
    db: scoped_session,
    user: User,
) -> UserProfileResponseSchema:
    contacts = db.query(UserContacts).filter(UserContacts.user_id == user.id).first()
    experience = (
        db.query(UserExperience).filter(UserExperience.user_id == user.id).first()
    )
    return UserProfileResponseSchema(
        id=user.id,
        name=user.name,
        surname=user.surname,
        patronymic=user.patronymic,
        o_sebe=user.o_sebe,
        skills=user.skills,
        user_contacts=(
            UserContactsResponseSchema.model_validate(contacts) if contacts else None
        ),
        user_experience=(
            UserExperienceResponseSchema.model_validate(experience)
            if experience
            else None
        ),
    )


def get_user_or_404(db: scoped_session, user_id: uuid.UUID) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        api_error(status_code=404, code="USER_NOT_FOUND", message="User not found.")
    return user


@router.post("/me/profile", response_model=UserProfileResponseSchema, status_code=201)
def create_my_profile(
    profile_data: UserProfileCreateSchema,
    db: Annotated[scoped_session, Depends(get_session)],
    current_user: Annotated[User, Depends(manager)],
):
    existing_contacts = (
        db.query(UserContacts).filter(UserContacts.user_id == current_user.id).first()
    )
    existing_experience = (
        db.query(UserExperience).filter(UserExperience.user_id == current_user.id).first()
    )
    if existing_contacts or existing_experience:
        api_error(
            status_code=400,
            code="PROFILE_EXISTS",
            message="Profile already exists.",
        )

    current_user.name = profile_data.name.strip()
    current_user.surname = profile_data.surname.strip()
    current_user.patronymic = normalize_optional_text(profile_data.patronymic)
    current_user.o_sebe = normalize_optional_text(profile_data.o_sebe)
    current_user.skills = profile_data.skills

    contacts = UserContacts(user_id=current_user.id, **profile_data.user_contacts.model_dump())
    experience = UserExperience(
        user_id=current_user.id, **profile_data.user_experience.model_dump()
    )
    db.add(contacts)
    db.add(experience)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        api_error(
            status_code=400,
            code="PROFILE_CONFLICT",
            message="Profile contains conflicting unique values.",
        )
    db.refresh(current_user)
    return get_user_profile_response(db=db, user=current_user)


@router.get("/me/profile", response_model=UserProfileResponseSchema)
def get_my_profile(
    db: Annotated[scoped_session, Depends(get_session)],
    current_user: Annotated[User, Depends(manager)],
):
    if not profile_exists(db=db, user_id=current_user.id):
        api_error(status_code=404, code="PROFILE_NOT_FOUND", message="Profile not found.")
    return get_user_profile_response(db=db, user=current_user)


@router.get("/{user_id}/profile", response_model=UserProfileResponseSchema)
def get_profile_by_user_id(
    user_id: uuid.UUID,
    db: Annotated[scoped_session, Depends(get_session)],
    _: Annotated[User, Depends(manager)],
):
    user = get_user_or_404(db=db, user_id=user_id)
    if not profile_exists(db=db, user_id=user.id):
        api_error(status_code=404, code="PROFILE_NOT_FOUND", message="Profile not found.")
    return get_user_profile_response(db=db, user=user)


@router.patch("/me/profile", response_model=UserProfileResponseSchema)
def update_my_profile(
    profile_data: UserProfileUpdateSchema,
    db: Annotated[scoped_session, Depends(get_session)],
    current_user: Annotated[User, Depends(manager)],
):
    if not profile_exists(db=db, user_id=current_user.id):
        api_error(status_code=404, code="PROFILE_NOT_FOUND", message="Profile not found.")

    for field, value in profile_data.model_dump(exclude_unset=True).items():
        if field in {"user_contacts", "user_experience"}:
            continue
        if field in {"name", "surname"} and isinstance(value, str):
            value = value.strip()
            if not value:
                api_error(
                    status_code=422,
                    code="INVALID_PROFILE_FIELD",
                    message=f"{field} cannot be empty.",
                )
        if field in {"patronymic", "o_sebe"} and isinstance(value, str):
            value = normalize_optional_text(value)
        setattr(current_user, field, value)

    if profile_data.user_contacts is not None:
        contacts = (
            db.query(UserContacts).filter(UserContacts.user_id == current_user.id).first()
        )
        if contacts is None:
            contacts = UserContacts(
                user_id=current_user.id,
                phone="",
                email=current_user.email,
                socials=[],
            )
            db.add(contacts)
        for field, value in profile_data.user_contacts.model_dump(
            exclude_unset=True
        ).items():
            setattr(contacts, field, value)

    if profile_data.user_experience is not None:
        experience = (
            db.query(UserExperience)
            .filter(UserExperience.user_id == current_user.id)
            .first()
        )
        if experience is None:
            experience = UserExperience(
                user_id=current_user.id,
                need_work=False,
                resume=None,
            )
            db.add(experience)
        for field, value in profile_data.user_experience.model_dump(
            exclude_unset=True
        ).items():
            setattr(experience, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        api_error(
            status_code=400,
            code="PROFILE_CONFLICT",
            message="Profile contains conflicting unique values.",
        )
    db.refresh(current_user)
    return get_user_profile_response(db=db, user=current_user)


@router.delete("/me/profile", status_code=204)
def delete_my_profile(
    db: Annotated[scoped_session, Depends(get_session)],
    current_user: Annotated[User, Depends(manager)],
):
    if not profile_exists(db=db, user_id=current_user.id):
        api_error(status_code=404, code="PROFILE_NOT_FOUND", message="Profile not found.")

    contacts = db.query(UserContacts).filter(UserContacts.user_id == current_user.id).first()
    experience = (
        db.query(UserExperience).filter(UserExperience.user_id == current_user.id).first()
    )
    if contacts:
        db.delete(contacts)
    if experience:
        db.delete(experience)

    current_user.name = ""
    current_user.surname = ""
    current_user.patronymic = None
    current_user.o_sebe = None
    current_user.skills = []
    db.commit()
    return None
