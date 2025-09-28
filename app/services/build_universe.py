import httpx
import yfinance as yf
from app.dal.ai_scores import AIScoreDAL

SEC_TICKER_URL = "https://www.sec.gov/files/company_tickers.json"


class UniverseBuilderService:
    """Service to build and refresh the AI company universe."""

    def __init__(self, ai_score_dal: AIScoreDAL):
        self.ai_score_dal = ai_score_dal

    async def fetch_sec_tickers(self) -> dict[str, dict[str, str]]:
        """Fetch ticker -> CIK mapping from SEC."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                SEC_TICKER_URL, headers={"User-Agent": "ai-exposure-app"}
            )
            resp.raise_for_status()
            data = resp.json()

        tickers = {}
        for _, entry in data.items():
            ticker = entry.get("ticker")
            cik = str(entry.get("cik_str")).zfill(10)
            name = entry.get("title")
            if ticker:
                tickers[ticker.upper()] = {"cik": cik, "name": name}
        return tickers

    async def enrich_with_yfinance(self, ticker: str) -> dict | None:
        """Fetch sector, industry, description from Yahoo Finance."""
        try:
            info = yf.Ticker(ticker).info
            return {
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "description": info.get("longBusinessSummary"),
            }
        except Exception:
            return None

    async def build_universe(self, limit: int | None = None) -> int:
        """Build/refresh the AI universe using SEC + Yahoo Finance."""
        sec_tickers = await self.fetch_sec_tickers()
        processed = 0

        for ticker, meta in sec_tickers.items():
            if limit and processed >= limit:
                break

            enrich = await self.enrich_with_yfinance(ticker)
            if not enrich:
                continue

            await self.ai_score_dal.upsert(
                ticker=ticker,
                cik=meta["cik"],
                company_name=meta["name"],
                sector=enrich.get("sector"),
                industry=enrich.get("industry"),
                description=enrich.get("description"),
            )

            processed += 1

        return processed
