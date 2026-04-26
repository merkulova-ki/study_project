from pydantic import BaseModel, Field


class RegisterUserRequestSchema(BaseModel):
    email: str = Field(pattern=r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
    password: str
