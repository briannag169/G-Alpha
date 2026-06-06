"""
G-Alpha AI Financial Research Agent.

A LangChain tool-calling agent that acts as an autonomous financial analyst,
drawing on the SEC Filings corpus and Equity Intelligence corpus to answer
natural language research queries about US equities.

The agent uses GPT-4 Turbo with tool-calling to decide which data to fetch,
retrieve it from MongoDB via the corpus retrieval APIs, and synthesize a
structured analyst response grounded in actual regulatory filings.
"""
from __future__ import annotations

import logging

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from galpha.agents.tools import TOOLS
from galpha.config import settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are G-Alpha's AI financial research analyst — an expert in interpreting \
SEC regulatory filings and insider transaction disclosures for US public equities.

Your role is to answer research queries by grounding your analysis in actual SEC data. \
You have access to two tools:
- **get_10k_section**: retrieves text from any of the 19 sections of a company's 10-K annual \
report (risk factors, MD&A, financial statements, etc.)
- **get_insider_transactions**: retrieves executive and director equity transaction disclosures \
(Form 4/5) — who bought or sold shares, how much, and when.

Guidelines:
- Always use at least one tool before answering. Never answer from training data alone.
- For fundamental analysis questions, use get_10k_section (section 1A for risks, section 7 \
for MD&A, section 8 for financials).
- For conviction signal questions, use get_insider_transactions to cross-reference executive \
behavior with filing disclosures.
- Structure your response as a brief analyst report: key findings first, supporting evidence \
from the filings, and a one-sentence investment implication.
- Be precise about dates and sources. If data is unavailable, say so explicitly."""


def build_research_agent() -> AgentExecutor:
    """Construct the G-Alpha research agent with both corpus tools.

    Returns:
        A LangChain AgentExecutor ready to handle financial research queries.
    """
    llm = ChatOpenAI(
        model="gpt-4-turbo",
        temperature=0,
        api_key=settings.openai_api_key,
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_openai_tools_agent(llm=llm, tools=TOOLS, prompt=prompt)

    return AgentExecutor(
        agent=agent,
        tools=TOOLS,
        verbose=True,
        max_iterations=6,
        handle_parsing_errors=True,
    )


def run_research_query(query: str) -> str:
    """Run a natural language financial research query against the G-Alpha corpus.

    Args:
        query: Natural language research question, e.g.
            "What were Apple's top 3 risk factors in 2023 and did any
             executives sell shares around the filing date?"

    Returns:
        Agent-synthesized analyst response grounded in SEC filing data.
    """
    logger.info("Running research query: %s", query[:120])
    agent = build_research_agent()
    result = agent.invoke({"input": query})
    return result["output"]
