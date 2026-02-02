"""SQLAlchemy session setup."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase


class Base(DeclarativeBase):
    pass


def make_engine(db_url: str):
    return create_engine(db_url, future=True)


def make_session_factory(db_url: str | None = None, engine=None):
    if engine is None:
        if not db_url:
            raise ValueError("db_url is required when engine is not provided")
        engine = make_engine(db_url)
    return sessionmaker(bind=engine, expire_on_commit=False, autoflush=False, future=True)
