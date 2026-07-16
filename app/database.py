"""Async SQLAlchemy engine, session factory, declarative base and FastAPI dependency."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


engine = create_async_engine(settings.async_database_url, echo=settings.db_echo, pool_pre_ping=True)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a transactional session.

    Note: this commit runs as part of the dependency's teardown, which FastAPI
    executes *after* any ``BackgroundTasks`` scheduled during the request have
    already run. Code that schedules a background task depending on data just
    written in this request must commit that data explicitly beforehand —
    never rely on this commit for background-task visibility.
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
