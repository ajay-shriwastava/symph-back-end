"""Tools router — exposes tool parameter metadata."""

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.tools import TOOL_PARAMS

router = APIRouter(prefix="/api/v1/tools", tags=["tools"])


@router.get("/params")
async def get_tool_params(_: dict = Depends(get_current_user)) -> dict:
    """Return configurable parameters for every pipeline and LLM tool."""
    return TOOL_PARAMS
