from fastapi import FastAPI
from app.routers import score

app = FastAPI(title="AI Exposure Scoring API", version="0.1.0")

app.include_router(score.router)

@app.get("/")
async def root():
    return {"message": "AI Exposure Scoring API is running"}
