from app.templates.data_ingestion import DATA_INGESTION_TEMPLATE
from app.templates.sre_report import SRE_REPORT_TEMPLATE
from app.templates.portfolio_reco import PORTFOLIO_RECO_TEMPLATE

TEMPLATES: list[dict] = [
    DATA_INGESTION_TEMPLATE,
    SRE_REPORT_TEMPLATE,
    PORTFOLIO_RECO_TEMPLATE,
]

TEMPLATES_BY_ID: dict[str, dict] = {t["id"]: t for t in TEMPLATES}
