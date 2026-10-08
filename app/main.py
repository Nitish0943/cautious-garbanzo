from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine
from app.models.base import Base
from app.api.routes import jobs, certificates
from app.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure tables exist on startup (especially for SQLite or initial bootstrapping)
    logger.info("Initializing database schema...")
    Base.metadata.create_all(bind=engine)
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} started successfully.")
    yield
    logger.info(f"Shutting down {settings.APP_NAME}...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Production-ready bulk certificate generation API with asynchronous background processing and fault isolation.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Enable CORS for convenience
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Register API v1 routes
app.include_router(jobs.router, prefix=settings.API_V1_STR)
app.include_router(certificates.router, prefix=settings.API_V1_STR)

# Mount static files if present
static_dir = Path("static")
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", tags=["Dashboard"])
def root():
    index_file = Path("static/index.html")
    if index_file.exists():
        return FileResponse(index_file)
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "status": "healthy",
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
