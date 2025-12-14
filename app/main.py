import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import engine, Base
from app.api.routers import chat


@asynccontextmanager
async def lifespan(app: FastAPI):
	# Create tables on startup (For Dev only - use Alembic in Prod)
	async with engine.begin() as conn:
		await conn.run_sync(Base.metadata.create_all)
	yield
	pass


app = FastAPI(
	title=settings.PROJECT_NAME,
	openapi_url=f"{settings.API_V1_STR}/openapi.json",
	lifespan=lifespan,
)

# CORS
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

# Routers
app.include_router(chat.router, prefix="/api", tags=["chat"])

# Static Files (Frontend)
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
	uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
