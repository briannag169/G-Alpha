# Agent Design: G-Alpha Financial Research Agent

## Overview

The research agent is a LangChain tool-calling agent built on GPT-4 Turbo that answers natural language financial research queries by retrieving grounded data from the G-Alpha corpus. It is the AI-facing interface that makes the data engineering pipeline useful as an analyst tool.

---

## Why Tool-Calling over a Fixed Chain

The first design decision was whether to use a **LangChain tool-calling agent** (`create_openai_tools_agent`) or a **fixed chain** (e.g., `SequentialChain` or `LLMChain`).

**Fixed chain:** always executes in a predetermined order — fetch MD&A, fetch insider trades, stuff into prompt, generate response. Simple to reason about, but inflexible. A query like "Did Apple's executives buy or sell stock in 2023?" requires only the insider transactions tool — but a fixed chain would also fetch 10-K sections unnecessarily, consuming tokens and adding latency for no benefit.

**Tool-calling agent:** the LLM decides which tools to invoke based on the query, in what order, and with what parameters. For a query about risk factors only, it calls `get_10k_section` once. For a cross-signal query ("What risks did Tesla disclose and what did Musk do with his shares?"), it calls both tools sequentially. The agent is adaptive to the query type without code changes.

The tool-calling approach also scales naturally: adding a new data source (e.g., earnings call transcripts, 8-K filings) means adding a new Tool object — no chain restructuring required.

---

## Tool Design

### `get_10k_section`

**Input:** JSON string — avoids LangChain tool interface limitations with complex typed inputs. The agent generates valid JSON naturally when the description specifies the format clearly.

**Output:** Concatenated section text with `[TICKER — DATE]` headers, truncated at 4,000 characters. The truncation threshold was set empirically: MD&A sections for large-cap companies average 8,000–15,000 words, which would exhaust the context window if the agent calls multiple tools. 4,000 characters captures the most material disclosures (typically the first ~500 words of any section) while leaving room for the insider transactions output and the model's reasoning.

**Why not return the full text?** The downstream use case is analyst reasoning, not full-document retrieval. The agent is not a document viewer — it is a synthesis engine. Truncated inputs force the model to identify the most salient content rather than padding the response with raw text.

### `get_insider_transactions`

**Input:** JSON string with optional `person_name` filter. The SEC API returns filings for all insiders of a company; filtering by person is useful for questions about specific executives.

**Output:** One line per transaction: `{person} | {date} | BUY/SELL | ${amount}`. This format is compact (one transaction per line), parseable by the LLM, and maps directly to the analyst question pattern "who bought/sold, how much, and when."

---

## Model Choice: GPT-4 Turbo at Temperature 0

**GPT-4 Turbo** was chosen over GPT-3.5 for two reasons:
1. Financial analysis requires multi-step reasoning over long, dense text. GPT-4 Turbo's 128K context window and stronger reasoning capability are necessary for synthesising across multiple 10-K sections and transaction records simultaneously.
2. Tool-calling accuracy — GPT-4 Turbo generates correctly structured JSON tool calls reliably. GPT-3.5 occasionally malforms tool inputs when multiple optional parameters are involved.

**Temperature 0** enforces deterministic outputs. Financial analysis is not a creative task — the same query against the same corpus should produce the same response. Determinism also enables regression testing: if the corpus is unchanged and the query is unchanged, a changed response indicates a model or prompt regression.

---

## System Prompt Design

The system prompt has three components:

**1. Role definition:** *"You are G-Alpha's AI financial research analyst..."*
This primes the model to behave as a domain expert rather than a general assistant. It sets the expectation that answers will be grounded, structured, and framed in financial analysis terms.

**2. Tool usage mandate:** *"Always use at least one tool before answering. Never answer from training data alone."*
This is the most important instruction. GPT-4 has memorised information about public companies from its training data — AAPL's revenue, Elon Musk's trades, etc. Without this instruction, the model may answer correctly from memory, bypassing the retrieval layer entirely. For a production analyst tool, answers must be grounded in the actual corpus, not the model's (potentially stale) parametric memory.

**3. Output format:** *"Structure your response as a brief analyst report: key findings first, supporting evidence from the filings, and a one-sentence investment implication."*
This shapes the response into a format that mimics how a human analyst would structure a brief. Key findings first (executive summary), then evidence (from the retrieved text), then implication (the actionable takeaway). This format is directly comparable to how institutional research notes are structured.

---

## Multi-Turn Capability

The `ChatPromptTemplate` includes a `MessagesPlaceholder(variable_name="chat_history", optional=True)` slot. This enables the agent to handle follow-up questions within a session:

```
User: What were Apple's top risk factors in 2023?
Agent: [calls get_10k_section, returns answer]
User: Did any executives sell shares in that period?
Agent: [calls get_insider_transactions with AAPL + 2023 date range, correlates with previous answer]
```

The `optional=True` flag means the agent works for single-turn queries (no chat history provided) without any code changes.

---

## Extension Path: Vector Search

The current retrieval layer uses exact-match MongoDB queries (filter by ticker and date range). The natural next iteration is **semantic retrieval**: embed each section with a text embedding model, store vectors in MongoDB Atlas Vector Search, and retrieve by cosine similarity to the query.

This would allow queries like "find all 10-K sections that discuss supply chain concentration risk" across the entire corpus — not possible with the current exact-match approach. The section-per-collection schema is already aligned with this: each collection can have its own Atlas Vector Search index built from the section text field, and the retrieval tools can be upgraded to use `$vectorSearch` aggregation stages transparently from the agent's perspective.
