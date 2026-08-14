"""
Eval tests for the RM Recommendation Writer prompt (Portfolio Reco template).

Key risks this guards against:
  - Format regression (per-investor note structure)
  - Hallucination (recommending funds not in the report)
  - Missing the warning format for flagged investors

Run:  pytest -m eval tests/eval/test_rm_writer.py -v
Cost: 2 Haiku calls (one for the agent, one for the LLM judge).
"""
import os
import re

import pytest
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from app.templates.portfolio_reco import _RM_RECOMMENDATION_PROMPT
from tests.eval.judge import llm_judge

pytestmark = [
    pytest.mark.eval,
    pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY"),
        reason="ANTHROPIC_API_KEY not set — skipping LLM eval tests",
    ),
]

# ---------------------------------------------------------------------------
# Canned portfolio impact report — two investors, one flagged
# Fund names deliberately specific so hallucination is detectable
# ---------------------------------------------------------------------------

_IMPACT_REPORT = """\
Market Alert Report
Event: RBI raises repo rate by 50bps to 7.0% to curb inflation
Sectors: Banking & Financial Services, Real Estate, Infrastructure
Sentiment: NEGATIVE

--- Investor Impact ---

Investor: Priya Sharma (INV001) | Aggressive, age 34, Wealth Builder
Exposed holdings:
  - ICICI Bluechip Fund (MF001): 45% sector exposure, Rs 2,25,000 at risk
Recommended alternatives (from product universe):
  - Mirae Large Cap Fund (MF002)
  - SBI Magnum Gilt Fund (MF025)

Investor: Raj Mehta (INV002) | Moderate, age 55, Pre-Retirement
Exposed holdings:
  - HDFC Banking & PSU Fund (MF010): 82% sector exposure, Rs 5,40,000 at risk
No suitable product in universe.
"""

# Only these two fund names should ever appear as recommendations
_PERMITTED_FUNDS = {"Mirae Large Cap Fund", "SBI Magnum Gilt Fund"}

# ---------------------------------------------------------------------------
# Module-scoped fixture — one LLM call shared across all tests
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
async def rm_writer_output() -> str:
    llm = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0)
    result = await llm.ainvoke([
        SystemMessage(content=_RM_RECOMMENDATION_PROMPT),
        HumanMessage(content=_IMPACT_REPORT),
    ])
    return result.content


# ---------------------------------------------------------------------------
# Format checks
# ---------------------------------------------------------------------------

async def test_investor_header_format(rm_writer_output):
    """Each investor block must start with *Name (ID)* | ..."""
    assert re.search(r"\*Priya Sharma \(INV001\)\*", rm_writer_output), (
        f"Missing formatted header for Priya Sharma:\n{rm_writer_output}"
    )


async def test_consider_line_present_for_normal_investor(rm_writer_output):
    """Non-flagged investor must have a '-> Consider:' recommendation line."""
    assert re.search(r"→\s*Consider:", rm_writer_output), (
        f"Missing '-> Consider:' line for Priya Sharma:\n{rm_writer_output}"
    )


async def test_warning_format_for_flagged_investor(rm_writer_output):
    """Flagged investor (Raj Mehta) must use the warning format with the flag emoji."""
    assert re.search(r"⚠️.*Raj Mehta", rm_writer_output), (
        f"Missing warning format for flagged investor Raj Mehta:\n{rm_writer_output}"
    )


async def test_warning_includes_no_suitable_product(rm_writer_output):
    assert "No suitable product in universe" in rm_writer_output, (
        f"Missing 'No suitable product in universe' for flagged investor:\n{rm_writer_output}"
    )


async def test_note_word_count_reasonable(rm_writer_output):
    """
    Rough word-count check per investor block — prompt says under 80 words each.
    We allow up to 120 as a lenient upper bound to avoid flakiness.
    """
    # Extract the Priya block (up to the next investor or end)
    match = re.search(
        r"\*Priya Sharma.*?(?=\*Raj Mehta|\Z)", rm_writer_output, re.DOTALL
    )
    if match:
        word_count = len(match.group(0).split())
        assert word_count <= 120, (
            f"Priya Sharma note is too long ({word_count} words, limit ~80):\n{match.group(0)}"
        )


# ---------------------------------------------------------------------------
# Quality checks — LLM judge
# ---------------------------------------------------------------------------

async def test_no_hallucinated_fund_recommendations(rm_writer_output):
    passed, reason = await llm_judge(
        output=rm_writer_output,
        criterion=(
            "The output recommends ONLY fund names explicitly listed in the report "
            "alternatives section: 'Mirae Large Cap Fund' and 'SBI Magnum Gilt Fund'. "
            "It does not recommend any other fund not present in the report."
        ),
        context=_IMPACT_REPORT,
    )
    assert passed, f"Hallucination check failed: {reason}"


async def test_event_connected_to_holdings(rm_writer_output):
    passed, reason = await llm_judge(
        output=rm_writer_output,
        criterion=(
            "The note for Priya Sharma explicitly connects the RBI rate hike event "
            "to her specific holding (ICICI Bluechip Fund) and explains why it is at risk."
        ),
        context=_IMPACT_REPORT,
    )
    assert passed, f"Event-to-holdings connection check failed: {reason}"
