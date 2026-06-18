"""
session_store.py — in-process session store (no Redis)
"""

import os
import time
from copy import deepcopy
from state import AppointmentState, REQUIRED_SLOTS

SESSION_TTL = int(os.getenv("SESSION_TTL_SECONDS", "1800"))

# internal store
_store: dict[str, dict] = {}


def _fresh_state(channel_id: str) -> AppointmentState:
    return AppointmentState(
        messages=[],
        channel_id=channel_id,
        active_flow=None,
        filled_slots={},
        pending_slots=list(REQUIRED_SLOTS),
        last_extracted_slots={},
        api_context={},
        resolved_ids={},
        confirmed=False,
        intent_change=False,
        confirm_retries=0,
    )


def load_session(channel_id: str) -> AppointmentState:
    entry = _store.get(channel_id)

    #  valid session
    if entry and (time.time() - entry["ts"]) < SESSION_TTL:
        entry["ts"] = time.time()  # refresh TTL

        state_dict = entry["state"]

        # ensure pending_slots is always correct
        filled = state_dict.get("filled_slots", {})
        state_dict["pending_slots"] = [
            slot for slot in REQUIRED_SLOTS if slot not in filled
        ]

        return AppointmentState(**state_dict)

    # expired or new
    return _fresh_state(channel_id)


def save_session(channel_id: str, state: AppointmentState) -> None:
    state_dict = dict(state)

    #  always recompute pending slots before saving
    filled = state_dict.get("filled_slots", {})
    state_dict["pending_slots"] = [
        slot for slot in REQUIRED_SLOTS if slot not in filled
    ]

    _store[channel_id] = {
        "state": deepcopy(state_dict),  # avoid mutation bugs
        "ts": time.time(),
    }


def clear_session(channel_id: str) -> None:
    _store.pop(channel_id, None)