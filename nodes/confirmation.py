"""
nodes/confirmation.py
─────────────────────
NODE — confirmation_node
NODE — confirmation_handler

confirmation_node:
    Called when either:
      (a) all slots are filled  →  ask "please confirm your booking"
      (b) intent_change detected →  ask "are you sure you want to switch?"

    Sets awaiting_confirm so the router sends the NEXT message here.

confirmation_handler:
    Processes the user's yes/no reply.

    For booking confirmation YES:
        → calls POST /appointments via hms_client
        → sets confirmed=True, booking_ref

    For intent switch YES:
        → resets filled_slots, pending_slots, active_flow

    For NO (or ambiguous) → resumes original flow or re-asks (max 3 retries)
"""
from __future__ import annotations

import logging
from state import AppointmentState, REQUIRED_SLOTS
from api.hms_client import confirm_booking

logger = logging.getLogger(__name__)

_YES_WORDS = {"yes", "y", "confirm", "ok", "sure", "yeah", "yep", "haan", "ha"}
_NO_WORDS  = {"no",  "n", "cancel",  "nope", "nahi", "nah", "change"}


# ── confirmation_node ─────────────────────────────────────────────────────

def confirmation_node(state: AppointmentState) -> dict:
    """Build the confirmation question and set awaiting_confirm."""

    if state.get("intent_change"):
        # Intent switch confirmation
        new_intent = state.get("proposed_intent", "a new service")
        message = (
            f"You're currently booking an appointment. "
            f"You seem to want to switch to: *{new_intent}*.\n\n"
            f"Are you sure you want to start over?\n"
            f"Reply *YES* to switch or *NO* to continue the current booking."
        )
        return {
            "awaiting_confirm": "intent_switch",
            "response":         {"type": "text", "message": message},
            "step":             "confirmation_node",
        }

    # Booking confirmation — summarise slots
    fs = state.get("filled_slots", {})
    summary = (
        "Please confirm your appointment details:\n\n"
        f"  🏥 Branch     : {fs.get('branch', '—')}\n"
        f"  🏬 Department : {fs.get('department', '—')}\n"
        f"  👨‍⚕️ Doctor     : {fs.get('doctor', '—')}\n"
        f"  🕐 Time slot  : {fs.get('time_slot', '—')}\n\n"
        "Reply *YES* to confirm or *NO* to change details."
    )
    return {
        "awaiting_confirm": "booking",
        "intent_change":    False,        # clear the flag
        "response":         {"type": "text", "message": summary},
        "step":             "confirmation_node",
    }


# ── confirmation_handler ──────────────────────────────────────────────────

