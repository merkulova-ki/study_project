import os

from dotenv import load_dotenv
from fastapi_login import LoginManager
from passlib.context import CryptContext
from slowapi import Limiter
from slowapi.util import get_remote_address

load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET = os.getenv("SECURITY_KEY")

manager = LoginManager(SECRET, "/login")

limiter = Limiter(key_func=get_remote_address)
