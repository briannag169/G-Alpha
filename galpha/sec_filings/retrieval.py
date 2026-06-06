"""
10-K filing retrieval interface.

Provides structured access to the historical SEC 10-K corpus stored in MongoDB,
supporting ticker-based and date-range queries across all 19 Regulation S-K sections.
"""
from __future__ import annotations

import logging
from datetime import datetime

from galpha.db import get_database
from galpha.sec_filings.ingestion import SECTION_MAP

logger = logging.getLogger(__name__)


def get_historical_sections(
    ticker: str,
    section: str,
    n_records: int | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[dict]:
    """Retrieve historical 10-K section documents for a given ticker.

    Results are sorted by filing date descending (most recent first).

    Args:
        ticker: Uppercase equity ticker symbol (e.g., 'MSFT').
        section: Section identifier string, e.g. '1A', '7', '9A'.
        n_records: Maximum number of documents to return. None returns all matches.
        start_date: Inclusive lower bound on the filing date.
        end_date: Inclusive upper bound on the filing date.

    Returns:
        List of document dicts containing ticker, date, and the section text field.
        Returns an empty list if the section identifier is not recognized.
    """
    collection_name = SECTION_MAP.get(section)
    if collection_name is None:
        logger.warning("Unknown section identifier '%s' — returning empty result", section)
        return []

    db = get_database("10K_Reports")
    collection = db[collection_name]

    query: dict = {"ticker": ticker.upper()}
    if start_date and end_date:
        query["date"] = {"$gte": start_date, "$lte": end_date}

    projection = {"_id": 0, "ticker": 1, "date": 1, f"section{section}": 1}

    cursor = collection.find(query, projection).sort("date", -1)

    if n_records is not None:
        cursor = cursor.limit(n_records)

    results = list(cursor)
    logger.info(
        "Retrieved %d record(s) for %s section %s", len(results), ticker.upper(), section
    )
    return results
