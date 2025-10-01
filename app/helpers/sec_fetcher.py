# app/services/sec_filing/sec_fetcher.py

import httpx
from bs4 import BeautifulSoup

BASE_HEADERS = {"User-Agent": "Joanne joanne.tisch@gmail.com"}


async def get_cik_from_ticker(ticker: str) -> str:
    """
    Fetch CIK from SEC's company tickers JSON.

    Args:
        ticker: Stock ticker symbol

    Returns:
        CIK as zero-padded 10-digit string

    Raises:
        ValueError: If ticker not found
    """
    url = "https://www.sec.gov/files/company_tickers.json"
    async with httpx.AsyncClient(headers=BASE_HEADERS, timeout=30.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

        for entry in data.values():
            if entry["ticker"].lower() == ticker.lower():
                return str(entry["cik_str"]).zfill(10)

    raise ValueError(f"Ticker '{ticker}' not found in SEC mapping")


async def fetch_latest_filing_info(cik: str) -> dict:
    """
    Fetch the latest 10-K or 10-Q filing info for a given CIK.

    Args:
        cik: Company CIK number (10 digits, zero-padded)

    Returns:
        dict with keys: filing_type, accession_number, filing_date, doc_url, text

    Raises:
        ValueError: If no recent 10-K/10-Q found
    """
    cik_padded = str(cik).zfill(10)
    submissions_url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
    async with httpx.AsyncClient(headers=BASE_HEADERS, timeout=30.0) as client:
        resp = await client.get(submissions_url)
        resp.raise_for_status()
        data = resp.json()
        filings = data["filings"]["recent"]

        for i, form in enumerate(filings["form"]):
            if form in ["10-K", "S-1", "F-1"]:
                accession = filings["accessionNumber"][i].replace("-", "")
                filing_date = filings["filingDate"][i]
                primary_doc = filings["primaryDocument"][i]

                doc_url = (
                    f"https://www.sec.gov/Archives/edgar/data/"
                    f"{int(cik)}/{accession}/{primary_doc}"
                )

                resp = await client.get(doc_url)
                resp.raise_for_status()

                soup = BeautifulSoup(resp.text, "html.parser")
                filing_text = soup.get_text()

                return {
                    "filing_type": form,
                    "accession_number": filings["accessionNumber"][i],
                    "filing_date": filing_date,
                    "doc_url": doc_url,
                    "text": filing_text,
                }

    raise ValueError(f"No recent 10-K/10-Q found for CIK {cik}")
