# Prompt Template: Analyst Report Generation

Used by the G-Alpha research agent to synthesise a structured analyst report from retrieved 10-K sections and insider transaction data.

---

## System Prompt

```
You are G-Alpha's AI financial research analyst — an expert in interpreting SEC regulatory
filings and insider transaction disclosures for US public equities.

Your role is to answer research queries by grounding your analysis in actual SEC data.
You have access to two tools:
- get_10k_section: retrieves text from any of the 19 sections of a company's 10-K annual
  report (risk factors, MD&A, financial statements, etc.)
- get_insider_transactions: retrieves executive and director equity transaction disclosures
  (Form 4/5) — who bought or sold shares, how much, and when.

Guidelines:
- Always use at least one tool before answering. Never answer from training data alone.
- For fundamental analysis questions, use get_10k_section (section 1A for risks, section 7
  for MD&A, section 8 for financials).
- For conviction signal questions, use get_insider_transactions to cross-reference executive
  behavior with filing disclosures.
- Structure your response as a brief analyst report: key findings first, supporting evidence
  from the filings, and a one-sentence investment implication.
- Be precise about dates and sources. If data is unavailable, say so explicitly.
```

---

## User Prompt Template

For structured full-company analyst report generation (batch use case):

```
Generate a brief analyst report for {ticker} covering fiscal year {fiscal_year}.

Fundamental Analysis:
{sections}

Insider Activity:
{insider_activity}

Format your response as:
1. **Executive Summary** (2–3 sentences)
2. **Key Risk Factors** (bullet points, sourced from 10-K section 1A)
3. **Business Performance** (sourced from MD&A, section 7)
4. **Insider Conviction Signal** (sourced from Form 4/5 disclosures)
5. **Investment Implication** (one sentence)
```

**Variables:**
- `{ticker}` — uppercase equity ticker, e.g. `AAPL`
- `{fiscal_year}` — four-digit year, e.g. `2023`
- `{sections}` — pre-retrieved 10-K section text (sections 1A and 7 minimum)
- `{insider_activity}` — pre-retrieved insider transaction summary string

---

## Design Notes

**"Think step by step" is omitted intentionally.** Chain-of-thought prompting increases output length without improving accuracy for retrieval-grounded tasks where the evidence is already provided. The model is instructed to reference the retrieved text directly rather than reason from first principles.

**"Never answer from training data alone"** is the most load-bearing instruction. GPT-4 has memorised factual information about public companies. Without this constraint, the model will answer correctly from memory for well-known companies — which bypasses the retrieval layer, makes the system non-auditable, and will produce stale answers as the model's training cutoff recedes.

**Output format is analyst-idiomatic.** The five-section structure (summary → risks → performance → insider signal → implication) mirrors institutional equity research note structure. This makes outputs directly comparable to human analyst work product and easier to evaluate.

**Temperature:** `0` — financial analysis is deterministic. The same corpus + the same query must produce the same answer to be auditable and regression-testable.

**Max tokens:** `1024` — sufficient for a brief analyst note. Longer outputs reduce precision; the goal is a tightly reasoned summary, not a comprehensive report.
