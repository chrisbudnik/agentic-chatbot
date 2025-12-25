import pytest
from typing import AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient, ASGITransport

from app.core.database import Base, get_db
from app.main import app


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
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


@pytest.fixture
async def test_client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
	"""
	Create a test client with an isolated in-memory database.
	Overrides the get_db dependency to use the test session.
	"""

	async def override_get_db():
		yield db_session

	app.dependency_overrides[get_db] = override_get_db

	transport = ASGITransport(app=app)
	async with AsyncClient(
		transport=transport, base_url="http://test"
	) as client:
		yield client

	app.dependency_overrides.clear()
