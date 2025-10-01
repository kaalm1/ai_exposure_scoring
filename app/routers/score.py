from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import get_sec_filing_service
from app.models.schemas import ScoreRequest
from app.services.sec_filing_service import SECFilingService

router = APIRouter(prefix="/score", tags=["Scoring"])


@router.post("/")
async def score_endpoint(
    request: ScoreRequest,
    sec_filing_service: Annotated[SECFilingService, Depends(get_sec_filing_service)],
):
    result = await sec_filing_service.process_and_score_company(
        request.company_name, request.ticker
    )
    return result