async def confirmation_handler(state: AppointmentState) -> dict:
    """Process the user's yes/no response."""
    messages   = state.get("messages", [])
    mode       = state.get("awaiting_confirm")
    retries    = state.get("confirm_retries", 0)

    last_text  = _last_user_text(messages).lower().strip()
    is_yes     = any(w in last_text.split() for w in _YES_WORDS)
    is_no      = any(w in last_text.split() for w in _NO_WORDS)

    # ── YES ───────────────────────────────────────────────────────────────
    if is_yes:
        if mode == "booking":
            return await _do_booking(state)

        if mode == "intent_switch":
            return {
                "active_flow":          state.get("proposed_intent"),
                "filled_slots":         {},
                "pending_slots":        list(REQUIRED_SLOTS),
                "awaiting_confirm":     None,
                "proposed_intent":      None,
                "intent_change":        False,
                "api_context":          {},
                "confirm_retries":      0,
                "response":             {
                    "type":    "text",
                    "message": "Sure! Let's start fresh. " + _first_slot_question(),
                },
                "step": "confirmation_handler",
            }

    # ── NO ────────────────────────────────────────────────────────────────
    if is_no:
        if mode == "intent_switch":
            # Resume original flow
            pending = state.get("pending_slots", [])
            resume_msg = (
                "No problem! Continuing your current booking.\n"
                + _pending_question(pending, state)
            )
            return {
                "awaiting_confirm":  None,
                "proposed_intent":   None,
                "intent_change":     False,
                "confirm_retries":   0,
                "response":          {"type": "text", "message": resume_msg},
                "step":              "confirmation_handler",
            }

        if mode == "booking":
            return {
                "awaiting_confirm":  None,
                "pending_slots":     list(REQUIRED_SLOTS),  # allow re-collection
                "filled_slots":      {},
                "api_context":       {},
                "confirm_retries":   0,
                "response":          {
                    "type":    "text",
                    "message": "No problem! Let's start over.\n" + _first_slot_question(),
                },
                "step": "confirmation_handler",
            }

    # ── Ambiguous ─────────────────────────────────────────────────────────
    new_retries = retries + 1
    if new_retries >= 3:
        # Give up waiting, resume original flow silently
        return {
            "awaiting_confirm": None,
            "confirm_retries":  0,
            "response": {
                "type":    "text",
                "message": "I'll take that as a no. " + _pending_question(
                    state.get("pending_slots", []), state
                ),
            },
            "step": "confirmation_handler",
        }

    return {
        "confirm_retries": new_retries,
        "response": {
            "type":    "text",
            "message": "Please reply *YES* to confirm or *NO* to cancel.",
        },
        "step": "confirmation_handler",
    }


# ── booking call ──────────────────────────────────────────────────────────

async def _do_booking(state: AppointmentState) -> dict:
    resolved   = state.get("api_context", {}).get("resolved", {})
    channel_id = state.get("channel_id", "unknown")

    if not resolved:
        logger.error("No resolved IDs in api_context for booking")
        return {
            "response": {
                "type":    "text",
                "message": "Sorry, something went wrong resolving your booking details. Please try again.",
            },
            "awaiting_confirm": None,
            "step": "confirmation_handler",
        }

    try:
        result = await confirm_booking(
            hospital_id   = resolved["hospital_id"],
            department_id = resolved["department_id"],
            doctor_id     = resolved["doctor_id"],
            slot_id       = resolved["slot_id"],
            patient_channel_id = channel_id,
        )
        ref = result.get("booking_ref", "N/A")
        fs  = state.get("filled_slots", {})
        return {
            "confirmed":        True,
            "booking_ref":      ref,
            "awaiting_confirm": None,
            "confirm_retries":  0,
            "response": {
                "type":        "booking_confirmed",
                "booking_ref": ref,
                "message": (
                    f"✅ Appointment confirmed!\n\n"
                    f"  📋 Ref       : {ref}\n"
                    f"  🏥 Branch    : {fs.get('branch')}\n"
                    f"  🏬 Dept      : {fs.get('department')}\n"
                    f"  👨‍⚕️ Doctor    : {fs.get('doctor')}\n"
                    f"  🕐 Time      : {fs.get('time_slot')}\n\n"
                    f"You will receive a reminder before your appointment."
                ),
            },
            "step": "confirmation_handler",
        }
    except Exception as exc:
        logger.error("Booking API failed: %s", exc)
        return {
            "awaiting_confirm": None,
            "response": {
                "type":    "text",
                "message": "Sorry, the booking could not be completed. Please try again.",
            },
            "step": "confirmation_handler",
        }


# ── Helpers ───────────────────────────────────────────────────────────────

def _last_user_text(messages: list[dict]) -> str:
    for m in reversed(messages):
        if m.get("role") == "user":
            return m.get("content", "")
    return ""


def _first_slot_question() -> str:
    from flow_config import FLOW_CONFIG
    return FLOW_CONFIG["city"]["question"]


def _pending_question(pending: list[str], state: AppointmentState) -> str:
    from flow_config import FLOW_CONFIG
    if not pending:
        return ""
    return FLOW_CONFIG.get(pending[0], {}).get("question", "")