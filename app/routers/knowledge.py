"""
Knowledge Base API

POST   /api/v1/knowledge          — ingest a document (chunks + embeds)
GET    /api/v1/knowledge          — list entries (paginated)
DELETE /api/v1/knowledge/{id}     — delete a single entry
POST   /api/v1/knowledge/search   — semantic similarity search
"""

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.embeddings import chunk_text, embed
from app.models.knowledge import KnowledgeEntry
from app.schemas.knowledge import (
    KnowledgeEntryOut,
    KnowledgeIngestPayload,
    KnowledgeSearchPayload,
    KnowledgeSearchResult,
)

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


@router.post("", response_model=list[KnowledgeEntryOut], status_code=201)
async def ingest_document(
    payload: KnowledgeIngestPayload,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
    """
    Chunk the document, embed each chunk with VoyageAI, and store in knowledge_base.
    Returns all created entries.
    """
    chunks = chunk_text(payload.content)
    vectors = await embed(chunks)

    created: list[KnowledgeEntry] = []
    for chunk, vector in zip(chunks, vectors):
        entry_id = uuid.uuid4()
        # Use raw SQL so we can pass the embedding with ::vector cast.
        # This avoids asyncpg needing to encode/decode the pgvector VECTOR type.
        await db.execute(
            text("""
                INSERT INTO knowledge_base (id, title, content, embedding, metadata_, created_at)
                VALUES (:id, :title, :content, CAST(:embedding AS vector), CAST(:metadata AS jsonb), NOW())
            """),
            {
                "id": str(entry_id),
                "title": payload.title,
                "content": chunk,
                "embedding": json.dumps(vector),
                "metadata": json.dumps(payload.metadata),
            },
        )
        # Fetch back via ORM for the response model
        row = (
            await db.execute(
                select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id)
            )
        ).scalar_one()
        created.append(row)

    await db.commit()
    # Refresh rows after commit
    for row in created:
        await db.refresh(row)

    return [
        KnowledgeEntryOut(
            id=r.id,
            title=r.title,
            content=r.content,
            metadata=r.metadata_,
            created_at=r.created_at,
        )
        for r in created
    ]


@router.get("", response_model=list[KnowledgeEntryOut])
async def list_knowledge(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
    rows = (
        await db.execute(
            select(KnowledgeEntry)
            .order_by(KnowledgeEntry.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
    ).scalars().all()
    return [
        KnowledgeEntryOut(
            id=r.id,
            title=r.title,
            content=r.content,
            metadata=r.metadata_,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.delete("/{entry_id}", status_code=204)
async def delete_knowledge(
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
    row = (
        await db.execute(
            select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id)
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Entry not found")
    await db.delete(row)
    await db.commit()


@router.post("/search", response_model=list[KnowledgeSearchResult])
async def search_knowledge(
    payload: KnowledgeSearchPayload,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
    """
    Semantic similarity search using pgvector cosine distance.
    Returns top_k most relevant chunks ordered by similarity score.
    """
    top_k = max(1, min(payload.top_k, 20))
    vectors = await embed([payload.query])
    query_vec = json.dumps(vectors[0])

    # We deliberately exclude the embedding column from SELECT to avoid
    # asyncpg needing to decode the VECTOR type (no codec registered).
    result = await db.execute(
        text("""
            SELECT
                id,
                title,
                content,
                metadata_,
                created_at,
                1 - (embedding <=> CAST(:query AS vector)) AS score
            FROM knowledge_base
            ORDER BY embedding <=> CAST(:query AS vector)
            LIMIT :top_k
        """),
        {"query": query_vec, "top_k": top_k},
    )
    rows = result.mappings().all()
    return [
        KnowledgeSearchResult(
            id=r["id"],
            title=r["title"],
            content=r["content"],
            metadata=r["metadata_"] or {},
            score=float(r["score"]),
        )
        for r in rows
    ]
