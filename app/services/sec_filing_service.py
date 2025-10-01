# app/services/sec_filing/sec_filing_service.py

from typing import List, Optional

from app.dal.ai_scores import AIScoreDAL
from app.dal.chunk_summary import ChunkSummaryDAL
from app.dal.filing_summary import FilingSummaryDAL
from app.helpers.chunker import chunk_text
from app.helpers.scorer import score_company
from app.helpers.sec_fetcher import (
    fetch_latest_filing_info,
    get_cik_from_ticker,
)
from app.helpers.summarizer import summarize_chunk
from app.models.ai_scores import AIScore
from app.models.chunk_summary import ChunkSummary
from app.models.filing_summary import FilingSummary
from app.models.schemas import AIScoreCreate


class SECFilingService:
    """
    Service to fetch, process, summarize, and score SEC filings.

    This service:
    - Fetches SEC filings (10-K, 10-Q) from EDGAR
    - Processes and summarizes filings with caching
    - Scores companies on AI exposure
    - Persists both summaries and scores
    """

    def __init__(
        self,
        ai_score_dal: AIScoreDAL,
        filing_summary_dal: FilingSummaryDAL,
        chunk_summary_dal: ChunkSummaryDAL,
    ):
        self.ai_score_dal = ai_score_dal
        self.filing_summary_dal = filing_summary_dal
        self.chunk_summary_dal = chunk_summary_dal

    async def process_and_score_company(
        self,
        company_name: str,
        ticker: Optional[str] = None,
        cik: Optional[str] = None,
        force_refresh: bool = False,
    ) -> dict:
        """
        Main entry point: fetch filing, process/summarize it, score it.

        Args:
            company_name: Name of the company
            ticker: Stock ticker (optional if cik provided)
            cik: CIK number (optional if ticker provided)
            force_refresh: If True, re-process even if summary exists

        Returns:
            dict with scoring results including scores, reasoning, final_score

        Raises:
            ValueError: If neither ticker nor CIK provided, or if ticker not found
        """
        # Step 1: Get CIK if not provided
        if not cik and ticker:
            cik = get_cik_from_ticker(ticker)

        if not cik:
            raise ValueError("Must provide either ticker or CIK")

        # Step 2: Get or create filing summary
        filing_summary = await self._get_or_create_summary(
            cik=cik, ticker=ticker, force_refresh=force_refresh
        )

        # Step 3: Score the company using the summary
        score_result = await score_company(
            company_name=company_name,
            ticker=ticker,
            summary=filing_summary.summary,
        )

        # Step 4: Save the score (if scoring was successful)
        if "error" not in score_result:
            await self._save_score(
                score_result=score_result,
                ticker=ticker,
                cik=cik,
            )

        return score_result

    async def _get_or_create_summary(
        self,
        cik: str,
        ticker: Optional[str],
        force_refresh: bool,
    ) -> FilingSummary:
        """
        Get existing summary from DB or create new one by processing filing.

        Args:
            cik: Company CIK
            ticker: Stock ticker (optional)
            force_refresh: Whether to force re-processing

        Returns:
            FilingSummary object (from DB or newly created)
        """
        # Check if we already have a summary for this CIK
        if not force_refresh:
            existing = await self.filing_summary_dal.get_latest_by_cik(cik)
            if existing and existing.summary:
                return existing

        # Fetch filing from SEC
        filing_info = await fetch_latest_filing_info(cik)

        # Check if this specific filing was already processed
        if not force_refresh:
            existing = await self.filing_summary_dal.get_by_accession(
                filing_info["accession_number"]
            )
            if existing:
                return existing

        ai_score_records: List[AIScore] = await self.ai_score_dal.get_score(
            cik=cik, ticker=ticker
        )
        ai_score_id: int = ai_score_records[0].id
        filing_summary_basic: FilingSummary = (
            await self.filing_summary_dal.upsert_summary(
                FilingSummary(cik=cik, ticker=ticker, ai_score_id=ai_score_id)
            )
        )
        filing_summary_id: int = filing_summary_basic.id
        summary_text = await self.process_filing(
            filing_info["text"], ai_score_id, filing_summary_id
        )

        # Save to database
        filing_summary = FilingSummary(
            cik=cik,
            ticker=ticker,
            filing_type=filing_info["filing_type"],
            accession_number=filing_info["accession_number"],
            filing_date=filing_info["filing_date"],
            raw_text_length=len(filing_info["text"]),
            chunk_count=len(chunk_text(filing_info["text"])),
            summary=summary_text,
        )

        return await self.filing_summary_dal.upsert_summary(filing_summary)

    async def _save_score(
        self,
        score_result: dict,
        ticker: Optional[str],
        cik: Optional[str],
    ) -> None:
        """
        Save the scoring result to the database.

        Maps the new scoring schema to the existing AIScore model.

        Args:
            score_result: Scoring result from score_company()
            ticker: Stock ticker
            cik: Company CIK
        """
        # Map new scoring schema to existing AIScore model fields
        score_obj = AIScore(
            company_name=score_result["company"],
            ticker=ticker,
            cik=cik,
            # Map new scores to existing fields
            pure_play_score=score_result["scores"]["core_dependence"],
            product_integration_score=score_result["scores"]["revenue_from_ai"],
            research_focus_score=score_result["scores"]["strategic_investment"],
            partnership_score=score_result["scores"]["ecosystem_dependence"],
            final_score=score_result["final_score"],
            # Map new reasoning to existing fields
            reasoning_pure_play=score_result["reasoning"]["core_dependence"],
            reasoning_product_integration=score_result["reasoning"]["revenue_from_ai"],
            reasoning_research_focus=score_result["reasoning"]["strategic_investment"],
            reasoning_partnership=score_result["reasoning"]["ecosystem_dependence"],
        )

        await self.ai_score_dal.upsert_model(score_obj)

    async def get_cached_summary(
        self,
        ticker: Optional[str] = None,
        cik: Optional[str] = None,
    ) -> Optional[FilingSummary]:
        """
        Get cached filing summary without processing.

        Args:
            ticker: Stock ticker
            cik: Company CIK

        Returns:
            FilingSummary if found, None otherwise
        """
        if ticker:
            return await self.filing_summary_dal.get_latest_by_ticker(ticker)
        elif cik:
            return await self.filing_summary_dal.get_latest_by_cik(cik)
        return None

    async def process_filing(
        self,
        text: str,
        ai_score_id: Optional[int] = None,
        filing_summary_id: Optional[int] = None,
    ) -> str:
        """
        Process a complete SEC filing text into a final AI-focused summary.

        This function:
        1. Chunks the text into manageable pieces
        2. Summarizes each chunk independently
        3. Combines all summaries
        4. Creates a final compressed summary

        Args:
            text: Raw SEC filing text

        Returns:
            Final compressed summary focused on AI-related content
        """
        # Step 1: Split into chunks
        chunks = chunk_text(text, max_tokens=2000)

        # Step 2: Summarize each chunk
        summaries = []
        for i, chunk in enumerate(chunks):
            summary = await summarize_chunk(chunk)
            chunk_summary = ChunkSummary(
                chunk_index=i,
                summary=summary,
                chunk_text_length=len(chunk),
                ai_score_id=ai_score_id,
                filing_summary_id=filing_summary_id,
            )
            await self.chunk_summary_dal.create_chunk_summary(chunk_summary)
            summaries.append(summary)

        # Step 3: Combine all summaries
        combined = "\n\n".join(summaries)

        # Step 4: Create final compressed summary
        final_summary = await summarize_chunk(combined)

        return final_summary
