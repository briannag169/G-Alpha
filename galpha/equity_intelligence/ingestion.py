"""
Equity intelligence ingestion pipeline.

Fetches SEC Form 4 / Form 5 insider transaction disclosures via the SEC Insider
Trading API and persists them to MongoDB. Each company is stored in its own
collection within the EquityIntelligence database, keyed by ticker symbol.

These transaction records form a complementary signal layer alongside 10-K
fundamental data, enabling the G-Alpha AI model to correlate insider conviction
with narrative disclosures in regulatory filings.
"""
from __future__ import annotations

import logging
import math

import pandas as pd
from pymongo.errors import DuplicateKeyError
from sec_api import InsiderTradingApi

from galpha.config import settings
from galpha.db import get_database

logger = logging.getLogger(__name__)

_PAGE_SIZE = 100


def fetch_and_store_insider_transactions(ticker: str) -> None:
    """Fetch all available insider transaction disclosures for a ticker and store in MongoDB.

    Paginates through the full SEC filing history for the given equity, flattens
    the nested Form 4 structure, and upserts records into a per-ticker MongoDB
    collection. Re-runs are idempotent — duplicate transactions are detected via a
    composite unique index and silently skipped.

    Args:
        ticker: Uppercase equity ticker symbol (e.g., 'AAPL').
    """
    ticker = ticker.upper()
    db = get_database("EquityIntelligence")
    collection = db[ticker]
    collection.create_index("ticker_date_shares_shareprice_owned", unique=True)

    api = InsiderTradingApi(settings.sec_api_key)
    offset = 0
    total_inserted = 0

    logger.info("Starting equity intelligence ingestion for %s", ticker)

    while True:
        response = api.get_data({
            "query": {"query_string": {"query": f"issuer.tradingSymbol:{ticker}"}},
            "from": str(offset),
            "size": str(_PAGE_SIZE),
            "sort": [{"filedAt": {"order": "desc"}}],
        })

        filings = response.get("transactions", [])
        if not filings:
            break

        transactions = flatten_filings(filings)

        inserted = 0
        for transaction in transactions:
            try:
                collection.insert_one(transaction)
                inserted += 1
            except DuplicateKeyError:
                pass
            except Exception:
                logger.error(
                    "Unexpected error inserting transaction for %s", ticker, exc_info=True
                )

        total_inserted += inserted
        logger.info(
            "Page offset=%d: %d/%d transactions inserted for %s",
            offset, inserted, len(transactions), ticker,
        )

        offset += _PAGE_SIZE
        if len(filings) < _PAGE_SIZE:
            break

    logger.info(
        "Completed equity intelligence ingestion for %s — %d total records inserted",
        ticker, total_inserted,
    )


def flatten_filing(filing: dict) -> list[dict]:
    """Flatten a single SEC Form 4 filing into a list of transaction records.

    Only non-derivative equity transactions are processed; derivative table entries
    are outside the scope of this pipeline's direct equity-transaction focus.

    Args:
        filing: Raw filing dict from the SEC Insider Trading API response.

    Returns:
        List of flat transaction dicts ready for MongoDB insertion.
        Returns an empty list if the filing contains no non-derivative transactions.
    """
    non_derivative = filing.get("nonDerivativeTable", {})
    raw_transactions = non_derivative.get("transactions")
    if not raw_transactions:
        return []

    base = {
        "periodOfReport": pd.to_datetime(filing["periodOfReport"]),
        "issuerCik": filing["issuer"]["cik"],
        "issuerTicker": filing["issuer"]["tradingSymbol"],
        "reportingPerson": filing["reportingOwner"]["name"],
    }

    records = []
    for tx in raw_transactions:
        amounts = tx["amounts"]
        shares = amounts["shares"]
        # pricePerShare is absent for gift/inheritance transactions; default to 0 for total calc.
        price = amounts.get("pricePerShare", None)
        total = math.ceil(shares * (price or 0))

        record = {
            **base,
            "securityTitle": tx["securityTitle"],
            "codingCode": tx["coding"]["code"],
            "acquiredDisposed": amounts["acquiredDisposedCode"],
            "shares": shares,
            "sharePrice": price,
            "total": total,
            "sharesOwnedFollowingTransaction": tx["postTransactionAmounts"][
                "sharesOwnedFollowingTransaction"
            ],
            "ticker_date_shares_shareprice_owned": (
                f"{filing['reportingOwner']['name']}"
                f"_{filing['periodOfReport']}"
                f"_{shares}_{price}"
                f"_{tx['postTransactionAmounts']['sharesOwnedFollowingTransaction']}"
            ),
        }
        records.append(record)

    return records


def flatten_filings(filings: list[dict]) -> list[dict]:
    """Flatten a list of SEC Form 4 filings into a flat list of transaction records.

    Args:
        filings: List of raw filing dicts from the SEC Insider Trading API.

    Returns:
        Flat list of transaction dicts across all filings.
    """
    result = []
    for filing in filings:
        result.extend(flatten_filing(filing))
    return result
