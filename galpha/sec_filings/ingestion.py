"""
10-K filing ingestion pipeline.

Extracts all 19 Regulation S-K sections from a 10-K document via the SEC
Extractor API and persists each section to its dedicated MongoDB collection
in the 10K_Reports database.
"""
from __future__ import annotations

import logging
from datetime import datetime

from pymongo.errors import DuplicateKeyError
from sec_api import ExtractorApi

from galpha.config import settings
from galpha.db import get_database

logger = logging.getLogger(__name__)

# Maps SEC section identifiers to their canonical MongoDB collection names.
SECTION_MAP: dict[str, str] = {
    "1":  "1 - Business",
    "1A": "1A - Risk Factors",
    "1B": "1B - Unresolved Staff Comments",
    "2":  "2 - Properties",
    "3":  "3 - Legal Proceedings",
    "4":  "4 - Mine Safety Disclosures",
    "5":  "5 - Market for Registrant's Common Equity, Related Stockholder Matters and Issuer Purchases of Equity Securities",
    "6":  "6 - Selected Financial Data",
    "7":  "7 - Management's Discussion and Analysis of Financial Condition and Results of Operations",
    "7A": "7A - Quantitative and Qualitative Disclosures about Market Risk",
    "8":  "8 - Financial Statements and Supplementary Data",
    "9":  "9 - Changes in and Disagreements with Accountants on Accounting and Financial Disclosure",
    "9A": "9A - Controls and Procedures",
    "9B": "9B - Other Information",
    "10": "10 - Directors, Executive Officers and Corporate Governance",
    "11": "11 - Executive Compensation",
    "12": "12 - Security Ownership of Certain Beneficial Owners and Management and Related Stockholder Matters",
    "13": "13 - Certain Relationships and Related Transactions, and Director Independence",
    "14": "14 - Principal Accountant Fees and Services",
}


def ingest_10k_filing(url_10k: str, ticker: str, filing_date: datetime) -> None:
    """Extract all 19 sections from a 10-K filing and store each in MongoDB.

    Sections are stored in separate collections within the 10K_Reports database.
    Re-ingesting an existing ticker/date combination is safe — duplicate documents
    are detected via a unique index on ticker_date and skipped with a warning.

    Args:
        url_10k: Full EDGAR URL to the 10-K filing document.
        ticker: Uppercase equity ticker symbol (e.g., 'AAPL').
        filing_date: Period-of-report date for this filing.
    """
    db = get_database("10K_Reports")
    extractor = ExtractorApi(settings.sec_api_key)
    ticker = ticker.upper()
    ticker_date = f"{ticker}_{filing_date.strftime('%Y-%m-%d')}"

    logger.info("Starting 10-K ingestion for %s (%s)", ticker, filing_date.date())

    for section_id, collection_name in SECTION_MAP.items():
        try:
            text = extractor.get_section(url_10k, section_id, "text")
        except Exception:
            logger.error(
                "Failed to extract section %s for %s — skipping",
                section_id, ticker, exc_info=True,
            )
            continue

        document = {
            "ticker": ticker,
            "date": filing_date,
            "ticker_date": ticker_date,
            f"section{section_id}": text,
        }

        collection = db[collection_name]
        collection.create_index("ticker_date", unique=True)

        try:
            collection.insert_one(document)
            logger.info("Inserted section %s for %s", section_id, ticker_date)
        except DuplicateKeyError:
            logger.warning(
                "Section %s for %s already exists — skipping duplicate",
                section_id, ticker_date,
            )
        except Exception:
            logger.error(
                "Unexpected error inserting section %s for %s",
                section_id, ticker_date, exc_info=True,
            )

    logger.info("Completed 10-K ingestion for %s (%s)", ticker, filing_date.date())
