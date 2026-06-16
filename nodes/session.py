"""
nodes/session.py
────────────────
NODE 2 — session_load_node
NODE 8 — session_write_node

session_load_node:
    Loads the persisted AppointmentState for the current channel_id and
    merges it with the incoming partial state (which only has channel_id
    and the new user message).  This gives downstream nodes full context
    from the previous turns.

session_write_node:
    Called just before response_node.  Persists the final state of this
    graph run so the NEXT message can load it back.
"""
from __future__ import annotations

from state import AppointmentState
import session_store


def session_load_node(state: AppointmentState) -> dict:
    """
    Merge persisted session state into the current (partial) state.

    The incoming state at this point only contains:
        channel_id, messages (with the new user message appended)

    We load the full previous state and merge — current keys win so the
    new user message is preserved.
    """
    channel_id = state.get("channel_id", "unknown")
    persisted = session_store.load_session(channel_id)

    # Build merged state: persisted base + current overrides
    merged = {**persisted, **state}

    # Always append the new user message to the persisted history
    # (avoid duplicates if the message was already in persisted messages)
    new_messages = state.get("messages", [])
    old_messages = persisted.get("messages", [])

    if new_messages and (not old_messages or old_messages[-1] != new_messages[-1]):
        merged["messages"] = old_messages + [new_messages[-1]]
    else:
        merged["messages"] = old_messages

    merged["step"] = "session_load"
    return merged


def session_write_node(state: AppointmentState) -> dict:
    """
    Persist the current state snapshot.  Called after all logic nodes,
    before response_node emits the reply.
    """
    channel_id = state.get("channel_id", "unknown")
    session_store.save_session(channel_id, state)
    return {"step": "session_write"}
    