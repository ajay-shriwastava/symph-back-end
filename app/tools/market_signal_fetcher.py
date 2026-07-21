"""
market_signal_fetcher — LangChain @tool (TOOL_REGISTRY)

Fetches real financial news headlines from Indian market RSS feeds.
Used by the Market Signal Watcher agent node — the LLM reasons about
which sectors are affected (direct + second-order) from the raw headlines.

Sources (free, no API key):
  - Economic Times Markets
  - Moneycontrol Market Reports
"""

import logging

import feedparser
import httpx
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

_RSS_FEEDS = [
    ("Economic Times Markets",  "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"),
    ("Moneycontrol Markets",    "https://www.moneycontrol.com/rss/marketreports.xml"),
]


async def _fetch_feed(url: str, client: httpx.AsyncClient, n: int) -> list[dict]:
    try:
        resp = await client.get(url, timeout=10.0, follow_redirects=True)
        parsed = feedparser.parse(resp.text)
        return [
            {
                "title":     e.get("title", "").strip(),
                "summary":   e.get("summary", "")[:250].strip(),
                "published": e.get("published", ""),
            }
            for e in parsed.entries[:n]
        ]
    except Exception as exc:
        logger.warning("RSS fetch failed for %s: %s", url, exc)
        return []


@tool
async def fetch_rss_signal(max_headlines: int = 15) -> str:
    """Fetch the latest financial market news headlines from Indian market RSS feeds.
    Pulls from Economic Times Markets and Moneycontrol Markets.
    Returns raw headlines with titles, summaries, and timestamps.
    max_headlines: total headlines to return across all sources (default 15).
    Use the returned headlines to identify significant market events and reason about
    which sectors and instruments are directly and indirectly affected."""
    per_feed = max(1, max_headlines // len(_RSS_FEEDS))
    all_entries: list[dict] = []

    async with httpx.AsyncClient() as client:
        for source_name, url in _RSS_FEEDS:
            entries = await _fetch_feed(url, client, per_feed)
            for e in entries:
                e["source"] = source_name
            all_entries.extend(entries)

    if not all_entries:
        return "No headlines fetched — RSS feeds may be unreachable. Proceed with available market context."

    lines = [f"Market News Headlines ({len(all_entries)} articles)", "=" * 60, ""]
    for i, e in enumerate(all_entries, 1):
        lines += [
            f"[{i}] {e['source']}  |  {e['published']}",
            f"    TITLE  : {e['title']}",
            f"    SUMMARY: {e['summary']}",
            "",
        ]

    logger.info("Fetched %d market headlines from %d RSS feeds", len(all_entries), len(_RSS_FEEDS))
    return "\n".join(lines)


async def run(state: dict) -> dict:
    result = await fetch_rss_signal.ainvoke({"max_headlines": 15})
    return {
        **state,
        "messages":      list(state.get("messages", [])) + [result],
        "market_signal": result,
    }
