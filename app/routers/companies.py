from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dal.ai_scores import AIScoreDAL
from app.dal.financial_data import FinancialDataDAL
from app.dependencies import get_ai_score_dal, get_financial_data_dal
from app.schemas.companies import CompanyWithFinancialsResponse

router = APIRouter(prefix="/api/companies", tags=["companies"])


@router.get("/scored", response_model=List[CompanyWithFinancialsResponse])
async def get_scored_companies(
    min_score: float = Query(0.0, description="Minimum final score threshold"),
    include_filtered: bool = Query(False, description="Include filtered companies"),
    limit: Optional[int] = Query(None, description="Limit number of results"),
    ai_score_dal: AIScoreDAL = Depends(get_ai_score_dal),
    financial_data_dal: FinancialDataDAL = Depends(get_financial_data_dal),
):
    """
    Get all companies with a final_score greater than the specified threshold,
    including their AI scores and latest financial data.

    Args:
        min_score: Minimum final_score threshold (default: 0.0)
        include_filtered: Whether to include companies where filter_decision=True (default: False)
        limit: Optional limit on number of results
        ai_score_dal: AI Score data access layer
        financial_data_dal: Financial data data access layer

    Returns:
        List of companies with AI scores and financial data
    """
    try:
        # Get all AI scores
        all_scores = await ai_score_dal.get_all_scores()

        # Filter by final_score and filter_decision
        filtered_scores = [
            score
            for score in all_scores
            if score.final_score is not None
            and score.final_score > min_score
            and (include_filtered or not score.filter_decision)
        ]

        # Sort by final_score descending
        filtered_scores.sort(key=lambda x: x.final_score, reverse=True)

        # Apply limit if specified
        if limit:
            filtered_scores = filtered_scores[:limit]

        # Build response with financial data
        results = []
        for score in filtered_scores:
            # Get latest financial data for this ticker
            latest_financial = await financial_data_dal.get_latest_by_ticker(
                score.ticker
            )

            # Build company response
            company_data = {
                # AI Score data
                "id": score.id,
                "ticker": score.ticker,
                "company_name": score.company_name,
                "cik": score.cik,
                "sector": score.sector,
                "industry": score.industry,
                "description": score.description,
                "market_cap": score.market_cap,
                "enterprise_value": score.enterprise_value,
                "employees": score.employees,
                "website": score.website,
                "logo_url": score.logo_url,
                "beta": score.beta,
                "recommendation_key": score.recommendation_key,
                "recommendation_mean": score.recommendation_mean,
                "hq_city": score.hq_city,
                "hq_state": score.hq_state,
                "filter_decision": score.filter_decision,
                "filter_reason": score.filter_reason,
                "pure_play_score": score.pure_play_score,
                "product_integration_score": score.product_integration_score,
                "research_focus_score": score.research_focus_score,
                "partnership_score": score.partnership_score,
                "final_score": score.final_score,
                "reasoning_pure_play": score.reasoning_pure_play,
                "reasoning_product_integration": score.reasoning_product_integration,
                "reasoning_research_focus": score.reasoning_research_focus,
                "reasoning_partnership": score.reasoning_partnership,
                "ai_proportion": score.ai_proportion,
                "business_role": score.business_role,
                "created_at": score.created_at,
                "updated_at": score.updated_at,
                # Financial data (if available)
                "financial_data": None,
            }

            if latest_financial:
                company_data["financial_data"] = {
                    "id": latest_financial.id,
                    "data_type": latest_financial.data_type,
                    "filing_date": latest_financial.filing_date,
                    "fiscal_year": latest_financial.fiscal_year,
                    "fiscal_period": latest_financial.fiscal_period,
                    "period_end_date": latest_financial.period_end_date,
                    # Valuation metrics
                    "pe_ratio": latest_financial.pe_ratio,
                    "ev_to_ebitda": latest_financial.ev_to_ebitda,
                    "price_to_sales": latest_financial.price_to_sales,
                    "price_to_book": latest_financial.price_to_book,
                    "peg_ratio": latest_financial.peg_ratio,
                    # Growth metrics
                    "revenue_growth": latest_financial.revenue_growth,
                    "net_income_growth": latest_financial.net_income_growth,
                    "ebitda_growth": latest_financial.ebitda_growth,
                    "eps_growth": latest_financial.eps_growth,
                    "free_cash_flow_growth": latest_financial.free_cash_flow_growth,
                    # Profitability metrics
                    "gross_margin": latest_financial.gross_margin,
                    "operating_margin": latest_financial.operating_margin,
                    "net_profit_margin": latest_financial.net_profit_margin,
                    "roe": latest_financial.roe,
                    "roa": latest_financial.roa,
                    # Financial health
                    "total_assets": latest_financial.total_assets,
                    "total_liabilities": latest_financial.total_liabilities,
                    "total_equity": latest_financial.total_equity,
                    "cash_and_equivalents": latest_financial.cash_and_equivalents,
                    "total_debt": latest_financial.total_debt,
                    "operating_cash_flow": latest_financial.operating_cash_flow,
                    "cash_flow_positive": latest_financial.cash_flow_positive,
                    "free_cash_flow": latest_financial.free_cash_flow,
                    "debt_to_equity": latest_financial.debt_to_equity,
                    "current_ratio": latest_financial.current_ratio,
                    "quick_ratio": latest_financial.quick_ratio,
                    # Efficiency metrics
                    "asset_turnover": latest_financial.asset_turnover,
                    "inventory_turnover": latest_financial.inventory_turnover,
                    # Market metrics
                    "market_cap": latest_financial.market_cap,
                    "enterprise_value": latest_financial.enterprise_value,
                    "current_price": latest_financial.current_price,
                    "beta": latest_financial.beta,
                    "dividend_yield": latest_financial.dividend_yield,
                    "previous_close": latest_financial.previous_close,
                    "fifty_two_week_high": latest_financial.fifty_two_week_high,
                    "fifty_two_week_low": latest_financial.fifty_two_week_low,
                    # Absolute values
                    "revenue": latest_financial.revenue,
                    "net_income": latest_financial.net_income,
                    "ebitda": latest_financial.ebitda,
                    "shares_outstanding": latest_financial.shares_outstanding,
                    "created_at": latest_financial.created_at,
                    "updated_at": latest_financial.updated_at,
                }

            results.append(company_data)

        return results

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving companies: {str(e)}"
        )


