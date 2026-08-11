from app.tools.csv_scanner import run as csv_scanner_run, scan_csv
from app.tools.data_quality import run as data_quality_run, check_data_quality
from app.tools.db_ingestor import run as db_ingestor_run, ingest_to_db
from app.tools.data_profiler import run as data_profiler_run, profile_data
from app.tools.job_stats_collector import run as job_stats_collector_run, collect_job_stats
from app.tools.report_publisher import run as report_publisher_run, publish_report
from app.tools.market_signal_fetcher import run as market_signal_fetcher_run, fetch_rss_signal
from app.tools.portfolio_impact_analyzer import run as portfolio_impact_analyzer_run
from app.tools.product_universe_filter import run as product_universe_filter_run
from app.tools.rm_alert_publisher import run as rm_alert_publisher_run, publish_rm_alert
from app.tools.email_sender import send_email
from app.tools.whatsapp_sender import send_whatsapp
from app.tools.telegram_sender import send_telegram

# Pipeline-node tools (state dict → state dict).
# Used by type="tool" nodes in graph_definition.
PIPELINE_TOOLS: dict = {
    "csv_scanner":               csv_scanner_run,
    "data_quality":              data_quality_run,
    "db_ingestor":               db_ingestor_run,
    "data_profiler":             data_profiler_run,
    "job_stats_collector":       job_stats_collector_run,
    "report_publisher":          report_publisher_run,
    "portfolio_impact_analyzer": portfolio_impact_analyzer_run,
    "product_universe_filter":   product_universe_filter_run,
}

# LangChain @tool objects keyed by tool name.
# Used by real agent nodes (create_react_agent).
TOOL_REGISTRY: dict = {
    "scan_csv":           scan_csv,
    "check_data_quality": check_data_quality,
    "ingest_to_db":       ingest_to_db,
    "profile_data":       profile_data,
    "collect_job_stats":  collect_job_stats,
    "publish_report":     publish_report,
    "fetch_rss_signal":   fetch_rss_signal,
    "publish_rm_alert":   publish_rm_alert,
    "send_email":         send_email,
    "send_whatsapp":      send_whatsapp,
    "send_telegram":      send_telegram,
}

# Channel name → list of tool names auto-injected when that channel is active.
# Tools must exist in TOOL_REGISTRY.
CHANNEL_TOOLS: dict[str, list[str]] = {
    "slack":     ["publish_report"],
    "email":     ["send_email"],
    "whatsapp":  ["send_whatsapp"],
    "telegram":  ["send_telegram"],
}

# All @tool objects as a list (for convenience)
ALL_TOOLS: list = list(TOOL_REGISTRY.values())

# Configurable parameters per tool (exposed via GET /api/v1/tools/params).
# Each entry maps a tool name (pipeline or LLM) to its list of param descriptors.
TOOL_PARAMS: dict[str, list[dict]] = {
    "csv_scanner":             [{"name": "dataset_dir",    "label": "Dataset Directory",      "type": "string", "required": False}],
    "scan_csv":                [{"name": "dataset_dir",    "label": "Dataset Directory",      "type": "string", "required": False}],
    "data_quality":            [{"name": "dataset_dir",    "label": "Dataset Directory",      "type": "string", "required": False}],
    "check_data_quality":      [{"name": "dataset_dir",    "label": "Dataset Directory",      "type": "string", "required": False}],
    "db_ingestor":             [{"name": "dataset_dir",    "label": "Dataset Directory",      "type": "string", "required": False}],
    "ingest_to_db":            [{"name": "dataset_dir",    "label": "Dataset Directory",      "type": "string", "required": False}],
    "data_profiler":           [{"name": "dataset_dir",    "label": "Dataset Directory",      "type": "string", "required": False}],
    "profile_data":            [{"name": "dataset_dir",    "label": "Dataset Directory",      "type": "string", "required": False}],
    "report_publisher":        [{"name": "slack_channel",  "label": "Slack Channel",          "type": "string", "required": False},
                                {"name": "dataset_dir",    "label": "Dataset Directory",      "type": "string", "required": False}],
    "publish_report":          [{"name": "slack_channel",  "label": "Slack Channel",          "type": "string", "required": False},
                                {"name": "dataset_dir",    "label": "Dataset Directory",      "type": "string", "required": False}],
    "product_universe_filter": [{"name": "catalogue_path", "label": "Product Catalogue Path", "type": "string", "required": False}],
    "rm_alert_publisher":      [{"name": "slack_channel",  "label": "Slack Channel",          "type": "string", "required": False}],
    "publish_rm_alert":        [{"name": "slack_channel",  "label": "Slack Channel",          "type": "string", "required": False}],
}
