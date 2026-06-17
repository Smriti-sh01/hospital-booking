from state import AppointmentState
from flow_config import FLOW_CONFIG


def router(state: AppointmentState) -> str:
    intent = state.get("intent")
    active_flow = state.get("active_flow")
    awaiting_confirm = state.get("awaiting_confirm", False)
    intent_change = state.get("intent_change", False)

    from state import REQUIRED_SLOTS
    extracted = state.get("last_extracted_slots", {})
    filled = {**state.get("filled_slots", {}), **extracted}
    pending = [s for s in REQUIRED_SLOTS if s not in filled]

    # ✅ 1. GREETING (HIGHEST PRIORITY ALWAYS)
    if intent == "greeting":
        return "greeting_node"

    # ✅ 2. HANDLE ERRORS DIRECTLY
    if intent == "error":
        return "session_write"

    # ✅ 3. INFO QUERY
    if intent == "info_query":
        return "info_node"

    # ✅ 3. START BOOKING FLOW
    if intent == "book_appointment":
        state["active_flow"] = "booking"
        active_flow = "booking"

    # ✅ 4. HANDLE INTENT CHANGE (ONLY DURING BOOKING)
    if intent_change and active_flow == "booking":
        return "confirmation_node"

    # ✅ 5. HANDLE CONFIRMATION STEP
    if awaiting_confirm:
        return "confirmation_handler"

    # ✅ 6. CONTINUE BOOKING FLOW
    if active_flow == "booking":
        if not pending:
            return "confirmation_node"

        current_slot = pending[0]

        # if slot requires API
        if FLOW_CONFIG.get(current_slot, {}).get("api"):
            return "api_chain_node"

        return "slot_fill_node"

    # ✅ 7. FALLBACK (GENERAL CHAT)
    return "greeting_node"