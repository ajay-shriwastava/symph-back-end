"""
Eval tests for the Data Ingestion Agent prompt.

The agent is a ReAct tool-caller, so we test the one step that produces
free-text output: the executive summary (step 6 of the prompt). We simulate
completed tool results in the user message so no real tools are needed.

Run:  pytest -m eval tests/eval/test_data_ingestion.py -v
Cost: 2 Haiku calls (one for the agent, one for the LLM judge).
"""
import os
import re

import pytest
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from app.templates.data_ingestion import _SYSTEM_PROMPT
from tests.eval.judge import llm_judge

pytestmark = [
    pytest.mark.eval,
    pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY"),
        reason="ANTHROPIC_API_KEY not set — skipping LLM eval tests",
    ),
]

# ---------------------------------------------------------------------------
# Canned pipeline result — simulates the outcome of steps 1-5
# ---------------------------------------------------------------------------

_PIPELINE_RESULT = """\
The data ingestion pipeline tools have completed with the following results:

scan_csv result:
  file_path: /data/input/sales_q3_2024.csv
  table_name: sales_data

check_data_quality result:
  clean_csv_path: /data/output/sales_q3_2024_clean.csv
  rows_original: 1870
  rows_clean: 1847
  rows_rejected: 23
  rejection_reasons: 14 blank rows, 9 duplicate entries
  warnings: 2 columns have >5% null values (discount_pct, return_date)

ingest_to_db result:
  rows_ingested: 1847
  rows_rejected: 23
  table: sales_data

profile_data result:
  row_count: 1847
  avg_sale_value: 4230.50
  top_region: Maharashtra (38% of sales)
  peak_month: September
  null_rate_discount_pct: 7.2%
  null_rate_return_date: 5.8%

Now write the executive summary for step 6.
"""

# ---------------------------------------------------------------------------
# Module-scoped fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
async def ingestion_summary() -> str:
    llm = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0)
    result = await llm.ainvoke([
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=_PIPELINE_RESULT),
    ])
    return result.content


# ---------------------------------------------------------------------------
# Format and content checks
# ---------------------------------------------------------------------------

async def test_summary_mentions_filename(ingestion_summary):
    assert "sales_q3_2024" in ingestion_summary, (
        f"Summary does not mention the processed filename:\n{ingestion_summary}"
    )


async def test_summary_mentions_rows_ingested(ingestion_summary):
    assert re.search(r"1[,.]?847", ingestion_summary), (
        f"Summary does not include rows ingested count (1847):\n{ingestion_summary}"
    )


async def test_summary_mentions_rows_rejected(ingestion_summary):
    assert re.search(r"\b23\b", ingestion_summary), (
        f"Summary does not include rows rejected count (23):\n{ingestion_summary}"
    )


async def test_summary_word_count(ingestion_summary):
    """Prompt says under 200 words."""
    word_count = len(ingestion_summary.split())
    assert word_count <= 250, (
        f"Summary is too long ({word_count} words, limit 200):\n{ingestion_summary}"
    )


async def test_summary_mentions_data_quality_warning(ingestion_summary):
    assert re.search(r"null|missing|warning", ingestion_summary, re.IGNORECASE), (
        f"Summary does not mention the data quality warnings:\n{ingestion_summary}"
    )


# ---------------------------------------------------------------------------
# Quality check — LLM judge
# ---------------------------------------------------------------------------

async def test_summary_is_executive_quality(ingestion_summary):
    passed, reason = await llm_judge(
        output=ingestion_summary,
        criterion=(
            "The summary reads as an executive-level report: it covers what file was processed, "
            "ingestion stats with specific numbers (1847 ingested, 23 rejected), "
            "data quality warnings, and at least one key insight from the data profile. "
            "It is concise and specific — not vague or generic."
        ),
        context=_PIPELINE_RESULT,
    )
    assert passed, f"Executive quality check failed: {reason}"
