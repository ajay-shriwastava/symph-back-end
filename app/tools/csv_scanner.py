"""
csv_scanner — Tool node + LangChain @tool

Scans DATASET_DIR for CSV files and picks the most recently modified one.
"""

import json
import logging
import os
import re

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

DATASET_DIR = os.environ.get(
    "DATASET_DIR",
    "/Users/ajay/tech/yuno/symph-prgm-mgmt/dataset",
)
INPUT_DIR     = os.path.join(DATASET_DIR, "input")
OUTPUT_DIR    = os.path.join(DATASET_DIR, "output")
ERROR_DIR     = os.path.join(DATASET_DIR, "error")
PROCESSED_DIR = os.path.join(DATASET_DIR, "processed")


# ---------------------------------------------------------------------------
# LangChain @tool — used by real agent nodes
# ---------------------------------------------------------------------------

@tool
async def scan_csv() -> str:
    """Scan the dataset input directory for the most recently modified CSV file to process.
    Returns JSON with: found (bool), file_path, filename, table_name.
    Call this first in the data ingestion pipeline."""
    os.makedirs(INPUT_DIR, exist_ok=True)
    try:
        csv_files = [
            f for f in os.listdir(INPUT_DIR)
            if f.lower().endswith(".csv") and os.path.isfile(os.path.join(INPUT_DIR, f))
        ]
    except Exception as exc:
        return json.dumps({"found": False, "error": str(exc)})

    if not csv_files:
        return json.dumps({"found": False, "message": "No CSV files found in input directory. Nothing to process."})

    csv_files.sort(key=lambda f: os.path.getmtime(os.path.join(INPUT_DIR, f)), reverse=True)
    chosen = csv_files[0]
    file_path = os.path.join(INPUT_DIR, chosen)
    stem = os.path.splitext(chosen)[0].lower()
    table_name = re.sub(r"[^a-z0-9_]", "_", stem).strip("_")
    if not table_name or table_name[0].isdigit():
        table_name = "data_" + table_name

    return json.dumps({
        "found": True,
        "file_path": file_path,
        "filename": chosen,
        "table_name": table_name,
    })


async def run(state: dict) -> dict:
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(ERROR_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    try:
        csv_files = [
            f
            for f in os.listdir(INPUT_DIR)
            if f.lower().endswith(".csv") and os.path.isfile(os.path.join(INPUT_DIR, f))
        ]
    except Exception as exc:
        logger.error("Error scanning input dir %s: %s", INPUT_DIR, exc)
        return {**state, "condition_result": False, "csv_file_path": None}

    if not csv_files:
        logger.info("No CSV files found in %s", INPUT_DIR)
        return {
            **state,
            "condition_result": False,
            "csv_file_path": None,
            "messages": list(state.get("messages", [])) + ["No CSV files found in input directory."],
        }

    # Pick the most recently modified file
    csv_files.sort(
        key=lambda f: os.path.getmtime(os.path.join(INPUT_DIR, f)),
        reverse=True,
    )
    chosen = csv_files[0]
    file_path = os.path.join(INPUT_DIR, chosen)

    # Derive a safe PostgreSQL table name from the filename
    stem = os.path.splitext(chosen)[0].lower()
    table_name = re.sub(r"[^a-z0-9_]", "_", stem).strip("_")
    if not table_name or table_name[0].isdigit():
        table_name = "data_" + table_name

    logger.info("Selected CSV: %s → table: %s", file_path, table_name)

    return {
        **state,
        "condition_result": True,
        "csv_file_path": file_path,
        "csv_filename": chosen,
        "table_name": table_name,
        "output_dir": OUTPUT_DIR,
        "error_dir": ERROR_DIR,
        "processed_dir": PROCESSED_DIR,
        "messages": list(state.get("messages", [])) + [f"Found CSV file: {chosen} → table: {table_name}"],
    }
