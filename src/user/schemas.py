import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserContactsBaseSchema(BaseModel):
    phone: str = Field(min_length=5, max_length=32)
    email: str = Field(pattern=r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
    socials: list[str] = Field(default_factory=list)

    @field_validator("socials")
    @classmethod
    def validate_socials(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value if item.strip()]
        if len(normalized) != len(set(normalized)):
            raise ValueError("socials must contain unique values")
        return normalized


class UserContactsCreateSchema(UserContactsBaseSchema):
    pass


class UserContactsUpdateSchema(BaseModel):
    phone: str | None = None
    email: str | None = None
    socials: list[str] | None = None


class UserContactsResponseSchema(UserContactsBaseSchema):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID


class UserExperienceBaseSchema(BaseModel):
    need_work: bool
    resume: str | None = Field(default=None, max_length=2048)


class UserExperienceCreateSchema(UserExperienceBaseSchema):
    pass


class UserExperienceUpdateSchema(BaseModel):
    need_work: bool | None = None
    resume: str | None = None


class UserExperienceResponseSchema(UserExperienceBaseSchema):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID


class UserProfileBaseSchema(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    surname: str = Field(min_length=1, max_length=128)
    patronymic: str | None = Field(default=None, max_length=128)
    o_sebe: str | None = Field(default=None, max_length=4096)
    skills: list[str] = Field(default_factory=list)

    @field_validator("skills")
    @classmethod
    def validate_skills(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value if item.strip()]
        if len(normalized) != len(set(normalized)):
            raise ValueError("skills must contain unique values")
        return normalized


class UserProfileCreateSchema(UserProfileBaseSchema):
    user_contacts: UserContactsCreateSchema
    user_experience: UserExperienceCreateSchema


class UserProfileUpdateSchema(BaseModel):
    name: str | None = None
    surname: str | None = None
    patronymic: str | None = None
    o_sebe: str | None = None
    skills: list[str] | None = None
    user_contacts: UserContactsUpdateSchema | None = None
    user_experience: UserExperienceUpdateSchema | None = None


class UserProfileResponseSchema(UserProfileBaseSchema):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_contacts: UserContactsResponseSchema | None = None
    user_experience: UserExperienceResponseSchema | None = None
