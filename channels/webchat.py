"""
channels/webchat.py
───────────────────
WebSocket channel adapter.

Protocol (JSON over WebSocket):
  Incoming from browser:
      { "text": "I want to book an appointment in Delhi" }

  Outgoing to browser (one of three shapes):
      { "type": "text",       "message": "Which branch..." }
      { "type": "slot_options", "slot": "branch", "question": "...", "options": [...] }
      { "type": "booking_confirmed", "booking_ref": "APT-…", "message": "..." }

The WebSocket handler:
  1. Accepts the connection
  2. Loops: receive text → build initial state → invoke graph → (response
     is sent inside response_node via the ws_context ContextVar)
"""
from __future__ import annotations

import json
import logging

from fastapi import WebSocket, WebSocketDisconnect

from graph import compiled_graph
from nodes.response import ws_context

logger = logging.getLogger(__name__)


async def handle_websocket(ws: WebSocket, session_id: str) -> None:
    """Main loop for a single WebChat WebSocket connection."""
    await ws.accept()
    channel_id = f"webchat:{session_id}"
    logger.info("WebSocket connected: %s", channel_id)

    # Inject the live WebSocket into the ContextVar so response_node can use it
    token = ws_context.set(ws)

    try:
        while True:
            raw = await ws.receive_text()

            try:
                data = json.loads(raw)
                text = data.get("text", "").strip()
            except json.JSONDecodeError:
                text = raw.strip()

            if not text:
                continue

            # Build the minimal initial state for this graph run
            initial_state = {
                "channel_id": channel_id,
                "messages":   [{"role": "user", "content": text}],
            }

            # Run the full graph — response_node sends the reply over the WS
            await compiled_graph.ainvoke(initial_state)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: %s", channel_id)
    except Exception as exc:
        logger.error("WebSocket error (%s): %s", channel_id, exc)
        try:
            await ws.send_text(json.dumps({
                "type":    "text",
                "message": "An unexpected error occurred. Please try again.",
            }))
        except Exception:
            pass
    finally:
        ws_context.reset(token)