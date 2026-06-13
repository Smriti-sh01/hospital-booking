# """
# nodes/slot_fill.py
# ──────────────────
# NODE — slot_fill_node

# Two jobs in one node:
#   1. MERGE — fold last_extracted_slots into filled_slots and recompute
#              pending_slots.
#   2. ASK   — build the response payload asking the user for the first
#              pending slot (for slots where no API options are needed,
#              e.g. city).

# If api_chain_node already fetched options and stored them in api_context,
# this node also builds the slot_options payload from that cache so the
# router does not need a second pass.
# """
# from __future__ import annotations

# from state import AppointmentState, REQUIRED_SLOTS
# from flow_config import FLOW_CONFIG


# def slot_fill_node(state: AppointmentState) -> dict:
#     # ── Step 1: Merge newly extracted slots ──────────────────────────────
#     extracted = state.get("last_extracted_slots", {})
#     filled    = {**state.get("filled_slots", {}), **extracted}
#     pending   = [s for s in REQUIRED_SLOTS if s not in filled]

#     # ── Step 2: Build response for the first pending slot ────────────────
#     response: dict = {}

#     if pending:
#         first     = pending[0]
#         cfg       = FLOW_CONFIG.get(first, {})
#         api_cache = state.get("api_context", {})
#         api_key   = cfg.get("api_key")

#         if api_key and api_key in api_cache:
#             # Options already fetched by api_chain_node — send them now
#             raw_options = api_cache[api_key]
#             options = [
#                 {"id": item["id"], "label": item.get("name") or item.get("label", "")}
#                 for item in raw_options
#             ]
#             response = {
#                 "type":     "slot_options",
#                 "slot":     first,
#                 "question": cfg["question"],
#                 "options":  options,
#             }
#         else:
#             # Static options (e.g. city list) or plain question
#             static_opts = cfg.get("options", [])
#             if static_opts:
#                 response = {
#                     "type":     "slot_options",
#                     "slot":     first,
#                     "question": cfg["question"],
#                     "options":  [{"id": o.lower(), "label": o} for o in static_opts],
#                 }
#             else:
#                 response = {
#                     "type":    "text",
#                     "message": cfg.get("question", f"Please provide: {first}"),
#                 }

#     return {
#         "filled_slots":         filled,
#         "pending_slots":        pending,
#         "last_extracted_slots": {},     # clear after merge
#         "response":             response,
#         "step":                 "slot_fill_node",
#     }

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
        api_key = cfg.get("api_key")

        if api_key and api_key in cache:
            items = cache[api_key]
            opts  = [{"id": i["id"], "label": i.get("name") or i.get("label", "")} for i in items]
            response = {"type": "slot_options", "slot": first,
                        "question": cfg["question"], "options": opts}
        elif cfg.get("options"):
            response = {"type": "slot_options", "slot": first,
                        "question": cfg["question"],
                        "options": [{"id": o.lower(), "label": o} for o in cfg["options"]]}
        else:
            response = {"type": "text", "message": cfg["question"]}

    return {
        "filled_slots": filled, "pending_slots": pending,
        "last_extracted_slots": {}, "response": response,
        "step": "slot_fill_node",
    }