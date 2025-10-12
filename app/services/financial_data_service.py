import logging
from datetime import date, datetime
from typing import Dict, List, Optional, Set

from sqlalchemy.ext.asyncio import AsyncSession

from app.dal.ai_scores import AIScoreDAL
from app.dal.financial_data import FinancialDataDAL
from app.models.ai_scores import AIScore
from app.models.financial_data import FinancialData
from app.services.company_financial_analyzer_service import CompanyFinancialAnalyzer

logger = logging.getLogger(__name__)


class FinancialDataService:
    """Service layer for financial data operations."""

    def __init__(
        self,
        ai_score_dal: AIScoreDAL,
        financial_data_dal: FinancialDataDAL,
        user_agent: str,
    ):
        """
        Initialize the service.

        Args:
            session: AsyncSession for database operations
            user_agent: User-Agent string for SEC API requests
        """
        self.ai_score_dal = ai_score_dal
        self.financial_data_dal = financial_data_dal
        self.analyzer = CompanyFinancialAnalyzer(user_agent)

    async def sync_all_financial_data(
        self,
        require_final_score: bool = True,
        skip_existing: bool = True,
        force_update_all: bool = False,
        tickers: Optional[List[str]] = None,
    ) -> Dict[str, any]:
        """
        Sync financial data for companies in ai_scores table.

        Args:
            require_final_score: If True, only process companies with a final_score
            skip_existing: If True, skip tickers that already have financial data
            force_update_all: If True, update all tickers even if data exists and hasn't changed
            tickers: Optional list of specific tickers to process. If None, processes all.

        Returns:
            Dictionary with sync statistics
        """
        logger.info("Starting financial data sync")

        stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "updated": 0,
            "created": 0,
            "errors": [],
        }

        try:
            # Get all AI scores
            all_scores = await self.ai_score_dal.get_all_scores()

            # Filter based on criteria
            scores_to_process = []
            for score in all_scores:
                # Filter by specific tickers if provided
                if tickers and score.ticker not in tickers:
                    continue

                # Filter by final_score requirement
                if require_final_score and score.final_score is None:
                    logger.debug(f"Skipping {score.ticker} - no final_score")
                    stats["skipped"] += 1
                    continue

                # Check if CIK exists
                if not score.cik:
                    logger.warning(f"Skipping {score.ticker} - no CIK available")
                    stats["skipped"] += 1
                    continue

                if not score.ticker:
                    logger.warning(
                        f"Skipping {score.company_name} - no ticker available"
                    )
                    stats["skipped"] += 1
                    continue

                scores_to_process.append(score)

            logger.info(f"Processing {len(scores_to_process)} companies")

            # Get existing financial data tickers if we're skipping
            existing_tickers: Set[str] = set()
            if skip_existing and not force_update_all:
                existing_tickers = (
                    await self.financial_data_dal.get_tickers_with_financial_data()
                )
                logger.info(
                    f"Found {len(existing_tickers)} tickers with existing financial data"
                )

            # Process each company
            for score in scores_to_process:
                try:
                    stats["total_processed"] += 1

                    # Skip if already has data and we're not forcing update
                    if (
                        skip_existing
                        and not force_update_all
                        and score.ticker in existing_tickers
                    ):
                        logger.debug(
                            f"Skipping {score.ticker} - already has financial data"
                        )
                        stats["skipped"] += 1
                        continue

                    # Fetch and save financial data
                    result = await self._fetch_and_save_financial_data(
                        score=score, force_update=force_update_all
                    )

                    if result["success"]:
                        stats["successful"] += 1
                        if result["action"] == "created":
                            stats["created"] += 1
                        elif result["action"] == "updated":
                            stats["updated"] += 1
                    else:
                        stats["failed"] += 1
                        stats["errors"].append(
                            {
                                "ticker": score.ticker,
                                "error": result.get("error", "Unknown error"),
                            }
                        )

                except Exception as e:
                    logger.error(f"Error processing {score.ticker}: {e}", exc_info=True)
                    stats["failed"] += 1
                    stats["errors"].append({"ticker": score.ticker, "error": str(e)})

            logger.info(
                f"Financial data sync completed: "
                f"{stats['successful']} successful, "
                f"{stats['failed']} failed, "
                f"{stats['skipped']} skipped"
            )

            return stats

        except Exception as e:
            logger.error(
                f"Critical error in sync_all_financial_data: {e}", exc_info=True
            )
            stats["errors"].append({"error": f"Critical error: {str(e)}"})
            return stats

    async def _fetch_and_save_financial_data(
        self, score: AIScore, force_update: bool = False
    ) -> Dict[str, any]:
        """
        Fetch financial data from SEC and save to database.

        Args:
            score: AIScore object
            force_update: If True, update even if data hasn't changed

        Returns:
            Dictionary with result information
        """
        try:
            logger.info(
                f"Fetching financial data for {score.ticker} (CIK: {score.cik})"
            )

            # Fetch financial data using the analyzer
            analysis = self.analyzer.analyze_company(ticker=score.ticker, cik=score.cik)

            if not analysis:
                return {
                    "success": False,
                    "error": "Failed to fetch financial data from SEC",
                }

            # Check if we got any meaningful data
            if not self._has_meaningful_data(analysis):
                return {
                    "success": False,
                    "error": "No meaningful financial data available",
                }

            # Prepare data for database
            financial_data = self._prepare_financial_data(analysis, score.id)

            # Check if this exact data already exists
            if not force_update:
                existing = await self.financial_data_dal.get_by_ticker_and_period(
                    ticker=score.ticker,
                    fiscal_year=financial_data["fiscal_year"],
                    fiscal_period=financial_data["fiscal_period"],
                )

                if existing and self._data_is_identical(existing, financial_data):
                    logger.debug(f"Data for {score.ticker} is identical, skipping")
                    return {
                        "success": True,
                        "action": "skipped",
                        "reason": "identical_data",
                    }

            # Upsert the data
            result = await self.financial_data_dal.upsert(
                ticker=score.ticker,
                ai_score_id=score.id,
                fiscal_year=financial_data["fiscal_year"],
                fiscal_period=financial_data["fiscal_period"],
                data=financial_data,
            )

            if result:
                action = "updated" if result.id else "created"
                logger.info(f"Successfully {action} financial data for {score.ticker}")
                return {
                    "success": True,
                    "action": action,
                    "financial_data_id": result.id,
                }
            else:
                return {"success": False, "error": "Database upsert failed"}

        except Exception as e:
            logger.error(
                f"Error fetching/saving financial data for {score.ticker}: {e}"
            )
            return {"success": False, "error": str(e)}

    def _has_meaningful_data(self, analysis: Dict) -> bool:
        """Check if the analysis contains meaningful financial data."""
        # Check if we have at least revenue or total assets
        has_revenue = analysis.get("valuation_metrics", {}).get(
            "price_to_sales"
        ) is not None or "revenue" in str(analysis.get("profitability_metrics", {}))
        has_assets = (
            analysis.get("financial_health", {}).get("total_assets") is not None
        )

        return has_revenue or has_assets

    def _prepare_financial_data(self, analysis: Dict, ai_score_id: int) -> Dict:
        """
        Convert analyzer output to database format.

        Args:
            analysis: Output from CompanyFinancialAnalyzer.analyze_company()
            ai_score_id: Foreign key to AIScore

        Returns:
            Dictionary ready for database insertion
        """
        # Determine fiscal year and period
        fiscal_year = None
        fiscal_period = None

        if analysis.get("data_type") == "quarterly":
            # Parse from "FY2025 Q2" format
            period_str = analysis.get("most_recent_period", "")
            if period_str:
                parts = period_str.split()
                if len(parts) == 2:
                    fiscal_year = int(parts[0].replace("FY", ""))
                    fiscal_period = parts[1]
        else:
            fiscal_year = analysis.get("most_recent_fiscal_year")
            fiscal_period = "FY"

        # Parse filing date (use current date if not available)
        filing_date = date.today()

        # Parse period end date if available
        period_end_date = None
        if analysis.get("data_type") == "quarterly" and analysis.get(
            "most_recent_quarter"
        ):
            end_date_str = analysis["most_recent_quarter"].get("end_date")
            if end_date_str:
                period_end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

        # Build the financial data dictionary
        data = {
            "cik": analysis.get("cik"),
            "data_type": analysis.get("data_type"),
            "filing_date": filing_date,
            "fiscal_year": fiscal_year,
            "fiscal_period": fiscal_period,
            "period_end_date": period_end_date,
        }

        # Add valuation metrics
        valuation = analysis.get("valuation_metrics", {})
        data.update(
            {
                "pe_ratio": valuation.get("pe_ratio"),
                "ev_to_ebitda": valuation.get("ev_to_ebitda"),
                "price_to_sales": valuation.get("price_to_sales"),
                "price_to_book": valuation.get("price_to_book"),
                "peg_ratio": valuation.get("peg_ratio"),
            }
        )

        # Add growth metrics (handle different key names)
        growth = analysis.get("growth_metrics", {})
        for key, value in growth.items():
            if "revenue_growth" in key:
                data["revenue_growth"] = value
            elif "net_income_growth" in key:
                data["net_income_growth"] = value
            elif "ebitda_growth" in key:
                data["ebitda_growth"] = value
            elif "eps_growth" in key:
                data["eps_growth"] = value
            elif "free_cash_flow_growth" in key:
                data["free_cash_flow_growth"] = value

        # Add profitability metrics
        profitability = analysis.get("profitability_metrics", {})
        data.update(
            {
                "gross_margin": profitability.get("gross_margin"),
                "operating_margin": profitability.get("operating_margin"),
                "net_profit_margin": profitability.get("net_profit_margin"),
                "roe": profitability.get("roe"),
                "roa": profitability.get("roa"),
            }
        )

        # Add financial health metrics
        health = analysis.get("financial_health", {})
        data.update(
            {
                "total_assets": health.get("total_assets"),
                "total_liabilities": health.get("total_liabilities"),
                "total_equity": health.get("total_equity"),
                "cash_and_equivalents": health.get("cash_and_equivalents"),
                "total_debt": health.get("total_debt"),
                "operating_cash_flow": health.get("operating_cash_flow"),
                "cash_flow_positive": health.get("cash_flow_positive"),
                "free_cash_flow": health.get("free_cash_flow"),
                "debt_to_equity": health.get("debt_to_equity"),
                "current_ratio": health.get("current_ratio"),
                "quick_ratio": health.get("quick_ratio"),
            }
        )

        # Add efficiency metrics
        efficiency = analysis.get("efficiency_metrics", {})
        data.update(
            {
                "asset_turnover": efficiency.get("asset_turnover"),
                "inventory_turnover": efficiency.get("inventory_turnover"),
            }
        )

        # Add market metrics
        market = analysis.get("market_metrics", {})
        data.update(
            {
                "market_cap": market.get("market_cap"),
                "enterprise_value": market.get("enterprise_value"),
                "current_price": market.get("current_price"),
                "beta": market.get("beta"),
                "dividend_yield": market.get("dividend_yield"),
                "previous_close": market.get("previous_close"),
                "fifty_two_week_high": market.get("52_week_high"),
                "fifty_two_week_low": market.get("52_week_low"),
            }
        )

        # Add absolute values (you may need to extract these from the analyzer)
        # These would need to be added to the analyzer's return values
        # For now, leaving as None
        data.update(
            {
                "revenue": None,  # TODO: Extract from analyzer if available
                "net_income": None,  # TODO: Extract from analyzer if available
                "ebitda": None,  # TODO: Extract from analyzer if available
                "shares_outstanding": None,  # TODO: Extract from analyzer if available
            }
        )

        return data

    def _data_is_identical(self, existing: FinancialData, new_data: Dict) -> bool:
        """
        Check if new data is identical to existing data.

        Args:
            existing: Existing FinancialData record
            new_data: New data dictionary

        Returns:
            True if data is identical, False otherwise
        """
        # Compare key financial metrics
        key_fields = [
            "pe_ratio",
            "ev_to_ebitda",
            "price_to_sales",
            "price_to_book",
            "revenue_growth",
            "net_income_growth",
            "gross_margin",
            "operating_margin",
            "net_profit_margin",
            "total_assets",
            "total_liabilities",
            "total_equity",
            "market_cap",
        ]

        for field in key_fields:
            existing_value = getattr(existing, field, None)
            new_value = new_data.get(field)

            # If both are None, continue
            if existing_value is None and new_value is None:
                continue

            # If one is None and other isn't, they're different
            if existing_value is None or new_value is None:
                return False

            # Compare with small tolerance for floating point
            if isinstance(existing_value, float) and isinstance(new_value, float):
                if abs(existing_value - new_value) > 0.01:
                    return False
            elif existing_value != new_value:
                return False

        return True

    async def update_single_ticker(
        self, ticker: str, force_update: bool = False
    ) -> Dict[str, any]:
        """
        Update financial data for a single ticker.

        Args:
            ticker: Stock ticker symbol
            force_update: If True, update even if data hasn't changed

        Returns:
            Dictionary with result information
        """
        try:
            # Get the AI score for this ticker
            all_scores = await self.ai_score_dal.get_all_scores()
            score = next((s for s in all_scores if s.ticker == ticker), None)

            if not score:
                return {
                    "success": False,
                    "error": f"Ticker {ticker} not found in ai_scores",
                }

            if not score.cik:
                return {"success": False, "error": f"Ticker {ticker} has no CIK"}

            # Fetch and save
            result = await self._fetch_and_save_financial_data(
                score=score, force_update=force_update
            )

            return result

        except Exception as e:
            logger.error(f"Error updating ticker {ticker}: {e}")
            return {"success": False, "error": str(e)}

    async def get_financial_summary(self, ticker: str) -> Optional[Dict]:
        """
        Get a summary of financial data for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dictionary with financial summary or None
        """
        try:
            latest = await self.financial_data_dal.get_latest_by_ticker(ticker)
            if not latest:
                return None

            return {
                "ticker": ticker,
                "fiscal_year": latest.fiscal_year,
                "fiscal_period": latest.fiscal_period,
                "data_type": latest.data_type,
                "filing_date": (
                    latest.filing_date.isoformat() if latest.filing_date else None
                ),
                "valuation": {
                    "pe_ratio": latest.pe_ratio,
                    "ev_to_ebitda": latest.ev_to_ebitda,
                    "price_to_sales": latest.price_to_sales,
                    "price_to_book": latest.price_to_book,
                },
                "profitability": {
                    "gross_margin": latest.gross_margin,
                    "operating_margin": latest.operating_margin,
                    "net_profit_margin": latest.net_profit_margin,
                    "roe": latest.roe,
                    "roa": latest.roa,
                },
                "financial_health": {
                    "total_assets": latest.total_assets,
                    "total_equity": latest.total_equity,
                    "debt_to_equity": latest.debt_to_equity,
                    "current_ratio": latest.current_ratio,
                    "free_cash_flow": latest.free_cash_flow,
                },
                "market": {
                    "market_cap": latest.market_cap,
                    "current_price": latest.current_price,
                    "beta": latest.beta,
                },
            }

        except Exception as e:
            logger.error(f"Error getting financial summary for {ticker}: {e}")
            return None
