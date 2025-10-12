from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.models.base import Base


class FinancialData(Base):
    __tablename__ = "financial_data"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign key relationship to AIScore
    ai_score_id = Column(
        Integer, ForeignKey("ai_scores.id"), nullable=False, index=True
    )
    ticker = Column(String, index=True, nullable=False)
    cik = Column(String, index=True, nullable=False)

    # Filing information
    data_type = Column(String, nullable=False)  # "annual" or "quarterly"
    filing_date = Column(Date, nullable=False, index=True)  # Date the filing was made
    fiscal_year = Column(Integer, nullable=True, index=True)  # e.g., 2025
    fiscal_period = Column(
        String, nullable=True
    )  # e.g., "FY" for annual, "Q2" for quarterly
    period_end_date = Column(
        Date, nullable=True
    )  # The period end date (e.g., 2025-06-30)

    # === VALUATION METRICS ===
    pe_ratio = Column(Float, nullable=True)
    ev_to_ebitda = Column(Float, nullable=True)
    price_to_sales = Column(Float, nullable=True)
    price_to_book = Column(Float, nullable=True)
    peg_ratio = Column(Float, nullable=True)

    # === GROWTH METRICS (%) ===
    revenue_growth = Column(Float, nullable=True)
    net_income_growth = Column(Float, nullable=True)
    ebitda_growth = Column(Float, nullable=True)
    eps_growth = Column(Float, nullable=True)
    free_cash_flow_growth = Column(Float, nullable=True)

    # === PROFITABILITY METRICS (%) ===
    gross_margin = Column(Float, nullable=True)
    operating_margin = Column(Float, nullable=True)
    net_profit_margin = Column(Float, nullable=True)
    roe = Column(Float, nullable=True)  # Return on Equity
    roa = Column(Float, nullable=True)  # Return on Assets

    # === FINANCIAL HEALTH ===
    total_assets = Column(Float, nullable=True)
    total_liabilities = Column(Float, nullable=True)
    total_equity = Column(Float, nullable=True)
    cash_and_equivalents = Column(Float, nullable=True)
    total_debt = Column(Float, nullable=True)
    operating_cash_flow = Column(Float, nullable=True)
    cash_flow_positive = Column(Boolean, nullable=True)
    free_cash_flow = Column(Float, nullable=True)
    debt_to_equity = Column(Float, nullable=True)
    current_ratio = Column(Float, nullable=True)
    quick_ratio = Column(Float, nullable=True)

    # === EFFICIENCY METRICS ===
    asset_turnover = Column(Float, nullable=True)
    inventory_turnover = Column(Float, nullable=True)

    # === MARKET METRICS ===
    market_cap = Column(Float, nullable=True)
    enterprise_value = Column(Float, nullable=True)
    current_price = Column(Float, nullable=True)
    beta = Column(Float, nullable=True)
    dividend_yield = Column(Float, nullable=True)
    previous_close = Column(Float, nullable=True)
    fifty_two_week_high = Column(Float, nullable=True)
    fifty_two_week_low = Column(Float, nullable=True)

    # === ABSOLUTE VALUES (for reference) ===
    revenue = Column(Float, nullable=True)
    net_income = Column(Float, nullable=True)
    ebitda = Column(Float, nullable=True)
    shares_outstanding = Column(Float, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationship back to AIScore
    ai_score = relationship("AIScore", back_populates="financial_data")

    def __repr__(self):
        return (
            f"<FinancialData(ticker={self.ticker}, "
            f"fiscal_year={self.fiscal_year}, "
            f"fiscal_period={self.fiscal_period}, "
            f"filing_date={self.filing_date})>"
        )
