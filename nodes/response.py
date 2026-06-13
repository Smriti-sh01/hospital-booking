"""
nodes/response.py
─────────────────
NODE — response_node  (final node before END)

Reads state["response"] (set by whichever logic node ran) and emits it
to the correct channel:
  • webchat   → sends JSON string back over the WebSocket connection
                (the connection object is injected via a thread-local)
  • whatsapp  → calls the WATI API

The node itself does NOT build the response payload — it only dispatches
the one already in state.  This keeps all logic nodes channel-agnostic.
"""
from __future__ import annotations

import json
import logging
from contextvars import ContextVar

from state import AppointmentState

logger = logging.getLogger(__name__)

# ── WebSocket injection ───────────────────────────────────────────────────
# The WebSocket handler injects the live WS connection into this ContextVar
# before invoking the graph.  response_node reads it to send the reply.
# For WhatsApp the channel adapter handles sending AFTER graph.invoke().
ws_context: ContextVar = ContextVar("ws_context", default=None)


async def response_node(state: AppointmentState) -> dict:
    response   = state.get("response")
    channel_id = state.get("channel_id", "")

    if not response:
        logger.warning("response_node: no response payload in state")
        return {"step": "response_node"}

    # Append assistant message to conversation history
    messages = list(state.get("messages", []))
    messages.append({
        "role":    "assistant",
        "content": response.get("message") or json.dumps(response),
    })

    # ── WebChat: send over WebSocket ──────────────────────────────────────
    if channel_id.startswith("webchat:"):
        ws = ws_context.get()
        if ws:
            try:
                await ws.send_text(json.dumps(response))
            except Exception as exc:
                logger.error("WebSocket send failed: %s", exc)

    # WhatsApp replies are sent AFTER graph.invoke() by the webhook handler
    # (see channels/whatsapp.py) — nothing to do here for that channel.

    return {
        "messages": messages,
        "step":     "response_node",
    }