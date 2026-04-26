from collections.abc import Generator

from anyio.functools import lru_cache
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from src.core.config import settings

engine = create_engine(
    f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
)


@lru_cache
def create_session() -> scoped_session:
    session_factory = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    session = scoped_session(session_factory)
    return session


def get_session() -> Generator[scoped_session, None, None]:
    session = create_session()
    try:
        yield session
    finally:
        session.remove()
