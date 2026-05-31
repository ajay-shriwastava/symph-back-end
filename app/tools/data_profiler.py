"""
data_profiler — Tool node + LangChain @tool

Builds a statistical profile of a dataset and uses Claude to generate
a domain-aware narrative summary.
"""

import logging
import statistics
from collections import Counter, defaultdict

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

_REAL_ESTATE = {"price", "bedrooms", "bhk", "bedroom", "sqft", "sqfeet", "area",
                "bath", "bathrooms", "location", "city", "no_of_bedrooms", "beds"}
_HR          = {"salary", "department", "employee", "age", "designation", "experience"}
_ECOMMERCE   = {"price", "quantity", "product", "category", "revenue", "orders", "sku"}


def _detect_domain(columns: list[str]) -> str:
    lower = {c.lower() for c in columns}
    if len(lower & _REAL_ESTATE) >= 2:
        return "real_estate"
    if lower & _HR:
        return "hr"
    if lower & _ECOMMERCE:
        return "ecommerce"
    return "generic"


def _find_col(columns: list[str], candidates: set[str]) -> str | None:
    for col in columns:
        if col.lower() in candidates:
            return col
    return None


def _build_profile(records: list[dict], columns: list[str], domain: str) -> dict:
    profile: dict = {"domain": domain, "total_rows": len(records), "columns": {}}

    for col in columns:
        vals = [r[col] for r in records if r.get(col) is not None]
        try:
            nums = [float(v) for v in vals]
            profile["columns"][col] = {
                "type": "numeric",
                "count": len(nums),
                "min":    round(min(nums), 4),
                "max":    round(max(nums), 4),
                "mean":   round(statistics.mean(nums), 4),
                "median": round(statistics.median(nums), 4),
            }
        except (ValueError, TypeError):
            counts = Counter(str(v) for v in vals)
            profile["columns"][col] = {
                "type":     "categorical",
                "distinct": len(counts),
                "top_values": [{"value": v, "count": c} for v, c in counts.most_common(5)],
            }

    # Real estate: group by bedroom count
    if domain == "real_estate":
        bed_col   = _find_col(columns, {"bedrooms", "bhk", "bedroom", "no_of_bedrooms", "beds"})
        price_col = _find_col(columns, {"price", "amount", "price_per_sqft"})

        if bed_col and price_col:
            groups: dict[str, list[float]] = defaultdict(list)
            for r in records:
                bed = r.get(bed_col)
                prc = r.get(price_col)
                if bed is not None and prc is not None:
                    try:
                        groups[str(bed)].append(float(prc))
                    except (ValueError, TypeError):
                        pass

            bedroom_summary = {}
            for bed_val, prices in sorted(groups.items()):
                bedroom_summary[bed_val] = {
                    "count":     len(prices),
                    "min_price": round(min(prices), 2),
                    "max_price": round(max(prices), 2),
                    "avg_price": round(sum(prices) / len(prices), 2),
                }
            profile["bedroom_summary"] = bedroom_summary

    return profile


def _profile_text(profile: dict, table_name: str) -> str:
    lines = [
        f"Dataset: {table_name}",
        f"Domain: {profile['domain']}",
        f"Total rows: {profile['total_rows']}",
    ]

    for col, stats in profile["columns"].items():
        if stats["type"] == "numeric":
            lines.append(
                f"  {col}: min={stats['min']}, max={stats['max']}, "
                f"mean={stats['mean']}, median={stats['median']}"
            )
        else:
            top = ", ".join(f"{v['value']}({v['count']})" for v in stats["top_values"][:3])
            lines.append(f"  {col}: {stats['distinct']} distinct values — top: {top}")

    if "bedroom_summary" in profile:
        lines.append("Price by bedroom count:")
        for bed_val, s in profile["bedroom_summary"].items():
            lines.append(
                f"  {bed_val} BHK: {s['count']} units | "
                f"price range {s['min_price']:,.0f}–{s['max_price']:,.0f} | "
                f"avg {s['avg_price']:,.0f}"
            )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# LangChain @tool — used by real agent nodes
