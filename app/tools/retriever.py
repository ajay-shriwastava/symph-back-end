"""
retrieve_context — LangChain @tool for RAG.

Agents can call this tool to fetch relevant context from the knowledge base
based on a query string. It embeds the query with VoyageAI, performs a
pgvector cosine-similarity search, and returns the top chunks as text.
"""

import json
import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

_DEFAULT_TOP_K = 5


@tool
async def retrieve_context(query: str, top_k: int = _DEFAULT_TOP_K) -> str:
    """
    Retrieve relevant context from the knowledge base for the given query.

    Args:
        query: The search query — use the core question or topic.
        top_k: Number of chunks to retrieve (default 5, max 20).

    Returns:
        Retrieved context chunks separated by '---', or a message saying
        no relevant context was found.
    """
    from app.embeddings import embed
    from app.database import AsyncSessionLocal
    from sqlalchemy import text

    top_k = max(1, min(int(top_k), 20))

    try:
        vectors = await embed([query])
        query_vec = json.dumps(vectors[0])

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("""
                    SELECT title, content,
                           1 - (embedding <=> CAST(:query AS vector)) AS score
                    FROM knowledge_base
                    ORDER BY embedding <=> CAST(:query AS vector)
                    LIMIT :top_k
                """),
                {"query": query_vec, "top_k": top_k},
            )
            rows = result.mappings().all()

        if not rows:
            return "No relevant context found in the knowledge base."

        parts = [
            f"[Source: {r['title']} | relevance: {r['score']:.2f}]\n{r['content']}"
            for r in rows
        ]
        return "\n---\n".join(parts)

    except Exception as exc:
        logger.warning("retrieve_context failed: %s", exc)
        return f"Knowledge base retrieval failed: {exc}"
