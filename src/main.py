from fastapi import FastAPI

from src.auth.endpoints import router as auth_router
from src.company.endpoints import router as company_router
from src.company.models import (  # noqa: F401
    Company,
    CompanyInvitation,
    CompanyMember,
    CompanyTasks,
    CompanyWallet,
)
from src.core.base_model import Base
from src.core.database import engine
from src.user.endpoints import router as user_router
from src.user.models import User, UserContacts, UserExperience  # noqa: F401

Base.metadata.create_all(bind=engine)

app = FastAPI(title="passproof")


app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(user_router, prefix="/users", tags=["users"])
app.include_router(company_router, prefix="/companies", tags=["companies"])