@router.get("/scored/{ticker}", response_model=CompanyWithFinancialsResponse)
async def get_scored_company_by_ticker(
    ticker: str,
    ai_score_dal: AIScoreDAL = Depends(get_ai_score_dal),
    financial_data_dal: FinancialDataDAL = Depends(get_financial_data_dal),
):
    """
    Get a specific company by ticker with AI scores and financial data.

    Args:
        ticker: Stock ticker symbol
        ai_score_dal: AI Score data access layer
        financial_data_dal: Financial data data access layer

    Returns:
        Company with AI scores and financial data
    """
    try:
        # Get AI score for ticker
        scores = await ai_score_dal.get_score(ticker=ticker.upper())

        if not scores:
            raise HTTPException(
                status_code=404, detail=f"Company with ticker {ticker} not found"
            )

        score = scores[0]

        # Check if company has a final_score
        if score.final_score is None or score.final_score <= 0:
            raise HTTPException(
                status_code=404,
                detail=f"Company {ticker} does not have a positive final_score",
            )

        # Get latest financial data
        latest_financial = await financial_data_dal.get_latest_by_ticker(score.ticker)

        # Build response
        company_data = {
            # AI Score data
            "id": score.id,
            "ticker": score.ticker,
            "company_name": score.company_name,
            "cik": score.cik,
            "sector": score.sector,
            "industry": score.industry,
            "description": score.description,
            "market_cap": score.market_cap,
            "enterprise_value": score.enterprise_value,
            "employees": score.employees,
            "website": score.website,
            "logo_url": score.logo_url,
            "beta": score.beta,
            "recommendation_key": score.recommendation_key,
            "recommendation_mean": score.recommendation_mean,
            "hq_city": score.hq_city,
            "hq_state": score.hq_state,
            "filter_decision": score.filter_decision,
            "filter_reason": score.filter_reason,
            "pure_play_score": score.pure_play_score,
            "product_integration_score": score.product_integration_score,
            "research_focus_score": score.research_focus_score,
            "partnership_score": score.partnership_score,
            "final_score": score.final_score,
            "reasoning_pure_play": score.reasoning_pure_play,
            "reasoning_product_integration": score.reasoning_product_integration,
            "reasoning_research_focus": score.reasoning_research_focus,
            "reasoning_partnership": score.reasoning_partnership,
            "ai_proportion": score.ai_proportion,
            "business_role": score.business_role,
            "created_at": score.created_at,
            "updated_at": score.updated_at,
            # Financial data
            "financial_data": None,
        }

        if latest_financial:
            company_data["financial_data"] = {
                "id": latest_financial.id,
                "data_type": latest_financial.data_type,
                "filing_date": latest_financial.filing_date,
                "fiscal_year": latest_financial.fiscal_year,
                "fiscal_period": latest_financial.fiscal_period,
                "period_end_date": latest_financial.period_end_date,
                "pe_ratio": latest_financial.pe_ratio,
                "ev_to_ebitda": latest_financial.ev_to_ebitda,
                "price_to_sales": latest_financial.price_to_sales,
                "price_to_book": latest_financial.price_to_book,
                "peg_ratio": latest_financial.peg_ratio,
                "revenue_growth": latest_financial.revenue_growth,
                "net_income_growth": latest_financial.net_income_growth,
                "ebitda_growth": latest_financial.ebitda_growth,
                "eps_growth": latest_financial.eps_growth,
                "free_cash_flow_growth": latest_financial.free_cash_flow_growth,
                "gross_margin": latest_financial.gross_margin,
                "operating_margin": latest_financial.operating_margin,
                "net_profit_margin": latest_financial.net_profit_margin,
                "roe": latest_financial.roe,
                "roa": latest_financial.roa,
                "total_assets": latest_financial.total_assets,
                "total_liabilities": latest_financial.total_liabilities,
                "total_equity": latest_financial.total_equity,
                "cash_and_equivalents": latest_financial.cash_and_equivalents,
                "total_debt": latest_financial.total_debt,
                "operating_cash_flow": latest_financial.operating_cash_flow,
                "cash_flow_positive": latest_financial.cash_flow_positive,
                "free_cash_flow": latest_financial.free_cash_flow,
                "debt_to_equity": latest_financial.debt_to_equity,
                "current_ratio": latest_financial.current_ratio,
                "quick_ratio": latest_financial.quick_ratio,
                "asset_turnover": latest_financial.asset_turnover,
                "inventory_turnover": latest_financial.inventory_turnover,
                "market_cap": latest_financial.market_cap,
                "enterprise_value": latest_financial.enterprise_value,
                "current_price": latest_financial.current_price,
                "beta": latest_financial.beta,
                "dividend_yield": latest_financial.dividend_yield,
                "previous_close": latest_financial.previous_close,
                "fifty_two_week_high": latest_financial.fifty_two_week_high,
                "fifty_two_week_low": latest_financial.fifty_two_week_low,
                "revenue": latest_financial.revenue,
                "net_income": latest_financial.net_income,
                "ebitda": latest_financial.ebitda,
                "shares_outstanding": latest_financial.shares_outstanding,
                "created_at": latest_financial.created_at,
                "updated_at": latest_financial.updated_at,
            }

        return company_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving company: {str(e)}"
        )
