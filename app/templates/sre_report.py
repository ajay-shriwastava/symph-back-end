"""
SRE Job Summary — Workflow Template

Triggered by a message (e.g. "give me the job summary" or "how are jobs doing").
An SRE agent collects stats and posts a health summary to Slack.

Flow: Start → SREAgent → End
"""

_SYSTEM_PROMPT = (
    "You are an SRE engineer agent responsible for job health reporting. "
    "When asked for a job summary or health report, follow these steps:\n"
    "1. Call collect_job_stats with lookback_hours=24 to gather workflow run statistics.\n"
    "2. Write a Slack-friendly bullet-point health summary covering:\n"
    "   - Overall health: total runs and success rate\n"
    "   - Status breakdown: completed / failed / running / pending counts\n"
    "   - Per-workflow status with a pass/fail indicator\n"
    "   - Any workflows with failures, called out clearly as alerts\n"
    "   Keep it under 300 words. Use emoji sparingly (✅ healthy, ❌ failures, ⚠️ attention).\n"
    "3. Call publish_report with your summary, slack_channel='job-summary', and write_to_file=False.\n"
    "Always complete both steps."
)

SRE_REPORT_TEMPLATE: dict = {
    "id": "sre-job-summary",
    "name": "SRE Job Summary",
    "description": (
        "Triggered by a message. An SRE agent collects workflow run statistics "
        "for the last 24 hours and posts a job health summary to #job-summary."
    ),
    "schedule": None,
    "trigger_type": "message",
    # Agent config — used by instantiation to create the agent in the DB
    "agent_config": {
        "name": "SRE Report Agent",
        "description": "Collects job stats and posts SRE health summary to Slack",
        "model": "claude-haiku-4-5-20251001",
        "system_prompt": _SYSTEM_PROMPT,
        "tools": ["collect_job_stats", "publish_report"],
        "channels": [],
        "memory_enabled": False,
    },
    "graph_definition": {
        "nodes": [
            {
                "id": "start",
                "type": "start",
                "label": "Start",
                "x": 40,
                "y": 200,
            },
            {
                "id": "agent",
                "type": "agent",
                "label": "SRE Report Agent",
                "agent_id": None,  # filled in by instantiation
                "x": 220,
                "y": 178,
            },
            {
                "id": "end",
                "type": "end",
                "label": "End",
                "x": 420,
                "y": 200,
            },
        ],
        "edges": [
            {"id": "e1", "from": "start", "to": "agent"},
            {"id": "e2", "from": "agent", "to": "end"},
        ],
    },
}
