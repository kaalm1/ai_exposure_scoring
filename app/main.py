import app.silence_logs  # isort:skip  # noqa
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db_manager import AsyncDatabaseManager
from app.routers import companies, score

# Configure root logger
logging.basicConfig(
    level=logging.INFO,  # or DEBUG
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
# Create logger for this module
logger = logging.getLogger(__name__)

db_manager = AsyncDatabaseManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database
    await db_manager.initialize_database()
    logger.info("Database initialized")
    yield
    # Shutdown: Dispose database connections
    await db_manager.dispose()
    logger.info("Database connections closed")


app = FastAPI(title="AI Exposure Scoring API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite's default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(score.router)
app.include_router(companies.router)


@app.get("/")
async def root():
    return {"message": "AI Exposure Scoring API running"}
