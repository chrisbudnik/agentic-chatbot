import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base


@pytest.fixture
async def db_session() -> AsyncSession:
	"""
	Create an isolated in-memory SQLite DB per test, including all tables.
	"""
	engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
	async with engine.begin() as conn:
		await conn.run_sync(Base.metadata.create_all)

	SessionLocal = sessionmaker(
		autocommit=False,
		autoflush=False,
		bind=engine,
		class_=AsyncSession,
		expire_on_commit=False,
	)
	async with SessionLocal() as session:
		yield session

	await engine.dispose()
