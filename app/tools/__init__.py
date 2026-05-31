from app.tools.csv_scanner import run as csv_scanner_run, scan_csv
from app.tools.data_quality import run as data_quality_run, check_data_quality
from app.tools.db_ingestor import run as db_ingestor_run, ingest_to_db
from app.tools.data_profiler import run as data_profiler_run, profile_data
from app.tools.job_stats_collector import run as job_stats_collector_run, collect_job_stats
from app.tools.report_publisher import run as report_publisher_run, publish_report

# Legacy pipeline-node tools (state dict → state dict).
# Used by type="tool" nodes in graph_definition.
PIPELINE_TOOLS: dict = {
    "csv_scanner":       csv_scanner_run,
    "data_quality":      data_quality_run,
    "db_ingestor":       db_ingestor_run,
    "data_profiler":     data_profiler_run,
    "job_stats_collector": job_stats_collector_run,
    "report_publisher":  report_publisher_run,
}

# LangChain @tool objects keyed by tool name.
# Used by real agent nodes (create_react_agent).
TOOL_REGISTRY: dict = {
    "scan_csv":            scan_csv,
    "check_data_quality":  check_data_quality,
    "ingest_to_db":        ingest_to_db,
    "profile_data":        profile_data,
    "collect_job_stats":   collect_job_stats,
    "publish_report":      publish_report,
}

# All @tool objects as a list (for convenience)
ALL_TOOLS: list = list(TOOL_REGISTRY.values())
