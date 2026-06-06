# G-Alpha: SEC Filing Intelligence Pipeline

> **AI-ready financial corpus construction from a decade of SEC regulatory disclosures**

---

## Overview

G-Alpha's SEC Filing Intelligence Pipeline is the data engineering backbone of the [Generative Alpha](https://generativealpha.com) AI platform — a vertical AI company building autonomous financial research agents for institutional and quantitative investment teams.

The pipeline constructs a structured, temporally indexed corpus from two complementary SEC data streams: annual 10-K filings and insider transaction disclosures (Form 4/5). Raw EDGAR documents are extracted, normalized, and persisted to MongoDB Atlas, where they serve as the primary training and retrieval substrate for G-Alpha's GPT-4-based financial AI models. The architecture supports ingesting a full decade of filings across all US30 index constituents — approximately 19 structured sections per 10-K filing, multiplied across 30 companies and 10+ fiscal years.

The retrieval layer feeds a downstream fine-tuning pipeline that generates instruction-following Q&A pairs from high-signal sections (MD&A, Risk Factors, Executive Compensation), enabling the model to reason over corporate narrative alongside quantitative signals. Insider transaction data provides a behavioral conviction layer: correlating disclosed trades with contemporaneous 10-K language is a core feature of G-Alpha's fundamental AI analyst capability.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        SEC EDGAR                                 │
│          (10-K Filings API + Insider Trading API)                │
└───────────────────┬──────────────────────┬───────────────────────┘
                    │                      │
                    ▼                      ▼
      ┌─────────────────────┐   ┌──────────────────────────┐
      │  10-K Filing        │   │  Equity Intelligence     │
      │  Ingestion Pipeline │   │  Ingestion Pipeline      │
      │                     │   │                          │
      │  sec_filings/       │   │  equity_intelligence/    │
      │  ingestion.py       │   │  ingestion.py            │
      │                     │   │                          │
      │  · 19 sections/doc  │   │  · Form 4/5 transactions │
      │  · Paginated fetch  │   │  · Paginated fetch       │
      │  · Idempotent upsert│   │  · Idempotent upsert     │
      └──────────┬──────────┘   └────────────┬─────────────┘
                 │                            │
                 ▼                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                       MongoDB Atlas                             │
│                                                                 │
│  10K_Reports (DB)                EquityIntelligence (DB)        │
│  ├─ 1 - Business                 ├─ AAPL                        │
│  ├─ 1A - Risk Factors            ├─ MSFT                        │
│  ├─ 7 - MD&A                     ├─ TSLA                        │
│  ├─ 8 - Financial Statements     └─ ... (US30 constituents)     │
│  └─ ... (19 collections total)                                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   Retrieval APIs       │
              │                        │
              │  sec_filings/          │
              │  retrieval.py          │
              │                        │
              │  equity_intelligence/  │
              │  retrieval.py          │
              └──────────┬─────────────┘
                         │
              ┌──────────┴──────────────────────────┐
              │                                     │
              ▼                                     ▼
┌─────────────────────────────┐   ┌─────────────────────────────────┐
│  AI Research Agent          │   │  AI Training Corpus             │
│                             │   │                                 │
│  agents/research_agent.py   │   │  · GPT-4 Q&A pair generation    │
│                             │   │  · Instruction fine-tuning      │
│  · GPT-4 Turbo              │   │  · Temporal train/eval splits   │
│  · Tool-calling             │   │  · Insider conviction signals   │
│  · Natural language queries │   │                                 │
└─────────────────────────────┘   └─────────────────────────────────┘
```

---

## Data Sources

### SEC 10-K Filings (Extractor API)
Annual reports filed under Regulation S-K, covering all 19 mandated sections:

| Section | Content |
|---------|---------|
| 1 | Business description |
| 1A | Risk Factors |
| 7 | Management's Discussion & Analysis (MD&A) |
| 8 | Financial Statements & Supplementary Data |
| 9A | Controls & Procedures |
| ... | All 19 sections indexed |

### SEC Insider Transaction Disclosures (Form 4/5)
Executive and director equity transactions filed within 2 business days of execution. Fields captured: reporting person, transaction type (acquire/dispose), shares, price, post-transaction ownership, and filing date.

---

## Setup

**1. Clone and install dependencies**
```bash
git clone <repo-url>
cd galpha
pip install -r requirements.txt
```

**2. Configure environment**
```bash
cp .env.example .env
# Edit .env and fill in your SEC_API_KEY and MONGODB_URI
```

**3. Verify configuration**
```bash
python -c "from galpha.config import settings; print('Config OK')"
```

---

## Usage

### Ingest a 10-K filing
```bash
python -m scripts.ingest_10k \
    --ticker AAPL \
    --url https://www.sec.gov/Archives/edgar/data/320193/000032019323000106/aapl-20230930.htm \
    --date 2023-09-30
