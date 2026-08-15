"""
VoyageAI embedding helper.

Calls the VoyageAI REST API via httpx (already in requirements).
Model: voyage-3-lite  — 512 dimensions, optimised for speed & cost.

Env var required:  VOYAGE_API_KEY
"""

import json
import logging
import os
import re

import httpx

logger = logging.getLogger(__name__)

_VOYAGE_URL = "https://api.voyageai.com/v1/embeddings"
_MODEL = "voyage-3-lite"
_DIMS = 512

# Chunking parameters
_CHUNK_SIZE = 500   # target chars per chunk
_OVERLAP = 50       # overlap between consecutive chunks


def _get_api_key() -> str:
    key = os.environ.get("VOYAGE_API_KEY", "")
    if not key:
        raise RuntimeError("VOYAGE_API_KEY environment variable is not set")
    return key


async def embed(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of strings using VoyageAI voyage-3-lite.

    Returns a list of 512-dimensional float vectors in the same order as input.
    """
    if not texts:
        return []

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            _VOYAGE_URL,
            headers={
                "Authorization": f"Bearer {_get_api_key()}",
                "Content-Type": "application/json",
            },
            content=json.dumps({"model": _MODEL, "input": texts}),
        )
        resp.raise_for_status()
        data = resp.json()

    # VoyageAI returns {"data": [{"embedding": [...], "index": N}, ...]}
    items = sorted(data["data"], key=lambda x: x["index"])
    return [item["embedding"] for item in items]


def chunk_text(text: str) -> list[str]:
    """
    Split text into overlapping sentence-aware chunks of ~_CHUNK_SIZE chars.

    Strategy:
      1. Split on sentence boundaries (. ! ?)
      2. Accumulate sentences into chunks until the size limit is reached
      3. Start each new chunk with the last _OVERLAP chars of the previous one
    """
    # Split on sentence endings, keeping the delimiter
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= _CHUNK_SIZE:
            current = (current + " " + sentence).strip()
        else:
            if current:
                chunks.append(current)
                # Overlap: carry the tail of the previous chunk
                current = current[-_OVERLAP:].strip() + " " + sentence
                current = current.strip()
            else:
                # Single sentence longer than chunk size — store as-is
                chunks.append(sentence)
                current = sentence[-_OVERLAP:].strip()

    if current:
        chunks.append(current)

    return chunks or [text]
