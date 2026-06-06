"""
CLI entry point: ingest a single 10-K filing into the SEC Filings corpus.

Usage:
    python -m scripts.ingest_10k --ticker AAPL --url <EDGAR_URL> --date 2023-09-30

Example:
    python -m scripts.ingest_10k \\
        --ticker CRM \\
        --url https://www.sec.gov/Archives/edgar/data/0001108524/000110852422000008/crm-20210131.htm \\
        --date 2021-01-31
"""
import argparse
import logging
import sys
from datetime import datetime

from galpha.db import close_client
from galpha.sec_filings.ingestion import ingest_10k_filing

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest a 10-K filing into the G-Alpha SEC Filings corpus."
    )
    parser.add_argument("--ticker", required=True, help="Equity ticker symbol (e.g., AAPL)")
    parser.add_argument("--url", required=True, help="Full EDGAR URL to the 10-K document")
    parser.add_argument("--date", required=True, help="Filing period-of-report date (YYYY-MM-DD)")
    args = parser.parse_args()

    try:
        filing_date = datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        print(f"Error: --date must be in YYYY-MM-DD format, got '{args.date}'", file=sys.stderr)
        sys.exit(1)

    ingest_10k_filing(args.url, args.ticker, filing_date)
    close_client()


if __name__ == "__main__":
    main()
