"""
PostgreSQL database connection & session management.

Uses SQLAlchemy async engine for FastAPI compatibility.

Environment variables:
    DATABASE_URL – PostgreSQL connection string
                   default: postgresql+asyncpg://postgres:postgres@localhost:5432/iksha
"""

import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/iksha",
)

engine = create_async_engine(DATABASE_URL, echo=False, pool_size=20, max_overflow=10)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncSession:
    """Dependency for FastAPI: yields a DB session."""
    async with async_session_factory() as session:
        yield session


async def init_db():
    """Create all tables (call once at startup)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
