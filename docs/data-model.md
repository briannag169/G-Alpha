# Data Model Reference: G-Alpha SEC Filing Intelligence Pipeline

## Databases

| Database | Purpose |
|----------|---------|
| `10K_Reports` | Annual 10-K filing sections, one collection per Regulation S-K section |
| `EquityIntelligence` | SEC Form 4/5 insider transaction disclosures, one collection per ticker |

---

## 10K_Reports Database

### Collections

One collection per section, named by the official Regulation S-K designation:

| Collection Name | Section ID | Content |
|-----------------|------------|---------|
| `1 - Business` | `1` | Company overview, products, markets, employees |
| `1A - Risk Factors` | `1A` | Material risk disclosures |
| `1B - Unresolved Staff Comments` | `1B` | Outstanding SEC comment letters |
| `2 - Properties` | `2` | Physical facilities and real estate |
| `3 - Legal Proceedings` | `3` | Material litigation |
| `4 - Mine Safety Disclosures` | `4` | Mining safety (N/A for most tech/finance companies) |
| `5 - Market for Registrant's Common Equity...` | `5` | Shareholder information, buybacks |
| `6 - Selected Financial Data` | `6` | 5-year financial summary (eliminated Feb 2021) |
| `7 - Management's Discussion and Analysis...` | `7` | MD&A — management's narrative on results |
| `7A - Quantitative and Qualitative Disclosures...` | `7A` | Market risk exposure |
| `8 - Financial Statements and Supplementary Data` | `8` | Full audited financials |
| `9 - Changes in and Disagreements with Accountants` | `9` | Auditor changes |
| `9A - Controls and Procedures` | `9A` | Internal controls assessment (SOX 302/404) |
| `9B - Other Information` | `9B` | Miscellaneous disclosures |
| `10 - Directors, Executive Officers...` | `10` | Board and officer bios |
| `11 - Executive Compensation` | `11` | Pay tables, equity awards |
| `12 - Security Ownership...` | `12` | Beneficial ownership by insiders and large holders |
| `13 - Certain Relationships and Related Transactions` | `13` | Related-party transactions |
| `14 - Principal Accountant Fees and Services` | `14` | Audit fees |

### Document Schema

```json
{
  "_id":        "ObjectId (MongoDB internal, excluded from projections)",
  "ticker":     "string  — uppercase equity ticker, e.g. 'AAPL'",
  "date":       "datetime — period-of-report date, stored as BSON Date",
  "ticker_date":"string  — composite key: '{TICKER}_{YYYY-MM-DD}', e.g. 'AAPL_2023-09-30'",
  "section{ID}":"string  — section text content, e.g. 'section1A', 'section7', 'section9A'"
}
```

**Field notes:**
- `ticker` is always uppercase. Normalised on ingestion via `ticker.upper()`.
- `date` is stored as a Python `datetime` object (BSON Date type in MongoDB), enabling native `$gte`/`$lte` range queries without string parsing.
- `ticker_date` carries a **unique index** — the primary idempotency mechanism.
- The section text field name follows the pattern `section{section_id}` exactly, e.g. `section1`, `section1A`, `section7A`. Retrieval projections use `f"section{section}"` to match this convention.

### Indexes

| Collection | Field | Type | Purpose |
|------------|-------|------|---------|
| All 19 collections | `ticker_date` | Unique | Prevents duplicate ingestion |

The `ticker_date` index is created on first insert via `collection.create_index("ticker_date", unique=True)`. Subsequent calls are no-ops (MongoDB is idempotent on index creation for existing identical indexes).

---

## EquityIntelligence Database

### Collections

One collection per equity ticker, named by uppercase ticker symbol (e.g., `AAPL`, `MSFT`, `TSLA`). Collections are created automatically on first insert.

### Document Schema

```json
{
  "_id":                                "ObjectId (MongoDB internal)",
  "periodOfReport":                     "datetime — transaction date, BSON Date",
  "issuerCik":                          "string  — SEC Central Index Key for the company",
  "issuerTicker":                       "string  — uppercase ticker from the filing",
  "reportingPerson":                    "string  — insider name as filed, e.g. 'Cook Timothy D'",
  "securityTitle":                      "string  — e.g. 'Common Stock', 'Restricted Stock Unit'",
  "codingCode":                         "string  — SEC transaction code: P=Purchase, S=Sale, A=Award, etc.",
  "acquiredDisposed":                   "string  — 'A' (acquired) or 'D' (disposed)",
  "shares":                             "float   — number of shares transacted",
  "sharePrice":                         "float | null — price per share; null for gift/inheritance transactions",
  "total":                              "float   — transaction value = ceil(shares × sharePrice); 0 if sharePrice is null",
  "sharesOwnedFollowingTransaction":    "float   — post-transaction ownership",
  "ticker_date_shares_shareprice_owned":"string  — composite unique key (see below)"
}
```

**Field notes:**
- `sharePrice` is nullable. Gift, inheritance, and award transactions have no cash price. The `total` field defaults to 0 for these cases rather than being omitted, to simplify downstream aggregation.
- `total` uses `math.ceil()` — consistent rounding convention across all records.
- Only non-derivative transactions are stored. Derivative tables (options, warrants) are out of scope for the current pipeline iteration.

### Composite Unique Key

```
ticker_date_shares_shareprice_owned = "{reportingPerson}_{periodOfReport}_{shares}_{sharePrice}_{sharesOwnedFollowingTransaction}"
```

Example: `"Cook Timothy D_2023-08-15_511000_177.82_3280274"`

This key was chosen over a simpler `ticker_date` because a single insider can execute multiple transactions on the same date (e.g., simultaneous sale of multiple grant tranches). The additional `shares`, `sharePrice`, and post-transaction ownership fields make each record uniquely identifiable without relying on MongoDB's internal `_id`.

### Indexes

| Collection | Field | Type | Purpose |
|------------|-------|------|---------|
| All ticker collections | `ticker_date_shares_shareprice_owned` | Unique | Prevents duplicate ingestion |

---

## Date Storage Convention

Both databases store dates as Python `datetime` objects, which MongoDB persists as native BSON Date types. This enables:
- Native `$gte` / `$lte` range operators in queries without string parsing
- Correct sort order on `periodOfReport` and `date` fields
- Compatibility with pandas `pd.to_datetime()` on read-back for DataFrame construction

All dates are ingested via `pd.to_datetime(date_string)` which handles ISO 8601 strings from the SEC API and returns timezone-naive datetimes consistent with the stored values.
