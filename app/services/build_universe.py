import time
import httpx
import yfinance as yf
from app.dal.ai_scores import AIScoreDAL

SEC_TICKER_URL = "https://www.sec.gov/files/company_tickers.json"


class UniverseBuilderService:
    """Service to build and refresh the AI company universe using batched yfinance requests."""

    def __init__(self, ai_score_dal: AIScoreDAL, batch_size: int = 50):
        self.ai_score_dal = ai_score_dal
        self.batch_size = batch_size

    def fetch_sec_tickers(self) -> dict[str, dict[str, str]]:
        """Fetch ticker -> CIK mapping from SEC."""
        resp = httpx.get(
            SEC_TICKER_URL, timeout=30, headers={"User-Agent": "ai-exposure-app"}
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

    def enrich_batch(self, tickers: list[str]) -> dict[str, dict]:
        """Fetch sector, industry, description and other key fields for multiple tickers using yfinance.Tickers."""
        info_dict = {}
        if not tickers:
            return info_dict

        try:
            yf_batch = yf.Tickers(" ".join(tickers))
            for ticker in tickers:
                info = getattr(yf_batch.tickers.get(ticker), "info", None)
                if not info:
                    continue
                info_dict[ticker] = {
                    "company_name": info.get("longName") or info.get("shortName"),
                    "sector": info.get("sector"),
                    "industry": info.get("industry"),
                    "description": info.get("longBusinessSummary"),
                    "market_cap": info.get("marketCap"),
                    "enterprise_value": info.get("enterpriseValue"),
                    "employees": info.get("fullTimeEmployees"),
                    "website": info.get("website"),
                    "logo_url": info.get("logo_url"),
                    "beta": info.get("beta"),
                    "recommendation_key": info.get("recommendationKey"),
                    "recommendation_mean": info.get("recommendationMean"),
                    "hq_city": info.get("city"),
                    "hq_state": info.get("state"),
                }
        except Exception:
            pass  # optionally log errors
        return info_dict

    def build_universe(self, limit: int | None = None) -> int:
        """Build/refresh the AI universe using SEC + Yahoo Finance in batches."""
        sec_tickers = self.fetch_sec_tickers()
        processed = 0

        # Get already enriched tickers from DAL
        enriched_tickers = self.ai_score_dal.get_enriched_tickers()

        # Filter out already enriched
        to_process = [
            (ticker, meta) for ticker, meta in sec_tickers.items() if ticker not in enriched_tickers
        ]

        # Apply limit if provided
        if limit:
            to_process = to_process[:limit]

        # Process in batches
        for i in range(0, len(to_process), self.batch_size):
            batch = to_process[i : i + self.batch_size]
            tickers_batch = [ticker for ticker, _ in batch]

            yfinance_data = self.enrich_batch(tickers_batch)

            for ticker, meta in batch:
                data = yfinance_data.get(ticker)
                if not data:
                    continue

                # Add CIK from SEC mapping
                data["cik"] = meta["cik"]

                # Upsert using the new DAL
                self.ai_score_dal.upsert(ticker, data)
                processed += 1

            # optional wait between batches to avoid hitting rate limits
            time.sleep(5)

        return processed
