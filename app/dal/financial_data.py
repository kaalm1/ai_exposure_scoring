import logging
from datetime import date
from typing import List, Optional

from sqlalchemy import and_, desc, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial_data import FinancialData

logger = logging.getLogger(__name__)


class FinancialDataDAL:
    """Data Access Layer for FinancialData."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_financial_data(self) -> List[FinancialData]:
        """Get all financial data records."""
        result = await self.session.execute(select(FinancialData))
        return result.scalars().all()

    async def get_by_ticker(
        self, ticker: str, limit: Optional[int] = None
    ) -> List[FinancialData]:
        """
        Get all financial data for a specific ticker, ordered by filing date (most recent first).

        Args:
            ticker: Stock ticker symbol
            limit: Optional limit on number of records to return
        """
        query = (
            select(FinancialData)
            .where(FinancialData.ticker == ticker)
            .order_by(desc(FinancialData.filing_date))
        )

        if limit:
            query = query.limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_ai_score_id(
        self, ai_score_id: int, limit: Optional[int] = None
    ) -> List[FinancialData]:
        """
        Get all financial data for a specific AI Score ID.

        Args:
            ai_score_id: Foreign key to AIScore table
            limit: Optional limit on number of records to return
        """
        query = (
            select(FinancialData)
            .where(FinancialData.ai_score_id == ai_score_id)
            .order_by(desc(FinancialData.filing_date))
        )

        if limit:
            query = query.limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_latest_by_ticker(self, ticker: str) -> Optional[FinancialData]:
        """Get the most recent financial data for a ticker."""
        result = await self.session.execute(
            select(FinancialData)
            .where(FinancialData.ticker == ticker)
            .order_by(desc(FinancialData.filing_date))
            .limit(1)
        )
        return result.scalars().first()

    async def get_by_ticker_and_period(
        self,
        ticker: str,
        fiscal_year: int,
        fiscal_period: str,
    ) -> Optional[FinancialData]:
        """
        Get financial data for a specific ticker and fiscal period.

        Args:
            ticker: Stock ticker symbol
            fiscal_year: Fiscal year (e.g., 2025)
            fiscal_period: Fiscal period (e.g., "FY", "Q2")
        """
        result = await self.session.execute(
            select(FinancialData).where(
                and_(
                    FinancialData.ticker == ticker,
                    FinancialData.fiscal_year == fiscal_year,
                    FinancialData.fiscal_period == fiscal_period,
                )
            )
        )
        return result.scalars().first()

    async def get_tickers_with_financial_data(self) -> set[str]:
        """Return a set of tickers that have financial data."""
        result = await self.session.execute(select(FinancialData.ticker).distinct())
        rows = result.scalars().all()
        return set(rows)

    async def get_tickers_needing_update(self, days_threshold: int = 90) -> List[str]:
        """
        Get tickers whose most recent financial data is older than the threshold.

        Args:
            days_threshold: Number of days to consider data as stale
        """
        from sqlalchemy import func

        # Subquery to get the most recent filing date for each ticker
        subquery = (
            select(
                FinancialData.ticker,
                func.max(FinancialData.filing_date).label("latest_date"),
            )
            .group_by(FinancialData.ticker)
            .subquery()
        )

        # Get tickers where the latest date is older than threshold
        result = await self.session.execute(
            select(subquery.c.ticker).where(
                subquery.c.latest_date < func.current_date() - days_threshold
            )
        )

        return result.scalars().all()

    async def upsert(
        self,
        ticker: str,
        ai_score_id: int,
        fiscal_year: int,
        fiscal_period: str,
        data: dict,
    ) -> Optional[FinancialData]:
        """
        Insert or update financial data for a specific ticker and period.

        Args:
            ticker: Stock ticker symbol
            ai_score_id: Foreign key to AIScore table
            fiscal_year: Fiscal year (e.g., 2025)
            fiscal_period: Fiscal period (e.g., "FY", "Q2")
            data: Dictionary with financial metrics (keys matching column names)

        Returns:
            The created or updated FinancialData object, or None on error
        """
        try:
            # Check if record exists for this ticker and period
            result = await self.session.execute(
                select(FinancialData).where(
                    and_(
                        FinancialData.ticker == ticker,
                        FinancialData.fiscal_year == fiscal_year,
                        FinancialData.fiscal_period == fiscal_period,
                    )
                )
            )
            financial_data = result.scalars().first()

            if financial_data:
                # Update existing record
                for key, value in data.items():
                    if hasattr(FinancialData, key):
                        setattr(financial_data, key, value)
                logger.info(
                    f"Updated financial data for {ticker} FY{fiscal_year} {fiscal_period}"
                )
            else:
                # Create new record
                valid_data = {
                    k: v for k, v in data.items() if hasattr(FinancialData, k)
                }
                valid_data.update(
                    {
                        "ticker": ticker,
                        "ai_score_id": ai_score_id,
                        "fiscal_year": fiscal_year,
                        "fiscal_period": fiscal_period,
                    }
                )
                financial_data = FinancialData(**valid_data)
                self.session.add(financial_data)
                logger.info(
                    f"Created financial data for {ticker} FY{fiscal_year} {fiscal_period}"
                )

            await self.session.flush()
            await self.session.commit()
            await self.session.refresh(financial_data)
            return financial_data

        except (IntegrityError, SQLAlchemyError) as e:
            logger.error(
                f"Error upserting financial data for {ticker} "
                f"FY{fiscal_year} {fiscal_period}: {e}"
            )
            await self.session.rollback()
            return None

    async def bulk_upsert(self, financial_records: List[dict]) -> tuple[int, int]:
        """
        Bulk insert or update multiple financial data records.

        Args:
            financial_records: List of dicts, each containing ticker, ai_score_id,
                             fiscal_year, fiscal_period, and other financial data

        Returns:
            Tuple of (success_count, failure_count)
        """
        success_count = 0
        failure_count = 0

        for record in financial_records:
            result = await self.upsert(
                ticker=record["ticker"],
                ai_score_id=record["ai_score_id"],
                fiscal_year=record["fiscal_year"],
                fiscal_period=record["fiscal_period"],
                data=record,
            )
            if result:
                success_count += 1
            else:
                failure_count += 1

        logger.info(
            f"Bulk upsert completed: {success_count} success, {failure_count} failures"
        )
        return success_count, failure_count

    async def delete_by_ticker(self, ticker: str) -> int:
        """
        Delete all financial data for a specific ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Number of records deleted
        """
        try:
            result = await self.session.execute(
                select(FinancialData).where(FinancialData.ticker == ticker)
            )
            records = result.scalars().all()
            count = len(records)

            for record in records:
                await self.session.delete(record)

            await self.session.commit()
            logger.info(f"Deleted {count} financial records for {ticker}")
            return count

        except SQLAlchemyError as e:
            logger.error(f"Error deleting financial data for {ticker}: {e}")
            await self.session.rollback()
            return 0

    async def delete_by_id(self, financial_data_id: int) -> bool:
        """
        Delete a specific financial data record by ID.

        Args:
            financial_data_id: Primary key ID

        Returns:
            True if deleted, False otherwise
        """
        try:
            result = await self.session.execute(
                select(FinancialData).where(FinancialData.id == financial_data_id)
            )
            record = result.scalars().first()

            if not record:
                logger.warning(f"Financial data ID {financial_data_id} not found")
                return False

            await self.session.delete(record)
            await self.session.commit()
            logger.info(f"Deleted financial data ID {financial_data_id}")
            return True

        except SQLAlchemyError as e:
            logger.error(f"Error deleting financial data ID {financial_data_id}: {e}")
            await self.session.rollback()
            return False

    async def get_financial_history(
        self, ticker: str, data_type: Optional[str] = None, limit: int = 10
    ) -> List[FinancialData]:
        """
        Get financial history for a ticker, optionally filtered by data type.

        Args:
            ticker: Stock ticker symbol
            data_type: Optional filter for "annual" or "quarterly"
            limit: Maximum number of records to return

        Returns:
            List of FinancialData records ordered by filing date (newest first)
        """
        query = select(FinancialData).where(FinancialData.ticker == ticker)

        if data_type:
            query = query.where(FinancialData.data_type == data_type)

        query = query.order_by(desc(FinancialData.filing_date)).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()
