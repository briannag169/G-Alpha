# Architecture Decision Record: G-Alpha SEC Filing Intelligence Pipeline

## Overview

The G-Alpha pipeline is split into two concerns: **ingestion** (pulling from SEC EDGAR and storing) and **retrieval** (serving data to the AI layer). An **agent layer** sits on top of retrieval, providing a natural language interface to the corpus. This document records the key architectural decisions and their rationale.

---

## Data Store: MongoDB Atlas over a Relational Database

**Decision:** Use MongoDB as the primary data store for both the 10-K corpus and the equity intelligence corpus.

**Rationale:**

SEC 10-K filings are unstructured narrative text. Section lengths vary by orders of magnitude — a company's Risk Factors section can be 2,000 words or 20,000 words. A relational schema would require either a wide `TEXT` column (poor query performance, no per-section indexing) or a normalised rows-of-sections approach (complex joins for retrieval, no benefit from relational integrity since there are no foreign key relationships between sections).

MongoDB's document model maps naturally to the filing structure: each document is a self-contained unit with a `ticker`, `date`, `ticker_date` key, and a single section text field. Collections are independent and can be indexed, scaled, and queried in isolation.

A secondary consideration is the future upgrade path to **MongoDB Atlas Vector Search**: when the pipeline is extended to support semantic retrieval (embedding sections and querying by cosine similarity), Atlas Vector Search operates at the collection level. The section-per-collection schema means vector indexes can be built and maintained independently per section type — a Risk Factors vector index is kept separate from a Financial Statements vector index, which is the correct granularity for the downstream AI analyst use case.

---

## Schema Design: Section-per-Collection

**Decision:** Store each of the 19 Regulation S-K sections in its own MongoDB collection, rather than embedding all sections in a single document per filing.

**Rationale:**

The primary retrieval pattern is: *"give me the Risk Factor disclosures for MSFT from 2015 to 2023."* This query touches only one section type across many tickers and dates. With a single-document-per-filing schema, MongoDB would need to load and project out 18 irrelevant sections on every query. With section-per-collection, the query hits a small, focused collection.

Secondary benefits:
- **Index isolation**: the `ticker_date` unique index is per-collection, keeping index size proportional to the number of filings for that section, not the total corpus.
- **Operational isolation**: a collection for a high-traffic section (e.g., `7 - MD&A`) can be moved to a dedicated shard or replica set node without restructuring the schema.
- **Partial failure tolerance**: if extraction of section 6 fails for a filing (section 6 was eliminated for most filers after February 2021), the other 18 sections are still persisted correctly. The ingestion loop catches per-section exceptions independently.

---

## Idempotency: Insert + DuplicateKeyError over Upsert

**Decision:** Use `insert_one` and catch `DuplicateKeyError` rather than `update_one` with `upsert=True`.

**Rationale:**

Both approaches prevent duplicate records. The choice comes down to what the operation means semantically.

An `upsert` says: *"the latest version of this document is authoritative; overwrite what was there."* For SEC filings, the original document text is immutable — a company cannot retroactively change its 2021 10-K Risk Factors after filing. Silently overwriting an existing document with an identical one is wasteful; silently overwriting it with a different one (e.g., if the SEC API returns different text for the same filing URL) would be data corruption without an audit trail.

Insert + catch says: *"this record already exists; skip it and log a warning."* The warning is surfaced at `WARNING` log level, making duplicate re-ingestion runs visible in the pipeline logs without failing the job. If a document genuinely needs to be updated (e.g., an SEC filing amendment), the operator can delete the record explicitly and re-run — a deliberate action with an audit trail.

---

## Agent Design: Tool-Calling over a Fixed Chain

**Decision:** Use a LangChain tool-calling agent (`create_openai_tools_agent`) rather than a fixed `LLMChain` or `SequentialChain`.

**Rationale:** See [agent-design.md](agent-design.md).

---

## Pipeline Continuity: Stateless Scripts + Idempotent Storage

**Decision:** Scripts are stateless and re-runnable; all state lives in MongoDB.

No pipeline state file, no checkpoint database, no job queue. Each script invocation queries the SEC API from offset 0 and relies on the unique index to skip already-ingested records. This trades slightly higher API call volume for dramatically simpler operations: there is no state to corrupt, no checkpoint to recover from, and no coordination needed between parallel runs of different tickers.

On EC2, this means the ingestion service can be restarted freely after a crash without any recovery logic. The `Restart=on-failure` systemd directive handles transient failures transparently.
