import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests
import yfinance as yf


class CompanyFinancialAnalyzer:
    """
    A comprehensive financial analysis class that calculates metrics from
    SEC EDGAR API data (primary) and uses yfinance for market data (stock price, market cap).
    Supports both 10-K (annual) and 10-Q (quarterly) data for newer IPO companies.
    Completely free - no API keys needed!
    """

    SEC_BASE_URL = "https://data.sec.gov"

    def __init__(self, user_agent: str):
        """
        Initialize the analyzer.

        Args:
            user_agent: User-Agent header for SEC (format: "Name email@example.com")
        """
        self.headers = {"User-Agent": user_agent}
        self.company_data = {}
        self.most_recent_year = None
        self.use_quarterly = False
        self.most_recent_quarter = None

    def _format_cik(self, cik: str) -> str:
        """Format CIK to 10-digit format required by SEC."""
        return cik.zfill(10)

    def _get_sec_company_facts(self, cik: str) -> Dict:
        """Retrieve company facts from SEC EDGAR."""
        cik_formatted = self._format_cik(cik)
        url = f"{self.SEC_BASE_URL}/api/xbrl/companyfacts/CIK{cik_formatted}.json"

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching SEC data: {e}")
            return {}

    def _get_sec_submissions(self, cik: str) -> Dict:
        """Retrieve company submissions from SEC EDGAR."""
        cik_formatted = self._format_cik(cik)
        url = f"{self.SEC_BASE_URL}/submissions/CIK{cik_formatted}.json"

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching SEC submissions: {e}")
            return {}

    def _get_market_data(self, ticker: str) -> Dict:
        """Get market data from Yahoo Finance using yfinance."""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            return {
                "price": info.get("currentPrice") or info.get("regularMarketPrice"),
                "market_cap": info.get("marketCap"),
                "beta": info.get("beta"),
                "dividend_yield": info.get("dividendYield"),
                "shares_outstanding": info.get("sharesOutstanding"),
                "previous_close": info.get("previousClose"),
                "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
                "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
            }
        except Exception as e:
            print(f"Error fetching Yahoo Finance data: {e}")
            return {}

    def _determine_data_availability(self, facts_data: Dict) -> Dict:
        """
        Determine whether to use annual (10-K) or quarterly (10-Q) data.
        Returns dict with most recent year/quarter and data type to use.
        """
        max_annual_year = None
        max_quarterly_info = {"year": None, "quarter": None, "end_date": None}

        try:
            for taxonomy in facts_data.get("facts", {}).values():
                for concept_data in taxonomy.values():
                    units = concept_data.get("units", {})
                    for unit_type in ["USD", "shares", "pure"]:
                        if unit_type in units:
                            # Check for annual data
                            for item in units[unit_type]:
                                if (
                                    item.get("form") in ["10-K", "10-K/A"]
                                    and item.get("fp") == "FY"
                                ):
                                    fy = item.get("fy")
                                    if fy and (
                                        max_annual_year is None or fy > max_annual_year
                                    ):
                                        max_annual_year = fy

                            # Check for quarterly data (looking for year-to-date entries)
                            for item in units[unit_type]:
                                if item.get("form") in ["10-Q", "10-Q/A"]:
                                    # Look for year-to-date entries (longer periods)
                                    start = item.get("start")
                                    end = item.get("end")
                                    fp = item.get("fp")
                                    fy = item.get("fy")

                                    if start and end and fp and fy:
                                        # Check if this is a year-to-date entry
                                        if start.startswith(
                                            f"{fy - 1}"
                                        ) or start.startswith(f"{fy}"):
                                            if (
                                                max_quarterly_info["end_date"] is None
                                                or end > max_quarterly_info["end_date"]
                                            ):
                                                max_quarterly_info = {
                                                    "year": fy,
                                                    "quarter": fp,
                                                    "end_date": end,
                                                }
        except (KeyError, TypeError):
            pass

        # Decide: use quarterly if no annual data or quarterly is more recent
        use_quarterly = False
        if max_annual_year is None:
            use_quarterly = True
            print(f"No 10-K data found. Using 10-Q quarterly data.")
        elif (
            max_quarterly_info["year"] and max_quarterly_info["year"] > max_annual_year
        ):
            use_quarterly = True
            print(
                f"Quarterly data (FY{max_quarterly_info['year']} {max_quarterly_info['quarter']}) is more recent than annual data (FY{max_annual_year}). Using 10-Q data."
            )
        else:
            print(f"Using 10-K annual data (FY{max_annual_year}).")

        return {
            "use_quarterly": use_quarterly,
            "most_recent_year": max_annual_year,
            "most_recent_quarter": max_quarterly_info if use_quarterly else None,
        }

    def _extract_concept_values(
        self,
        facts_data: Dict,
        concept: str,
        taxonomy: str = "us-gaap",
        periods: int = 3,
    ) -> List[Dict]:
        """
        Extract historical values for a given concept.
        Uses either annual (10-K) or quarterly (10-Q) data based on availability.
        Only returns data if recent data is available.

        Returns list of dicts with 'val', 'filed', 'fy', 'end' keys, or empty list if no recent data.
        """
        try:
            concept_data = (
                facts_data.get("facts", {}).get(taxonomy, {}).get(concept, {})
            )
            units = concept_data.get("units", {})

            # Try different unit types
            for unit_type in ["USD", "shares", "pure"]:
                if unit_type in units:
                    if self.use_quarterly:
                        # For quarterly data, handle two types:
                        # 1. Income statement items (have start/end dates) - use YTD entries
                        # 2. Balance sheet items (only end date) - use point-in-time snapshots
                        quarterly_data = []
                        for item in units[unit_type]:
                            if item.get("form") in ["10-Q", "10-Q/A"]:
                                start = item.get("start")
                                end = item.get("end")
                                fy = item.get("fy")
                                fp = item.get("fp")

                                # Balance sheet items (no start date - point in time)
                                if not start and end and fy and fp:
                                    quarterly_data.append(item)
                                # Income statement items (start and end - look for YTD)
                                elif start and end and fy and fp:
                                    if "-01-01" in start or "-01-" in start[:8]:
                                        quarterly_data.append(item)

                        if quarterly_data:
                            # Sort by end date descending
                            quarterly_data.sort(
                                key=lambda x: x.get("end", ""), reverse=True
                            )

                            # Check if most recent matches our target
                            if quarterly_data and len(quarterly_data) > 0:
                                most_recent = quarterly_data[0]
                                most_recent_fy = most_recent.get("fy")
                                most_recent_fp = most_recent.get("fp")

                                # Only return if it matches the most recent quarter we found
                                if (
                                    most_recent_fy == self.most_recent_quarter["year"]
                                    and most_recent_fp
                                    == self.most_recent_quarter["quarter"]
                                ):
                                    return quarterly_data[:periods]
                    else:
                        # Annual data logic (original)
                        annual_data = [
                            item
                            for item in units[unit_type]
                            if item.get("form") in ["10-K", "10-K/A"]
                            and item.get("fp") == "FY"
                        ]

                        if annual_data:
                            # Sort by end date descending to get most recent first
                            annual_data.sort(
                                key=lambda x: x.get("end", ""), reverse=True
                            )

                            # Check if most recent data is from 2025 or the most recent year
                            if annual_data and len(annual_data) > 0:
                                most_recent_fy = annual_data[0].get("fy")

                                # Only return if data is from 2025 or matches the most recent year
                                if (
                                    most_recent_fy == 2025
                                    or most_recent_fy == self.most_recent_year
                                ):
                                    return annual_data[:periods]
                                else:
                                    # Data is too old, skip this concept
                                    return []

            return []
        except (KeyError, IndexError, TypeError):
            return []

    def _get_latest_value(self, values_list: List[Dict]) -> Optional[float]:
        """Get the most recent value from a list of historical values."""
        if values_list and len(values_list) > 0:
            return values_list[0].get("val")
        return None

    def _calculate_growth_rate(
        self, current: float, previous: float
    ) -> Optional[float]:
        """Calculate YoY growth rate as percentage."""
        if previous and previous != 0 and current is not None:
            return ((current - previous) / abs(previous)) * 100
        return None

    def _calculate_margin(
        self, numerator: float, denominator: float
    ) -> Optional[float]:
        """Calculate margin as percentage."""
        if denominator and denominator != 0 and numerator is not None:
            return (numerator / denominator) * 100
        return None

    def _calculate_ratio(self, numerator: float, denominator: float) -> Optional[float]:
        """Calculate a simple ratio."""
        if denominator and denominator != 0 and numerator is not None:
            return numerator / denominator
        return None

    def _get_financial_data(self, sec_facts: Dict) -> Dict:
        """
        Extract all necessary financial statement line items from SEC data.
        Only includes concepts with recent data (either 10-K or 10-Q).
        """
        data = {}

        # Income Statement items
        concepts = {
            "revenue": [
                "Revenues",
                "RevenueFromContractWithCustomerExcludingAssessedTax",
                "SalesRevenueNet",
            ],
            "cost_of_revenue": ["CostOfRevenue", "CostOfGoodsAndServicesSold"],
            "gross_profit": ["GrossProfit"],
            "operating_expenses": ["OperatingExpenses", "OperatingIncomeLoss"],
            "operating_income": ["OperatingIncomeLoss"],
            "interest_expense": ["InterestExpense"],
            "income_before_tax": [
                "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"
            ],
            "income_tax": ["IncomeTaxExpenseBenefit"],
            "net_income": ["NetIncomeLoss", "ProfitLoss"],
            "ebitda": ["EarningsBeforeInterestTaxesDepreciationAndAmortization"],
            "depreciation_amortization": [
                "DepreciationDepletionAndAmortization",
                "DepreciationAndAmortization",
            ],
            # Balance Sheet items
            "total_assets": ["Assets"],
            "current_assets": ["AssetsCurrent"],
            "cash": ["CashAndCashEquivalentsAtCarryingValue", "Cash"],
            "accounts_receivable": ["AccountsReceivableNetCurrent"],
            "inventory": ["InventoryNet"],
            "total_liabilities": ["Liabilities"],
            "current_liabilities": ["LiabilitiesCurrent"],
            "accounts_payable": ["AccountsPayableCurrent"],
            "short_term_debt": ["LongTermDebtCurrent", "ShortTermBorrowings"],
            "long_term_debt": ["LongTermDebtNoncurrent"],
            "total_equity": [
                "StockholdersEquity",
                "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
            ],
            # Cash Flow Statement items
            "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
            "capex": ["PaymentsToAcquirePropertyPlantAndEquipment"],
            "investing_cash_flow": ["NetCashProvidedByUsedInInvestingActivities"],
            "financing_cash_flow": ["NetCashProvidedByUsedInFinancingActivities"],
            # Shares
            "shares_outstanding": [
                "CommonStockSharesOutstanding",
                "CommonStockSharesIssued",
            ],
            "weighted_average_shares": [
                "WeightedAverageNumberOfSharesOutstandingBasic"
            ],
            "diluted_shares": ["WeightedAverageNumberOfDilutedSharesOutstanding"],
        }

        # Extract values for each concept (try multiple GAAP terms)
        # Only keep concepts with recent data
        for key, concept_list in concepts.items():
            for concept in concept_list:
                values = self._extract_concept_values(sec_facts, concept, periods=3)
                if values:  # Only add if we got recent data
                    data[key] = values
                    break
            if key not in data:
                data[key] = []

        return data

    def _calculate_ebitda(
        self, net_income: float, interest: float, tax: float, depreciation: float
    ) -> Optional[float]:
        """Calculate EBITDA from components."""
        if net_income is not None:
            ebitda = net_income
            if interest:
                ebitda += interest
            if tax:
                ebitda += tax
            if depreciation:
                ebitda += depreciation
            return ebitda
        return None

    def analyze_company(self, ticker: str, cik: str) -> Dict:
        """
        Perform comprehensive financial analysis on a company.
        Automatically detects and uses either 10-K (annual) or 10-Q (quarterly) data.

        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')
            cik: CIK number

        Returns:
            Dictionary containing all calculated financial metrics
        """
        results = {
            "ticker": ticker,
            "cik": cik,
            "timestamp": datetime.now().isoformat(),
            "valuation_metrics": {},
            "growth_metrics": {},
            "profitability_metrics": {},
            "financial_health": {},
            "efficiency_metrics": {},
            "market_metrics": {},
        }

        # Fetch SEC data
        sec_facts = self._get_sec_company_facts(cik)
        sec_submissions = self._get_sec_submissions(cik)

        if not sec_facts:
            print("Failed to retrieve SEC data")
            return results

        # Determine whether to use annual or quarterly data
        data_info = self._determine_data_availability(sec_facts)
        self.use_quarterly = data_info["use_quarterly"]
        self.most_recent_year = data_info["most_recent_year"]
        self.most_recent_quarter = data_info["most_recent_quarter"]

        if self.use_quarterly:
            results["data_type"] = "quarterly"
            results["most_recent_period"] = (
                f"FY{self.most_recent_quarter['year']} {self.most_recent_quarter['quarter']}"
            )
        else:
            results["data_type"] = "annual"
            results["most_recent_fiscal_year"] = self.most_recent_year

        # Extract company info
        if sec_submissions:
            results["company_name"] = sec_submissions.get("name")
            results["sic"] = sec_submissions.get("sic")
            results["sic_description"] = sec_submissions.get("sicDescription")

        # Get all financial data (only with recent period data)
        fin_data = self._get_financial_data(sec_facts)

        # Get current period values (index 0)
        current = {}
        previous = {}

        for key, values in fin_data.items():
            current[key] = self._get_latest_value(values)
            if len(values) >= 2:
                previous[key] = values[1].get("val")

        # Get market data from Yahoo Finance (completely free!)
        market_data = self._get_market_data(ticker)
        current_price = market_data.get("price")
        market_cap = market_data.get("market_cap")
        shares_outstanding_market = market_data.get("shares_outstanding")

        # Use shares from market data if available, otherwise from SEC
        shares = (
            shares_outstanding_market
            or current.get("shares_outstanding")
            or current.get("weighted_average_shares")
        )

        # === CALCULATE EBITDA if not directly available ===
        if not current.get("ebitda"):
            current["ebitda"] = self._calculate_ebitda(
                current.get("net_income"),
                current.get("interest_expense"),
                current.get("income_tax"),
                current.get("depreciation_amortization"),
            )

        if not previous.get("ebitda"):
            previous["ebitda"] = self._calculate_ebitda(
                previous.get("net_income"),
                previous.get("interest_expense"),
                previous.get("income_tax"),
                previous.get("depreciation_amortization"),
            )

        # === VALUATION METRICS ===
        # P/E Ratio
        if current_price and current.get("net_income") and shares:
            eps = current["net_income"] / shares
            results["valuation_metrics"]["pe_ratio"] = self._calculate_ratio(
                current_price, eps
            )

        # EV/EBITDA
        total_debt = (current.get("long_term_debt") or 0) + (
            current.get("short_term_debt") or 0
        )
        enterprise_value = None
        if market_cap:
            enterprise_value = market_cap + total_debt - (current.get("cash") or 0)
            results["market_metrics"]["enterprise_value"] = enterprise_value

            if current.get("ebitda") and current["ebitda"] > 0:
                results["valuation_metrics"]["ev_to_ebitda"] = self._calculate_ratio(
                    enterprise_value, current["ebitda"]
                )

        # Price to Sales
        if current_price and current.get("revenue") and shares:
            sales_per_share = current["revenue"] / shares
            results["valuation_metrics"]["price_to_sales"] = self._calculate_ratio(
                current_price, sales_per_share
            )

        # Price to Book
        if current_price and current.get("total_equity") and shares:
            book_value_per_share = current["total_equity"] / shares
            results["valuation_metrics"]["price_to_book"] = self._calculate_ratio(
                current_price, book_value_per_share
            )

        # PEG Ratio (P/E divided by earnings growth rate)
        pe_ratio = results["valuation_metrics"].get("pe_ratio")
        if pe_ratio and current.get("net_income") and previous.get("net_income"):
            earnings_growth = self._calculate_growth_rate(
                current["net_income"], previous["net_income"]
            )
            if earnings_growth and earnings_growth > 0:
                results["valuation_metrics"]["peg_ratio"] = pe_ratio / earnings_growth

        # === GROWTH METRICS ===
        growth_label = "YoY" if not self.use_quarterly else "Period-over-Period"

        # Revenue growth
        results["growth_metrics"][
            f"revenue_growth_{growth_label.lower().replace('-', '_')}"
        ] = self._calculate_growth_rate(current.get("revenue"), previous.get("revenue"))

        # Net income growth
        results["growth_metrics"][
            f"net_income_growth_{growth_label.lower().replace('-', '_')}"
        ] = self._calculate_growth_rate(
            current.get("net_income"), previous.get("net_income")
        )

        # EBITDA growth
        results["growth_metrics"][
            f"ebitda_growth_{growth_label.lower().replace('-', '_')}"
        ] = self._calculate_growth_rate(current.get("ebitda"), previous.get("ebitda"))

        # EPS growth
        if shares and current.get("net_income") and previous.get("net_income"):
            if len(fin_data.get("shares_outstanding", [])) >= 2:
                prev_shares = fin_data["shares_outstanding"][1].get("val")
            else:
                prev_shares = shares

            current_eps = current["net_income"] / shares
            previous_eps = previous["net_income"] / prev_shares if prev_shares else None
            results["growth_metrics"][
                f"eps_growth_{growth_label.lower().replace('-', '_')}"
            ] = self._calculate_growth_rate(current_eps, previous_eps)

        # Free cash flow growth
        current_fcf = None
        previous_fcf = None

        if current.get("operating_cash_flow") and current.get("capex"):
            current_fcf = current["operating_cash_flow"] - abs(current["capex"])

        if previous.get("operating_cash_flow") and previous.get("capex"):
            previous_fcf = previous["operating_cash_flow"] - abs(previous["capex"])

        results["growth_metrics"][
            f"free_cash_flow_growth_{growth_label.lower().replace('-', '_')}"
        ] = self._calculate_growth_rate(current_fcf, previous_fcf)

        # === PROFITABILITY METRICS ===
        # Gross margin
        if (
            not current.get("gross_profit")
            and current.get("revenue")
            and current.get("cost_of_revenue")
        ):
            current["gross_profit"] = current["revenue"] - current["cost_of_revenue"]

        results["profitability_metrics"]["gross_margin"] = self._calculate_margin(
            current.get("gross_profit"), current.get("revenue")
        )

        # Operating margin
        results["profitability_metrics"]["operating_margin"] = self._calculate_margin(
            current.get("operating_income"), current.get("revenue")
        )

        # Net profit margin
        results["profitability_metrics"]["net_profit_margin"] = self._calculate_margin(
            current.get("net_income"), current.get("revenue")
        )

        # ROE (Return on Equity)
        results["profitability_metrics"]["roe"] = self._calculate_margin(
            current.get("net_income"), current.get("total_equity")
        )

        # ROA (Return on Assets)
        results["profitability_metrics"]["roa"] = self._calculate_margin(
            current.get("net_income"), current.get("total_assets")
        )

        # === FINANCIAL HEALTH ===
        results["financial_health"]["total_assets"] = current.get("total_assets")
        results["financial_health"]["total_liabilities"] = current.get(
            "total_liabilities"
        )
        results["financial_health"]["total_equity"] = current.get("total_equity")
        results["financial_health"]["cash_and_equivalents"] = current.get("cash")
        results["financial_health"]["total_debt"] = (
            total_debt if total_debt > 0 else None
        )

        # Operating cash flow
        results["financial_health"]["operating_cash_flow"] = current.get(
            "operating_cash_flow"
        )
        ocf = current.get("operating_cash_flow")
        results["financial_health"]["cash_flow_positive"] = ocf > 0 if ocf else None

        # Free cash flow
        if current_fcf is not None:
            results["financial_health"]["free_cash_flow"] = current_fcf

        # Debt to Equity ratio
        results["financial_health"]["debt_to_equity"] = self._calculate_ratio(
            total_debt, current.get("total_equity")
        )

        # Current ratio (current assets / current liabilities)
        results["financial_health"]["current_ratio"] = self._calculate_ratio(
            current.get("current_assets"), current.get("current_liabilities")
        )

        # Quick ratio ((current assets - inventory) / current liabilities)
        if current.get("current_assets") and current.get("current_liabilities"):
            quick_assets = current["current_assets"] - (current.get("inventory") or 0)
            results["financial_health"]["quick_ratio"] = self._calculate_ratio(
                quick_assets, current["current_liabilities"]
            )

        # === EFFICIENCY METRICS ===
        # Asset turnover (revenue / total assets)
        results["efficiency_metrics"]["asset_turnover"] = self._calculate_ratio(
            current.get("revenue"), current.get("total_assets")
        )

        # Inventory turnover (cost of revenue / inventory)
        if current.get("inventory") and current.get("inventory") > 0:
            results["efficiency_metrics"]["inventory_turnover"] = self._calculate_ratio(
                current.get("cost_of_revenue"), current.get("inventory")
            )

        # === MARKET METRICS ===
        results["market_metrics"]["market_cap"] = market_cap
        results["market_metrics"]["current_price"] = current_price
        results["market_metrics"]["beta"] = market_data.get("beta")
        results["market_metrics"]["dividend_yield"] = market_data.get("dividend_yield")
        results["market_metrics"]["previous_close"] = market_data.get("previous_close")
        results["market_metrics"]["52_week_high"] = market_data.get(
            "fifty_two_week_high"
        )
        results["market_metrics"]["52_week_low"] = market_data.get("fifty_two_week_low")

        return results

    def print_analysis(self, analysis: Dict):
        """Pretty print the analysis results."""
        print(f"\n{'=' * 80}")
        print(f"FINANCIAL ANALYSIS: {analysis.get('company_name', analysis['ticker'])}")
        print(f"Ticker: {analysis['ticker']} | CIK: {analysis['cik']}")
        print(f"Data Type: {analysis.get('data_type', 'N/A').upper()}")
        if analysis.get("data_type") == "quarterly":
            print(f"Most Recent Period: {analysis.get('most_recent_period', 'N/A')}")
        else:
            print(
                f"Most Recent Fiscal Year: {analysis.get('most_recent_fiscal_year', 'N/A')}"
            )
        print(f"{'=' * 80}\n")

        sections = [
            ("VALUATION METRICS", "valuation_metrics"),
            ("GROWTH METRICS (%)", "growth_metrics"),
            ("PROFITABILITY METRICS", "profitability_metrics"),
            ("FINANCIAL HEALTH", "financial_health"),
            ("EFFICIENCY METRICS", "efficiency_metrics"),
            ("MARKET METRICS", "market_metrics"),
        ]

        for section_name, section_key in sections:
            print(f"\n{section_name}")
            print("-" * 80)
            section_data = analysis.get(section_key, {})

            for key, value in section_data.items():
                formatted_key = key.replace("_", " ").title()
                if value is not None:
                    if isinstance(value, bool):
                        print(f"{formatted_key:.<50} {'Yes' if value else 'No'}")
                    elif isinstance(value, (int, float)):
                        if (
                            "growth" in key
                            or "margin" in key
                            or "yield" in key
                            or "roe" in key
                            or "roa" in key
                        ):
                            print(f"{formatted_key:.<50} {value:.2f}%")
                        elif abs(value) > 1000000000:  # Billions
                            sign = "-" if value < 0 else ""
                            print(
                                f"{formatted_key:.<50} {sign}${abs(value) / 1e9:.2f}B"
                            )
                        elif abs(value) > 1000000:  # Millions
                            sign = "-" if value < 0 else ""
                            print(
                                f"{formatted_key:.<50} {sign}${abs(value) / 1e6:.2f}M"
                            )
                        else:
                            print(f"{formatted_key:.<50} {value:.2f}")
                    else:
                        print(f"{formatted_key:.<50} {value}")
                else:
                    print(f"{formatted_key:.<50} N/A")

        print(f"\n{'=' * 80}\n")

    def get_summary_dict(self, analysis: Dict) -> Dict:
        """Return a clean summary dictionary with all metrics."""
        return {
            "company_info": {
                "name": analysis.get("company_name"),
                "ticker": analysis["ticker"],
                "cik": analysis["cik"],
                "industry": analysis.get("sic_description"),
                "data_type": analysis.get("data_type"),
                "most_recent_period": analysis.get("most_recent_period")
                or analysis.get("most_recent_fiscal_year"),
            },
            "valuation": analysis["valuation_metrics"],
            "growth": analysis["growth_metrics"],
            "profitability": analysis["profitability_metrics"],
            "financial_health": analysis["financial_health"],
            "efficiency": analysis["efficiency_metrics"],
            "market": analysis["market_metrics"],
        }
