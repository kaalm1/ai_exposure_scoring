import logging
import time

import httpx
import yfinance as yf

from app.dal.ai_scores import AIScoreDAL

logger = logging.getLogger(__name__)

SEC_TICKER_URL = "https://www.sec.gov/files/company_tickers.json"

HEADERS = {
    "User-Agent": "ai_exposure_scoring/1.0 (joanne.tisch@gmail.com)",
    "Accept-Encoding": "gzip, deflate",
    "Host": "www.sec.gov",
    "Accept": "*/*",
    "Connection": "keep-alive",
}


class UniverseBuilderService:
    """Service to build and refresh the AI company universe using batched yfinance requests."""

    def __init__(self, ai_score_dal: AIScoreDAL, batch_size: int = 50):
        self.ai_score_dal = ai_score_dal
        self.batch_size = batch_size

    def fetch_sec_tickers(self) -> dict[str, dict[str, str]]:
        """Fetch ticker -> CIK mapping from SEC."""
        with httpx.Client(headers=HEADERS, timeout=30) as client:
            resp = client.get(SEC_TICKER_URL)
            resp.raise_for_status()
            data = resp.json()

            tickers = {}
            for _, entry in data.items():
                ticker = entry.get("ticker")
                cik = str(entry.get("cik_str")).zfill(10)
                name = entry.get("title")
                if ticker:
                    tickers[ticker.upper()] = {"cik": cik, "name": name}

            logger.info(f"Fetched {len(tickers)} tickers")
            return tickers

    def enrich_batch(self, tickers: list[str]) -> dict[str, dict]:
        """Fetch sector, industry, description and other key fields for multiple tickers using yfinance.Tickers."""
        info_dict = {}
        if not tickers:
            logger.warning(f"No tickers found. Returning empty dict.")
            return info_dict

        try:
            yf_batch = yf.Tickers(" ".join(tickers))
            for ticker in tickers:
                info = getattr(yf_batch.tickers.get(ticker), "info", None)
                if not info:
                    logger.warning(f"No info found for ticker {ticker}")
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
            logger.info(f"Fetched {len(info_dict)} tickers")
        except Exception:
            logger.exception(
                "Failed to fetch yfinance.Tickers", extra={"tickers": tickers}
            )
        return info_dict

    async def build_universe(self, limit: int | None = None) -> int:
        """Build/refresh the AI universe using SEC + Yahoo Finance in batches."""
        logger.info("Starting universe build process...")

        sec_tickers = self.fetch_sec_tickers()
        logger.info(f"Fetched {len(sec_tickers)} tickers from SEC")

        processed = 0

        # Get already enriched tickers from DAL
        enriched_tickers = await self.ai_score_dal.get_enriched_tickers()
        logger.info(f"{len(enriched_tickers)} tickers already enriched, skipping those")

        # Filter out already enriched
        to_process = [
            (ticker, meta)
            for ticker, meta in sec_tickers.items()
            if ticker not in enriched_tickers
        ]
        logger.info(f"{len(to_process)} tickers to process after filtering")

        # Apply limit if provided
        if limit:
            to_process = to_process[:limit]
            logger.info(f"Applying limit: processing first {limit} tickers")

        # Process in batches
        for i in range(0, len(to_process), self.batch_size):
            batch = to_process[i : i + self.batch_size]
            tickers_batch = [ticker for ticker, _ in batch]
            logger.info(f"Processing batch {i // self.batch_size + 1}: {tickers_batch}")

            try:
                yfinance_data = self.enrich_batch(tickers_batch)
            except Exception as e:
                logger.error(
                    f"Error fetching data from Yahoo Finance for batch {tickers_batch}: {e}"
                )
                continue

            for ticker, meta in batch:
                data = yfinance_data.get(ticker)
                if not data:
                    logger.warning(
                        f"No data returned from Yahoo Finance for {ticker}, skipping"
                    )
                    continue

                # Add CIK from SEC mapping
                data["cik"] = meta["cik"]

                # Upsert using the DAL
                try:
                    await self.ai_score_dal.upsert(ticker, data)
                    processed += 1
                    logger.info(f"Processed {ticker} successfully")
                except Exception as e:
                    logger.error(f"Error upserting data for {ticker}: {e}")

            # Optional wait between batches to avoid hitting rate limits
            logger.debug("Sleeping for 5 seconds between batches")
            time.sleep(5)

        logger.info(f"Universe build complete, total tickers processed: {processed}")
        return processed
