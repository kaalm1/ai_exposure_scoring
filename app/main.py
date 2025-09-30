import logging

from fastapi import FastAPI

from app.db_manager import AsyncDatabaseManager
from app.routers import score

# Configure root logger
logging.basicConfig(
    level=logging.INFO,  # or DEBUG
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# Optional: increase verbosity of SQLAlchemy engine logs
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

# Create logger for this module
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Exposure Scoring API", version="0.1.0")
app.include_router(score.router)
db_manager = AsyncDatabaseManager()


@app.on_event("startup")
async def startup():
    # Initialize database on startup
    await db_manager.initialize_database()


@app.on_event("shutdown")
async def shutdown():
    await db_manager.dispose()


@app.get("/")
async def root():
    return {"message": "AI Exposure Scoring API running"}
