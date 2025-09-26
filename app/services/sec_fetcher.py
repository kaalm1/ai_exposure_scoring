import requests

BASE_HEADERS = {"User-Agent": "YourName Contact@yourdomain.com"}


def get_cik_from_ticker(ticker: str) -> str:
    url = "https://www.sec.gov/files/company_tickers.json"
    resp = requests.get(url, headers=BASE_HEADERS).json()
    for entry in resp.values():
        if entry["ticker"].lower() == ticker.lower():
            return str(entry["cik_str"]).zfill(10)
    raise ValueError("Ticker not found in SEC mapping")


def fetch_latest_filing_text(cik: str) -> str:
    submissions_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    resp = requests.get(submissions_url, headers=BASE_HEADERS).json()
    filings = resp["filings"]["recent"]

    for i, form in enumerate(filings["form"]):
        if form in ["10-K", "10-Q"]:
            accession = filings["accessionNumber"][i].replace("-", "")
            doc_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/{filings['primaryDocument'][i]}"
            filing_text = requests.get(doc_url, headers=BASE_HEADERS).text
            return filing_text
    raise ValueError("No recent 10-K/10-Q found")
