from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from db.db import get_session_maker

# Async session factory; reused across dependencies
SessionLocal = get_session_maker()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
