"""
LangChain tool definitions for the G-Alpha research agent.

Each tool wraps a retrieval function from the corpus layer, converting between
the string-based interface LangChain expects and the typed Python interfaces
the retrieval modules expose.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime

from langchain.tools import Tool

from galpha.equity_intelligence.retrieval import retrieve_insider_transactions
from galpha.sec_filings.retrieval import get_historical_sections

logger = logging.getLogger(__name__)

_MAX_SECTION_CHARS = 4000
_DATE_FMT = "%Y-%m-%d"


def _get_10k_section(input_json: str) -> str:
    """Fetch 10-K section text for a ticker from the SEC Filings corpus.

    Args:
        input_json: JSON string with keys:
            - ticker (str): Equity ticker, e.g. "AAPL"
            - section (str): Section ID, e.g. "1A", "7", "8"
            - n_records (int, optional): Number of filings to retrieve (default 3)
            - start_date (str, optional): ISO date "YYYY-MM-DD"
            - end_date (str, optional): ISO date "YYYY-MM-DD"
    """
    try:
        params = json.loads(input_json)
    except json.JSONDecodeError:
        return "Error: input must be a valid JSON string."

    ticker = params.get("ticker", "")
    section = params.get("section", "1A")
    n_records = int(params.get("n_records", 3))
    start_date = (
        datetime.strptime(params["start_date"], _DATE_FMT) if "start_date" in params else None
    )
    end_date = (
        datetime.strptime(params["end_date"], _DATE_FMT) if "end_date" in params else None
    )

    docs = get_historical_sections(
        ticker=ticker,
        section=section,
        n_records=n_records,
        start_date=start_date,
        end_date=end_date,
    )

    if not docs:
        return f"No 10-K section {section} data found for {ticker}."

    section_key = f"section{section}"
    parts = []
    for doc in docs:
        date_str = doc.get("date", "unknown date")
        if hasattr(date_str, "strftime"):
            date_str = date_str.strftime(_DATE_FMT)
        text = doc.get(section_key, "")
        parts.append(f"[{ticker} — {date_str}]\n{text}")

    combined = "\n\n---\n\n".join(parts)
    if len(combined) > _MAX_SECTION_CHARS:
        combined = combined[:_MAX_SECTION_CHARS] + "\n\n[truncated]"

    return combined


def _get_insider_transactions(input_json: str) -> str:
    """Fetch insider transaction history for a ticker from the EquityIntelligence corpus.

    Args:
        input_json: JSON string with keys:
            - ticker (str): Equity ticker, e.g. "TSLA"
            - person_name (str, optional): Filter to a specific insider, e.g. "Musk Elon"
            - start_date (str, optional): ISO date "YYYY-MM-DD"
            - end_date (str, optional): ISO date "YYYY-MM-DD"
            - num_transactions (int, optional): Max transactions to return
    """
    try:
        params = json.loads(input_json)
    except json.JSONDecodeError:
        return "Error: input must be a valid JSON string."

    ticker = params.get("ticker", "")
    person_name = params.get("person_name", None)
    start_date = (
        datetime.strptime(params["start_date"], _DATE_FMT) if "start_date" in params else None
    )
    end_date = (
        datetime.strptime(params["end_date"], _DATE_FMT) if "end_date" in params else None
    )
    num_transactions = params.get("num_transactions", None)

    df = retrieve_insider_transactions(
        ticker=ticker,
        person_name=person_name,
        start_date=start_date,
        end_date=end_date,
        num_transactions=num_transactions,
    )

    if df.empty:
        return f"No insider transaction records found for {ticker}."

    lines = []
    for _, row in df.iterrows():
        person = row.get("_id", "Unknown")
        transactions = row.get("transactions", [])
        for tx in transactions:
            date = tx.get("date", "")
            if hasattr(date, "strftime"):
                date = date.strftime(_DATE_FMT)
            amount = tx.get("transaction_amount", 0)
            direction = "BUY" if amount >= 0 else "SELL"
            lines.append(f"{person} | {date} | {direction} | ${abs(amount):,.0f}")

    return "\n".join(lines) if lines else f"No transactions to display for {ticker}."


get_10k_section_tool = Tool(
    name="get_10k_section",
    func=_get_10k_section,
    description=(
        "Retrieve 10-K filing section text for a given equity ticker from the SEC corpus. "
        "Use this to access fundamental disclosures: risk factors (section 1A), "
        "MD&A narratives (section 7), financial statements (section 8), "
        "and all other Regulation S-K sections. "
        "Input: JSON string with 'ticker' (required), 'section' (required), "
        "'n_records' (optional, default 3), 'start_date' and 'end_date' (optional, YYYY-MM-DD)."
    ),
)

get_insider_transactions_tool = Tool(
    name="get_insider_transactions",
    func=_get_insider_transactions,
    description=(
        "Retrieve SEC Form 4/5 insider transaction disclosures for a given equity ticker. "
        "Use this to surface executive conviction signals: who bought or sold, how much, and when. "
        "Correlate with 10-K filing dates to identify insider activity around key disclosures. "
        "Input: JSON string with 'ticker' (required), 'person_name' (optional), "
        "'start_date' and 'end_date' (optional, YYYY-MM-DD), 'num_transactions' (optional)."
    ),
)

TOOLS = [get_10k_section_tool, get_insider_transactions_tool]
