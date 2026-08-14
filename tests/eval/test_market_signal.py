"""
Eval tests for the Market Signal Watcher prompt (Portfolio Reco template).

These tests verify that the prompt + model combination reliably produces
output in the required structured format, using canned headlines so no
real RSS feed is hit.

Run:  pytest -m eval tests/eval/test_market_signal.py -v
Cost: 2 Haiku calls (one for the agent, one for the LLM judge).
"""
import os
import re

import pytest
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from app.templates.portfolio_reco import _MARKET_SIGNAL_PROMPT
from tests.eval.judge import llm_judge

pytestmark = [
    pytest.mark.eval,
    pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY"),
        reason="ANTHROPIC_API_KEY not set — skipping LLM eval tests",
    ),
]

# ---------------------------------------------------------------------------
# Canned input — avoids hitting a real RSS feed during tests
# ---------------------------------------------------------------------------

_HEADLINES = """\
Latest Indian market headlines:
- RBI raises repo rate by 50bps in surprise move to curb inflation
- Banking stocks fall sharply; Nifty Bank index drops 3.2% intraday
- PSU banks worst hit as rate hike fears grip Dalal Street
- Real estate developers warn of demand slowdown as home loan rates rise
- IT majors Infosys and TCS see marginal gains on rupee weakening
- Infrastructure projects face higher borrowing costs after rate decision
"""

_KNOWN_SECTORS = {
    "Financial Services", "IT", "Energy", "Healthcare", "Infrastructure",
    "Industrials", "FMCG", "Mid Cap", "Large Cap", "Metals", "Materials",
    "Consumer Discretionary", "Banking & Financial Services", "Real Estate",
    "Transportation", "NONE",
}

# ---------------------------------------------------------------------------
# Module-scoped fixture — one LLM call shared across all tests in this file
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
async def market_signal_output() -> str:
    llm = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0)
    result = await llm.ainvoke([
        SystemMessage(content=_MARKET_SIGNAL_PROMPT),
        HumanMessage(content=_HEADLINES),
    ])
    return result.content


# ---------------------------------------------------------------------------
# Format checks — regex, deterministic, no extra LLM call
# ---------------------------------------------------------------------------

async def test_event_summary_present(market_signal_output):
    assert re.search(r"^EVENT_SUMMARY:\s*.+", market_signal_output, re.MULTILINE), (
        f"Missing EVENT_SUMMARY:\n{market_signal_output}"
    )


async def test_all_affected_sectors_present(market_signal_output):
    assert re.search(r"^ALL_AFFECTED_SECTORS:\s*.+", market_signal_output, re.MULTILINE), (
        f"Missing ALL_AFFECTED_SECTORS:\n{market_signal_output}"
    )


async def test_sentiment_present_and_valid(market_signal_output):
    assert re.search(
        r"^SENTIMENT:\s*(POSITIVE|NEGATIVE|NEUTRAL)", market_signal_output, re.MULTILINE
    ), f"Missing or invalid SENTIMENT:\n{market_signal_output}"


async def test_structured_block_ends_output(market_signal_output):
    """Prompt says 'do not add any text after' the structured block."""
    tail = "\n".join(market_signal_output.strip().splitlines()[-6:])
    assert re.search(r"SENTIMENT:\s*(POSITIVE|NEGATIVE|NEUTRAL)", tail), (
        f"SENTIMENT block is not at the end — text appears after it:\n{market_signal_output}"
    )


async def test_sectors_from_known_list(market_signal_output):
    match = re.search(r"^ALL_AFFECTED_SECTORS:\s*(.+)", market_signal_output, re.MULTILINE)
    assert match, "Cannot parse ALL_AFFECTED_SECTORS"
    raw = match.group(1).strip()
    if raw.upper() == "NONE":
        return
    sectors = [s.strip() for s in raw.split(",")]
    unknown = [s for s in sectors if s not in _KNOWN_SECTORS]
    assert not unknown, (
        f"Sector names not in the known list: {unknown}\n"
        f"Full output:\n{market_signal_output}"
    )


# ---------------------------------------------------------------------------
# Quality checks — LLM judge
# ---------------------------------------------------------------------------

async def test_event_grounded_in_headlines(market_signal_output):
    passed, reason = await llm_judge(
        output=market_signal_output,
        criterion=(
            "The EVENT_SUMMARY field describes a specific event clearly present in the "
            "provided headlines. Ignore ALL_AFFECTED_SECTORS — second-order sector "
            "reasoning is intentional and correct. Judge only whether the event in "
            "EVENT_SUMMARY matches something actually stated in the headlines."
        ),
        context=_HEADLINES,
    )
    assert passed, f"Groundedness check failed: {reason}"


async def test_second_order_sectors_included(market_signal_output):
    passed, reason = await llm_judge(
        output=market_signal_output,
        criterion=(
            "ALL_AFFECTED_SECTORS includes at least one sector that is indirectly "
            "(second-order) impacted by the event, not just the most obviously direct sector."
        ),
        context=_HEADLINES,
    )
    assert passed, f"Second-order reasoning check failed: {reason}"
