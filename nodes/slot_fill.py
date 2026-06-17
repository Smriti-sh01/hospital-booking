"""nodes/slot_fill.py — merge slots, build options payload"""
from state import AppointmentState, REQUIRED_SLOTS
from flow_config import FLOW_CONFIG


def slot_fill_node(state: AppointmentState) -> dict:
    extracted = state.get("last_extracted_slots", {})
    filled    = {**state.get("filled_slots", {}), **extracted}
    pending   = [s for s in REQUIRED_SLOTS if s not in filled]
    response  = {}

    if pending:
        first = pending[0]
        cfg   = FLOW_CONFIG[first]
        cache = state.get("api_context", {})
        if first in cache:
            items = cache[first]
            opts  = [{"id": str(i.get("id", i.get("name", i.get("label", "")))), "value": i.get("name") or i.get("label", ""), "label": i.get("name") or i.get("label", "")} for i in items]
            response = {"type": "options", "slot": first,
                        "answer": cfg["question"], "options": opts}
        elif cfg.get("options"):
            response = {"type": "options", "slot": first,
                        "answer": cfg["question"],
                        "options": [{"id": o.lower(), "value": o, "label": o} for o in cfg["options"]]}
        else:
            response = {"type": "text", "answer": cfg["question"]}

    return {
        "filled_slots": filled, "pending_slots": pending,
        "last_extracted_slots": {}, "response": response,
        "step": "slot_fill_node",
    }