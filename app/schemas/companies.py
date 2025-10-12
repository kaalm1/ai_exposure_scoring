from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class FinancialDataResponse(BaseModel):
    """Response model for financial data."""

    id: int
    data_type: str
    filing_date: date
    fiscal_year: Optional[int] = None
    fiscal_period: Optional[str] = None
    period_end_date: Optional[date] = None

    # Valuation metrics
    pe_ratio: Optional[float] = None
    ev_to_ebitda: Optional[float] = None
    price_to_sales: Optional[float] = None
    price_to_book: Optional[float] = None
    peg_ratio: Optional[float] = None

    # Growth metrics
    revenue_growth: Optional[float] = None
    net_income_growth: Optional[float] = None
    ebitda_growth: Optional[float] = None
    eps_growth: Optional[float] = None
    free_cash_flow_growth: Optional[float] = None

    # Profitability metrics
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    net_profit_margin: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None

    # Financial health
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    total_equity: Optional[float] = None
    cash_and_equivalents: Optional[float] = None
    total_debt: Optional[float] = None
    operating_cash_flow: Optional[float] = None
    cash_flow_positive: Optional[bool] = None
    free_cash_flow: Optional[float] = None
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None

    # Efficiency metrics
    asset_turnover: Optional[float] = None
    inventory_turnover: Optional[float] = None

    # Market metrics
    market_cap: Optional[float] = None
    enterprise_value: Optional[float] = None
    current_price: Optional[float] = None
    beta: Optional[float] = None
    dividend_yield: Optional[float] = None
    previous_close: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None

    # Absolute values
    revenue: Optional[float] = None
    net_income: Optional[float] = None
    ebitda: Optional[float] = None
    shares_outstanding: Optional[float] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CompanyWithFinancialsResponse(BaseModel):
    """Response model combining AI scores and financial data."""

    # AI Score fields
    id: int
    ticker: Optional[str] = None
    company_name: str
    cik: Optional[str] = None

    # Classification
    sector: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None

    # Company info
    market_cap: Optional[float] = None
    enterprise_value: Optional[float] = None
    employees: Optional[int] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    beta: Optional[float] = None
    recommendation_key: Optional[str] = None
    recommendation_mean: Optional[float] = None
    hq_city: Optional[str] = None
    hq_state: Optional[str] = None

    # Filter decision
    filter_decision: bool = True
    filter_reason: Optional[str] = None

    # AI exposure scores
    pure_play_score: Optional[float] = None
    product_integration_score: Optional[float] = None
    research_focus_score: Optional[float] = None
    partnership_score: Optional[float] = None
    final_score: Optional[float] = None

    # AI reasoning
    reasoning_pure_play: Optional[str] = None
    reasoning_product_integration: Optional[str] = None
    reasoning_research_focus: Optional[str] = None
    reasoning_partnership: Optional[str] = None

    # AI misc
    ai_proportion: Optional[str] = None
    business_role: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    # Financial data (nested, optional)
    financial_data: Optional[FinancialDataResponse] = None

    class Config:
        from_attributes = True


class AIScoreCreate(BaseModel):
    """Schema for creating AI scores."""

    company_name: str
    ticker: Optional[str] = None
    pure_play_score: float
    product_integration_score: float
    research_focus_score: float
    partnership_score: float
    final_score: float
    reasoning_pure_play: str
    reasoning_product_integration: str
    reasoning_research_focus: str
    reasoning_partnership: str


class AIScoreRead(BaseModel):
    """Schema for reading AI scores."""

    id: int
    company_name: str
    ticker: Optional[str] = None
    cik: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    pure_play_score: Optional[float] = None
    product_integration_score: Optional[float] = None
    research_focus_score: Optional[float] = None
    partnership_score: Optional[float] = None
    final_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
