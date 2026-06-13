"""
channels/whatsapp.py
────────────────────
WhatsApp channel adapter (using WATI as the BSP).

WATI sends a POST webhook for every incoming message.  Two payload types:
  1. Regular text message  → payload["text"]
  2. List reply (user tapped an option)  → payload["listReply"]["title"]

After the graph runs, this adapter sends the response back via the
WATI REST API (see api/wati_client.py).
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def parse_wati_payload(payload: dict) -> tuple[str, str]:
    """
    Extract (channel_id, user_text) from a WATI webhook payload.

    Returns:
        channel_id : "whatsapp:<phone_number>"
        text       : cleaned user message string
    """
    phone = payload.get("waId") or payload.get("from", "unknown")

    # Text message
    text: str = ""
    if "text" in payload:
        text = payload["text"].get("body", "") if isinstance(payload["text"], dict) else str(payload["text"])

    # Interactive list reply (user tapped a slot option)
    elif "listReply" in payload:
        text = payload["listReply"].get("title", "")

    # Button reply
    elif "buttonReply" in payload:
        text = payload["buttonReply"].get("title", "")

    return f"whatsapp:{phone}", text.strip()


def is_duplicate(payload: dict, seen_ids: set) -> bool:
    """Simple dedup — WATI occasionally re-delivers messages."""
    msg_id: Optional[str] = payload.get("id") or payload.get("wamid")
    if msg_id and msg_id in seen_ids:
        return True
    if msg_id:
        seen_ids.add(msg_id)
    return False