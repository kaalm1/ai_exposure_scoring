from fastapi import APIRouter
from app.models.schemas import ScoreRequest
from app.services.scorer import score_company

router = APIRouter(prefix="/score", tags=["Scoring"])


@router.post("/")
async def score_endpoint(request: ScoreRequest):
    result = await score_company(request.company_name, request.ticker)
    return result
