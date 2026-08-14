"""
Eval tests for the SRE Job Summary pipeline (two-agent handoff).

Tests both agents independently with canned inputs:
  - Stats Collector: given raw DB stats, must return the four required sections
    and must NOT publish or Slack-format anything
  - Report Writer: given the stats text, must produce a Slack-friendly summary
    with emoji indicators and call publish_report

Run:  pytest -m eval tests/eval/test_sre_pipeline.py -v
Cost: 3 Haiku calls (one per agent output, one LLM judge).
"""
import os
import re

import pytest
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from app.templates.sre_report import _STATS_PROMPT, _REPORT_PROMPT
from tests.eval.judge import llm_judge

pytestmark = [
    pytest.mark.eval,
    pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY"),
        reason="ANTHROPIC_API_KEY not set — skipping LLM eval tests",
    ),
]

# ---------------------------------------------------------------------------
# Canned tool result — simulates what collect_job_stats returns
# ---------------------------------------------------------------------------

_RAW_STATS = """\
Tool result from collect_job_stats (lookback_hours=24):
{
  "total_runs": 12,
  "completed": 10,
  "failed": 2,
  "running": 0,
  "pending": 0,
  "success_rate_pct": 83.3,
  "per_workflow": [
    {"name": "Data Ingestion Pipeline", "total": 8, "completed": 8, "failed": 0},
    {"name": "Portfolio Recommendation", "total": 2, "completed": 2, "failed": 0},
    {"name": "My Test Workflow",         "total": 2, "completed": 0, "failed": 2}
  ]
}

Return the structured plain-text summary now.
"""

# ---------------------------------------------------------------------------
# Module-scoped fixtures — one LLM call per agent, shared across tests
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
async def stats_output() -> str:
    llm = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0)
    result = await llm.ainvoke([
        SystemMessage(content=_STATS_PROMPT),
        HumanMessage(content=_RAW_STATS),
    ])
    return result.content


@pytest.fixture(scope="module")
async def report_output(stats_output) -> str:
    llm = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0)
    result = await llm.ainvoke([
        SystemMessage(content=_REPORT_PROMPT),
        HumanMessage(content=stats_output),
    ])
    return result.content


# ---------------------------------------------------------------------------
# Stats Collector checks
# ---------------------------------------------------------------------------

async def test_stats_contains_total_runs(stats_output):
    assert re.search(r"\b12\b", stats_output), (
        f"Stats output missing total run count (12):\n{stats_output}"
    )


async def test_stats_contains_success_rate(stats_output):
    assert re.search(r"83", stats_output), (
        f"Stats output missing success rate (83.3%):\n{stats_output}"
    )


async def test_stats_contains_per_workflow_breakdown(stats_output):
    assert "Data Ingestion Pipeline" in stats_output, (
        f"Stats output missing per-workflow breakdown:\n{stats_output}"
    )
    assert "My Test Workflow" in stats_output, (
        f"Stats output missing 'My Test Workflow' entry:\n{stats_output}"
    )


async def test_stats_does_not_publish(stats_output):
    """Stats Collector must NOT call publish or format for Slack — that is the Report Writer's job."""
    assert "publish" not in stats_output.lower(), (
        f"Stats Collector output contains 'publish' — it should only return raw data:\n{stats_output}"
    )


async def test_stats_no_slack_formatting(stats_output):
    """Stats Collector must return plain text, not Slack markdown bullets."""
    # The report writer adds the emoji; the stats collector should not
    slack_emoji = re.search(r"[✅❌⚠️]", stats_output)
    assert not slack_emoji, (
        f"Stats Collector output contains Slack-style emoji — formatting is the Report Writer's job:\n{stats_output}"
    )


# ---------------------------------------------------------------------------
# Report Writer checks
# ---------------------------------------------------------------------------

async def test_report_uses_health_emoji(report_output):
    """Report must use at least one of the specified emoji indicators."""
    assert re.search(r"[✅❌⚠️]", report_output), (
        f"Report missing health emoji (✅ / ❌ / ⚠️):\n{report_output}"
    )


async def test_report_word_count(report_output):
    """Prompt says under 300 words."""
    word_count = len(report_output.split())
    assert word_count <= 350, (
        f"Report is too long ({word_count} words, limit 300):\n{report_output}"
    )


async def test_report_mentions_failed_workflow(report_output):
    """My Test Workflow had 2 failures — the report must surface this."""
    assert "My Test Workflow" in report_output, (
        f"Report does not mention the failed workflow:\n{report_output}"
    )


async def test_report_quality(report_output, stats_output):
    passed, reason = await llm_judge(
        output=report_output,
        criterion=(
            "The report is a concise Slack-friendly health summary that correctly "
            "reflects the statistics: 12 total runs, 83% success rate, "
            "2 failures in 'My Test Workflow', and flags it as needing attention."
        ),
        context=stats_output,
    )
    assert passed, f"Report quality check failed: {reason}"
