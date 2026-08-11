from contextvars import ContextVar

tool_config: ContextVar[dict] = ContextVar("tool_config", default={})
