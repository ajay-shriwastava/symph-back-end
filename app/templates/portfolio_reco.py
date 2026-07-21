"""
Portfolio Recommendation — Workflow Template

Four-node pipeline triggered manually from the UI:

  1. [Agent]         Market Signal Watcher      — fetch RSS headlines → LLM reasons about
                                                  direct + second-order sector impacts
  2. [Pipeline Tool] Portfolio Impact Analyzer  — deterministic: load CSVs, score weighted
                                                  exposure, draft top-3 alternatives
  3. [Pipeline Tool] Product Universe Filter    — hard constraint enforcement: strip any
                                                  fund not in product_catalogue.csv, flag
                                                  investors with zero valid alternatives (⚠️)
  4. [Agent]         RM Recommendation Writer   — LLM writes ≤60-word per-investor notes,
                                                  posts consolidated Slack message to
                                                  #portfolio-reco via publish_rm_alert

Flow: Start → market-signal-agent → portfolio-impact-analyzer
           → product-universe-filter → rm-recommendation-agent → End

Telemetry : LangSmith (LANGCHAIN_TRACING_V2=true, LANGCHAIN_PROJECT=portfolio)
Slack     : #portfolio-reco (SLACK_REPORT_CHANNEL env var)
Data      : pre-ingested CSVs at DATASET_DIR
"""

_MARKET_SIGNAL_PROMPT = """\
You are the Market Signal Watcher for a wealth management firm.

When invoked, call fetch_rss_signal to retrieve the latest Indian market news headlines.

Analyse the headlines and identify the single most significant market event occurring right now.
Then reason about which mutual fund sectors are directly affected and which are indirectly
affected via second-order exposure (e.g. an oil price spike directly hits Energy funds;
indirectly it raises input costs for Industrials, FMCG, and Infrastructure).

End your response with EXACTLY this structured block (do not add any text after it):

EVENT_SUMMARY: <1-2 sentences describing the key market event>
ALL_AFFECTED_SECTORS: <comma-separated sector names, e.g. Financial Services, IT, Energy>
SENTIMENT: <POSITIVE or NEGATIVE>

Rules:
- Use sector names that match these known categories: Financial Services, IT, Energy,
  Healthcare, Infrastructure, Industrials, FMCG, Mid Cap, Large Cap, Metals, Materials,
  Consumer Discretionary, Banking & Financial Services, Real Estate, Transportation.
- If no significant event is found, set SENTIMENT: NEUTRAL and ALL_AFFECTED_SECTORS: NONE.
- Never invent events not present in the headlines.
"""

_RM_RECOMMENDATION_PROMPT = """\
You are the RM Recommendation Writer for a wealth management firm.

You will receive a validated portfolio impact report. It contains per-investor blocks showing:
- Which holdings are exposed to the market event
- Recommended alternative funds from the product universe (with fund_id and name)
- ⚠️ flags for investors where no suitable product exists in the universe

Your job:
1. For each investor block in the report, write a concise RM action note:
   - Investor name, risk profile, life stage
   - What is at risk (affected holdings and approximate ₹ exposure)
   - Recommended action using ONLY the alternatives listed in the report
     (use exact fund names as they appear — never add funds from your own knowledge)
   - One sentence rationale
   Keep each note under 60 words.

2. For investors with a ⚠️ flag, write:
   "⚠️ [Name] — [exposure summary]. No suitable product in universe. RM review required."

3. After writing all notes, call publish_rm_alert with:
   - recommendations: the formatted notes (all investors consolidated)
   - slack_channel: "portfolio-reco"
   - event_title: "Market Alert — Portfolio Action Required"

CRITICAL: Only use fund names explicitly listed in the report. Never recommend any fund
from your training knowledge. Never skip step 3.
"""

PORTFOLIO_RECO_TEMPLATE: dict = {
    "id":           "portfolio-recommendation",
    "name":         "Portfolio Recommendation",
    "description":  (
        "Market signal → portfolio impact → RM recommendation pipeline. "
        "Fetches real Indian market news, identifies materially impacted investors, "
        "enforces product universe constraints, and posts RM-ready Slack alerts to #portfolio-reco."
    ),
    "schedule":     None,
    "trigger_type": "message",

    "agent_configs": [
        {
            "node_id":       "market-signal-agent",
            "name":          "Market Signal Watcher",
            "description":   "Fetches RSS headlines and reasons about direct + second-order sector impacts",
            "model":         "claude-haiku-4-5-20251001",
            "system_prompt": _MARKET_SIGNAL_PROMPT,
            "tools":         ["fetch_rss_signal"],
            "channels":      [],
            "memory_enabled": False,
        },
        {
            "node_id":       "rm-recommendation-agent",
            "name":          "RM Recommendation Writer",
            "description":   "Writes RM-ready notes from validated impact data and posts to Slack",
            "model":         "claude-haiku-4-5-20251001",
            "system_prompt": _RM_RECOMMENDATION_PROMPT,
            "tools":         ["publish_rm_alert"],
            "channels":      [],
            "memory_enabled": False,
        },
    ],

    "graph_definition": {
        "nodes": [
            {
                "id":    "start",
                "type":  "start",
                "label": "Start",
                "x":     40,
                "y":     200,
            },
            {
                "id":       "market-signal-agent",
                "type":     "agent",
                "label":    "Market Signal Watcher",
                "agent_id": None,   # filled by instantiation
                "x":        210,
                "y":        178,
            },
            {
                "id":        "portfolio-impact-analyzer",
                "type":      "tool",
                "label":     "Portfolio Impact Analyzer",
                "tool_name": "portfolio_impact_analyzer",
                "x":         430,
                "y":         178,
            },
            {
                "id":        "product-universe-filter",
                "type":      "tool",
                "label":     "Product Universe Filter",
                "tool_name": "product_universe_filter",
                "x":         640,
                "y":         178,
            },
            {
                "id":       "rm-recommendation-agent",
                "type":     "agent",
                "label":    "RM Recommendation Writer",
                "agent_id": None,   # filled by instantiation
                "x":        855,
                "y":        178,
            },
            {
                "id":    "end",
                "type":  "end",
                "label": "End",
                "x":     1060,
                "y":     200,
            },
        ],
        "edges": [
            {"id": "e1", "from": "start",                      "to": "market-signal-agent"},
            {"id": "e2", "from": "market-signal-agent",        "to": "portfolio-impact-analyzer"},
            {"id": "e3", "from": "portfolio-impact-analyzer",  "to": "product-universe-filter"},
            {"id": "e4", "from": "product-universe-filter",    "to": "rm-recommendation-agent"},
            {"id": "e5", "from": "rm-recommendation-agent",    "to": "end"},
        ],
    },
}