```

### Ingest insider transaction history
```bash
python -m scripts.ingest_insider_trading --ticker TSLA
```

### Query the corpus from Python

**Retrieve 10-K sections:**
```python
from datetime import datetime
from galpha.sec_filings.retrieval import get_historical_sections

# Last 5 Risk Factor disclosures for Microsoft
docs = get_historical_sections(
    ticker="MSFT",
    section="1A",
    n_records=5,
    start_date=datetime(2015, 1, 1),
    end_date=datetime(2023, 12, 31),
)
for doc in docs:
    print(doc["date"], doc["section1A"][:200])
```

**Retrieve insider transactions:**
```python
from datetime import datetime
from galpha.equity_intelligence.retrieval import retrieve_insider_transactions

df = retrieve_insider_transactions(
    ticker="TSLA",
    person_name="Musk Elon",
    start_date=datetime(2022, 1, 1),
    end_date=datetime(2023, 12, 31),
)
print(df)
```

---

## Data Schema

### 10K_Reports — document shape
```json
{
  "ticker": "AAPL",
  "date": "2023-09-30T00:00:00",
  "ticker_date": "AAPL_2023-09-30",
  "section1A": "We have identified the following material risk factors..."
}
```
*Each of the 19 sections is stored in its own collection. The `ticker_date` field carries a unique index to enforce idempotency.*

### EquityIntelligence — document shape
```json
{
  "periodOfReport": "2023-08-15T00:00:00",
  "issuerCik": "0000320193",
  "issuerTicker": "AAPL",
  "reportingPerson": "Cook Timothy D",
  "securityTitle": "Common Stock",
  "codingCode": "S",
  "acquiredDisposed": "D",
  "shares": 511000,
  "sharePrice": 177.82,
  "total": 90826020,
  "sharesOwnedFollowingTransaction": 3280274,
  "ticker_date_shares_shareprice_owned": "Cook Timothy D_2023-08-15_511000_177.82_3280274"
}
```

---

## AI Training Corpus Integration

The retrieval layer is consumed by a downstream GPT-4 fine-tuning pipeline that generates instruction-following Q&A pairs from high-signal 10-K sections — MD&A narratives, Risk Factor disclosures, and Executive Compensation tables. Each document carries a `ticker` and `date` field that enables precise temporal slicing: the model is trained on pre-2020 filings and evaluated against 2020–2023 disclosures, simulating real-world deployment where the model must generalize forward in time.

Insider transaction data adds a behavioral layer to fundamental analysis. By correlating disclosed equity transactions with contemporaneous 10-K language, G-Alpha's AI analyst agents can surface conviction signals that are invisible to models trained on financial statements alone — a capability that mirrors how human analysts triangulate regulatory filings with management behavior.

---

## Research Agent

The `galpha.agents` module provides a LangChain tool-calling agent that acts as an autonomous financial analyst. It receives natural language queries, decides which corpus data to retrieve, and synthesises a structured analyst response grounded entirely in actual SEC filings — not model memory.

### How it works

The agent is equipped with two tools backed by the retrieval layer:
- **`get_10k_section`** — fetches any of the 19 Regulation S-K sections for a given ticker and date range
- **`get_insider_transactions`** — fetches Form 4/5 executive transaction disclosures

GPT-4 Turbo decides which tools to call based on the query, retrieves the relevant data from MongoDB, and synthesises a brief analyst report.

### Usage

```python
from galpha.agents.research_agent import run_research_query

