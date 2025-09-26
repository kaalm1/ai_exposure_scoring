from pydantic import BaseModel

class ScoreRequest(BaseModel):
    company_name: str
    ticker: str | None = None
