from app.templates.data_ingestion import DATA_INGESTION_TEMPLATE
from app.templates.sre_report import SRE_REPORT_TEMPLATE

TEMPLATES: list[dict] = [
    DATA_INGESTION_TEMPLATE,
    SRE_REPORT_TEMPLATE,
]

TEMPLATES_BY_ID: dict[str, dict] = {t["id"]: t for t in TEMPLATES}
