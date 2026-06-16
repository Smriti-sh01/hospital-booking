"""
state.py
────────
Typed state dict shared across every LangGraph node.
Nodes return PARTIAL dicts — LangGraph merges them automatically.
"""
from __future__ import annotations
from typing import Any, Optional
from typing_extensions import TypedDict

REQUIRED_SLOTS: list[str] = ["city", "branch", "department", "doctor", "time_slot"]


class AppointmentState(TypedDict, total=False):
    # ── channel ──────────────────────────────────────────────────────────
    channel_id: str                    
    messages:   list[dict[str, str]]   

    # ── intent ───────────────────────────────────────────────────────────
    intent:           Optional[str]    
    intent_change:    bool
    proposed_intent:  Optional[str]
    active_flow:      Optional[str]

    # ── slots ─────────────────────────────────────────────────────────────
    filled_slots:         dict[str, str]
    pending_slots:        list[str]
    last_extracted_slots: dict[str, str]

    # ── confirmation guard ────────────────────────────────────────────────
    awaiting_confirm: Optional[str]    
    confirm_retries:  int

    # ── API cache ─────────────────────────────────────────────────────────
    api_context: dict[str, Any]       

    # ── outbound payload ──────────────────────────────────────────────────
    response: Optional[dict]         

    # ── control ───────────────────────────────────────────────────────────
    step:        Optional[str]
    confirmed:   bool
    booking_ref: Optional[str]