# ---------------------------------------------------------------------------

@tool
async def profile_data(csv_file_path: str, table_name: str) -> str:
    """Build a statistical profile of a CSV dataset and generate a domain-aware narrative.
    Detects domain (real_estate, hr, ecommerce, generic) and produces per-column stats
    plus an LLM-generated narrative summary.
    Returns the full profile text with narrative."""
    import pandas as pd
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage, SystemMessage

    try:
        df = pd.read_csv(csv_file_path)
    except Exception as exc:
        return f"Could not read CSV for profiling: {exc}"

    records = df.to_dict(orient="records")
    columns = list(df.columns)

    if not records:
        return "No data to profile."

    domain = _detect_domain(columns)
    profile = _build_profile(records, columns, domain)
    text = _profile_text(profile, table_name)

    try:
        llm = ChatAnthropic(model="claude-haiku-4-5-20251001")
        result = await llm.ainvoke([
            SystemMessage(content=(
                "You are a data analyst writing for a business stakeholder. "
                "Given a data profile, write a concise, insightful narrative (3–5 sentences). "
                "Be specific with numbers. "
                "For real estate data, comment on pricing trends by bedroom count. "
                "For HR data, comment on salary distribution by department. "
                "For e-commerce data, highlight top categories and revenue patterns."
            )),
            HumanMessage(content=f"Data profile:\n{text}\n\nWrite a narrative summary."),
        ])
        narrative = result.content if hasattr(result, "content") else str(result)
    except Exception as exc:
        narrative = f"[Narrative unavailable: {exc}]"

    return f"DATA PROFILE:\n{text}\n\nNARRATIVE:\n{narrative}"


async def run(state: dict) -> dict:
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage, SystemMessage
    from app.workflow_runner import _estimate_cost, _zero_usage

    records: list[dict] = state.get("clean_df_records", [])
    columns: list[str]  = state.get("clean_df_columns", [])
    table_name: str     = state.get("table_name", "dataset")

    if not records or not columns:
        return state

    domain  = _detect_domain(columns)
    profile = _build_profile(records, columns, domain)
    text    = _profile_text(profile, table_name)

    # LLM narrative
    narrative = ""
    new_usage = state.get("usage") or _zero_usage()
    model_id  = "claude-haiku-4-5-20251001"

    try:
        llm = ChatAnthropic(model=model_id)
        result = await llm.ainvoke([
            SystemMessage(content=(
                "You are a data analyst writing for a business stakeholder. "
                "Given a data profile, write a concise, insightful narrative (3–5 sentences). "
                "Be specific with numbers. "
                "For real estate data, comment on pricing trends by bedroom count. "
                "For HR data, comment on salary distribution by department. "
                "For e-commerce data, highlight top categories and revenue patterns."
            )),
            HumanMessage(content=f"Data profile:\n{text}\n\nWrite a narrative summary."),
        ])
        narrative = result.content if hasattr(result, "content") else str(result)

        usage_meta = getattr(result, "usage_metadata", None) or {}
        in_tok  = usage_meta.get("input_tokens", 0)
        out_tok = usage_meta.get("output_tokens", 0)
        cost    = _estimate_cost(model_id, in_tok, out_tok)
        prev    = state.get("usage") or _zero_usage()
        new_usage = {
            "input_tokens":        prev["input_tokens"]  + in_tok,
            "output_tokens":       prev["output_tokens"] + out_tok,
            "total_tokens":        prev["input_tokens"]  + in_tok + prev["output_tokens"] + out_tok,
            "estimated_cost_usd":  round(prev["estimated_cost_usd"] + cost, 6),
        }
    except Exception as exc:
        logger.error("LLM narrative error: %s", exc)
        narrative = f"[Narrative unavailable: {exc}]"

    profile["narrative"] = narrative

    profile_msg = f"DATA PROFILE:\n{text}\n\nNARRATIVE:\n{narrative}"

    return {
        **state,
        "data_profile": profile,
        "usage": new_usage,
        "messages": list(state.get("messages", [])) + [profile_msg],
    }
