from fastapi import FastAPI

from src.auth.endpoints import router as auth_router


from src.core.base_model import Base
from src.core.database import engine
from src.user.models import User


Base.metadata.create_all(bind=engine)

app = FastAPI(title="passproof")


app.include_router(auth_router, prefix="/auth", tags=["auth"])
