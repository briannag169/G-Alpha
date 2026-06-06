"""
CLI entry point: ingest insider transaction disclosures for a ticker into MongoDB.

Paginates through the full SEC Form 4/5 filing history for the given equity
and stores all non-derivative transactions in the EquityIntelligence database.

Usage:
    python -m scripts.ingest_insider_trading --ticker TSLA

Example:
    python -m scripts.ingest_insider_trading --ticker AAPL
"""
import argparse
import logging

from galpha.db import close_client
from galpha.equity_intelligence.ingestion import fetch_and_store_insider_transactions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest insider transaction disclosures into the G-Alpha EquityIntelligence corpus."
    )
    parser.add_argument("--ticker", required=True, help="Equity ticker symbol (e.g., TSLA)")
    args = parser.parse_args()

    fetch_and_store_insider_transactions(args.ticker)
    close_client()


if __name__ == "__main__":
    main()