result = run_research_query(
    "What were Apple's top 3 risk factors in 2023 "
    "and did any executives sell shares around the filing date?"
)
print(result)
```

**Example output:**
```
Key Findings: Apple's 2023 10-K identified macroeconomic conditions, supply chain
concentration in Asia, and intense competition in all product categories as primary risks.

Insider Activity: Timothy Cook disposed of 511,000 shares in August 2023 at $177.82
($90.8M total), approximately 6 weeks prior to the September 2023 filing date.

Investment Implication: The combination of acknowledged supply chain risk and significant
CEO share disposal ahead of the annual filing warrants close monitoring of near-term
guidance.
```

### Agent design rationale

See [docs/agent-design.md](docs/agent-design.md) for full design decisions: why tool-calling over a fixed chain, tool input/output design, model selection, and the extension path to MongoDB Atlas Vector Search.

---

## Deployment: Continuous Pipeline on AWS EC2

The pipeline is designed to run as a long-lived background service on an EC2 instance, continuously ingesting new filings as companies publish them.

### EC2 Setup

**1. Launch and configure instance**
```bash
# Recommended: t3.medium, Amazon Linux 2023, 20 GB gp3 EBS
# Attach an IAM role with SSM access for secret retrieval (avoids .env on disk)

ssh -i your-key.pem ec2-user@<instance-ip>
sudo dnf install python3.11 python3.11-pip git -y
git clone <repo-url> /opt/galpha && cd /opt/galpha
pip3.11 install -r requirements.txt
```

**2. Store secrets in AWS Systems Manager Parameter Store**
```bash
aws ssm put-parameter --name /galpha/SEC_API_KEY --value "<key>" --type SecureString
aws ssm put-parameter --name /galpha/MONGODB_URI --value "<uri>" --type SecureString
```
Pull them at runtime in a launch wrapper script rather than storing `.env` on disk.

**3. Run as a systemd service**

Create `/etc/systemd/system/galpha-ingest.service`:
```ini
[Unit]
Description=G-Alpha SEC Filing Ingestion Service
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/galpha
ExecStart=/usr/bin/python3.11 -m scripts.ingest_insider_trading --ticker AAPL
Restart=on-failure
RestartSec=60
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable galpha-ingest
sudo systemctl start galpha-ingest
journalctl -fu galpha-ingest   # tail structured logs
```

**4. Schedule periodic full-corpus refreshes with cron**
```bash
# Ingest all US30 constituents nightly at 02:00 UTC
crontab -e
0 2 * * * /opt/galpha/scripts/run_full_ingest.sh >> /var/log/galpha/ingest.log 2>&1
```

The idempotent design of both pipelines means re-running against already-ingested tickers is safe — duplicate records are detected via unique indexes and skipped without error.

---

## Project Structure

```
galpha/
├── galpha/
│   ├── config.py                      # Environment-based settings
│   ├── db.py                          # MongoDB connection management
│   ├── agents/
│   │   ├── tools.py                   # LangChain tool wrappers for retrieval layer
│   │   └── research_agent.py          # GPT-4 Turbo tool-calling research agent
│   ├── sec_filings/
│   │   ├── ingestion.py               # 10-K extraction and storage
│   │   └── retrieval.py               # Historical section queries
│   └── equity_intelligence/
│       ├── ingestion.py               # Form 4/5 ingestion pipeline
│       └── retrieval.py               # Insider transaction queries
├── scripts/
│   ├── ingest_10k.py                  # CLI: ingest a single 10-K filing
│   └── ingest_insider_trading.py      # CLI: ingest insider transactions
├── docs/
│   ├── architecture.md                # Data store and schema design decisions
│   ├── data-model.md                  # Field definitions, indexes, date conventions
│   └── agent-design.md                # Agent architecture and prompt design rationale
├── prompts/
│   ├── analyst_report.md              # Analyst report generation prompt template
│   └── qa_generation.md               # GPT-4 fine-tuning Q&A pair generation template
├── requirements.txt
├── .env.example
└── .gitignore
```
