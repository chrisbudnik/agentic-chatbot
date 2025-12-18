from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Use aiosqlite for the async sqlite driver
engine = create_async_engine(
	settings.DATABASE_URL,
	echo=False,
	future=True,
	connect_args={"check_same_thread": False}
	if "sqlite" in settings.DATABASE_URL
	else {},
)

SessionLocal = sessionmaker(
	autocommit=False,
	autoflush=False,
	bind=engine,
	class_=AsyncSession,
	expire_on_commit=False,
)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
	async with SessionLocal() as session:
		try:
			yield session
		finally:
			await session.close()
