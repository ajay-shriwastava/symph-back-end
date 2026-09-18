"""
MCP management REST endpoints (frontend use only).

GET /api/v1/mcp/audit-log   — paginated audit log
GET /api/v1/mcp/tools       — list of all 8 MCP tool descriptions
"""

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.mcp_audit_log import McpAuditLog
from app.schemas.mcp import McpAuditLogOut, McpAuditLogPage, McpToolInfo

router = APIRouter(prefix="/api/v1/mcp", tags=["mcp"])

_MCP_TOOLS: list[McpToolInfo] = [
    McpToolInfo(name="get_memory",         category="memory",    description="Retrieve a single memory entry for an agent by key."),
    McpToolInfo(name="list_memory",        category="memory",    description="List all memory entries for an agent."),
    McpToolInfo(name="set_memory",         category="memory",    description="Upsert a memory key-value pair for an agent."),
    McpToolInfo(name="delete_memory",      category="memory",    description="Delete a memory entry for an agent by key."),
    McpToolInfo(name="list_knowledge",     category="knowledge", description="List knowledge base entries (paginated)."),
    McpToolInfo(name="add_knowledge",      category="knowledge", description="Ingest a text document into the knowledge base."),
    McpToolInfo(name="add_knowledge_file", category="knowledge", description="Ingest a PDF or TXT file (base64-encoded) into the knowledge base."),
    McpToolInfo(name="search_knowledge",   category="knowledge", description="Semantic similarity search over the knowledge base."),
]


@router.get("/tools", response_model=list[McpToolInfo])
async def get_mcp_tools(_: dict = Depends(get_current_user)) -> list[McpToolInfo]:
    return _MCP_TOOLS


@router.get("/audit-log", response_model=McpAuditLogPage)
async def get_audit_log(
    skip: int = 0,
    limit: int = 50,
    caller_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> McpAuditLogPage:
    limit = max(1, min(limit, 200))

    query = select(McpAuditLog).order_by(McpAuditLog.created_at.desc())
    count_query = select(func.count()).select_from(McpAuditLog)

    if caller_id:
        query = query.where(McpAuditLog.caller_id == caller_id)
        count_query = count_query.where(McpAuditLog.caller_id == caller_id)

    total = (await db.execute(count_query)).scalar_one()
    rows = (await db.execute(query.offset(skip).limit(limit))).scalars().all()

    return McpAuditLogPage(
        items=[McpAuditLogOut.model_validate(r) for r in rows],
        total=total,
        skip=skip,
        limit=limit,
    )
