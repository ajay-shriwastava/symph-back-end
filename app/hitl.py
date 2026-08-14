"""
Human-in-the-loop pause / resume registry.

When a workflow hits a human_review node it registers an asyncio.Event here
and awaits it. The /resume endpoint fires the event and injects human input,
allowing the node — and the rest of the graph — to continue.

State is in-memory: if the process restarts while a run is paused the event
is lost and the run will remain stuck in `awaiting_review`. Operators can
reset it with:
    UPDATE workflow_runs SET status='failed', error='manually reset'
    WHERE status='awaiting_review';
"""
import asyncio

# run_id (str) -> (event, input_holder)
# input_holder is a list so it is mutable from the resume() caller.
_pending: dict[str, tuple[asyncio.Event, list[str]]] = {}


def register(run_id: str) -> tuple[asyncio.Event, list[str]]:
    """Register a new pause point for *run_id*. Returns (event, holder)."""
    event = asyncio.Event()
    holder: list[str] = []
    _pending[run_id] = (event, holder)
    return event, holder


def resume(run_id: str, human_input: str) -> bool:
    """
    Inject *human_input* and unblock the waiting node.
    Returns True if a pending review existed, False if the run was not found.
    """
    entry = _pending.get(run_id)
    if entry is None:
        return False
    event, holder = entry
    holder.append(human_input)
    event.set()
    return True


def cleanup(run_id: str) -> None:
    """Remove the registry entry once the node has resumed."""
    _pending.pop(run_id, None)


def is_pending(run_id: str) -> bool:
    return run_id in _pending
