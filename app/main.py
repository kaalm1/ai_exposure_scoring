from fastapi import FastAPI

from app.config import settings
from app.db import engine
from app.db_manager import AsyncDatabaseManager
from app.routers import score

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
