from fastapi import FastAPI
from app.routers import score
from app.db import database

app = FastAPI(title="AI Exposure Scoring API", version="0.1.0")
app.include_router(score.router)


@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


@app.get("/")
async def root():
    return {"message": "AI Exposure Scoring API running"}
