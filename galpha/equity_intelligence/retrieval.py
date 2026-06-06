"""
Equity intelligence retrieval interface.

Provides aggregated access to SEC Form 4 insider transaction history stored in
MongoDB, supporting filtering by reporting person and date range with grouped
output suitable for downstream quantitative and AI-driven analysis.
"""
from __future__ import annotations

import logging
from datetime import datetime

import pandas as pd

from galpha.db import get_database

logger = logging.getLogger(__name__)


def retrieve_insider_transactions(
    ticker: str,
    person_name: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    num_transactions: int | None = None,
) -> pd.DataFrame:
    """Retrieve insider transaction history for a ticker, grouped by reporting person.

    Executes a MongoDB aggregation pipeline: optional match filters → sort by date
    descending → optional limit → group by reporting person with full transaction history.

    Args:
        ticker: Uppercase equity ticker symbol (e.g., 'TSLA').
        person_name: Filter to a specific insider (e.g., 'Musk Elon'). None returns all.
        start_date: Inclusive lower bound on periodOfReport. Requires end_date.
        end_date: Inclusive upper bound on periodOfReport. Requires start_date.
        num_transactions: Maximum number of individual transactions before grouping.

    Returns:
        DataFrame with columns: _id (reporting person name), transactions (list of
        dicts with transaction_amount and date). Returns an empty DataFrame if no
        records match.
    """
    db = get_database("EquityIntelligence")
    collection = db[ticker.upper()]

    pipeline: list[dict] = []

    match_filter: dict = {}
    if person_name:
        match_filter["reportingPerson"] = person_name
    if start_date and end_date:
        match_filter["periodOfReport"] = {"$gte": start_date, "$lte": end_date}
    if match_filter:
        pipeline.append({"$match": match_filter})

    pipeline.append({"$sort": {"periodOfReport": -1}})

    if num_transactions is not None:
        pipeline.append({"$limit": num_transactions})

    pipeline.append({
        "$group": {
            "_id": "$reportingPerson",
            "transactions": {
                "$push": {
                    "transaction_amount": "$total",
                    "date": "$periodOfReport",
                }
            },
        }
    })

    results = list(collection.aggregate(pipeline))
    df = pd.DataFrame(results)

    logger.info(
        "Retrieved transactions for %d insider(s) in %s", len(df), ticker.upper()
    )
    return df
