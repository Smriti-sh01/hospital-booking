# """
# nodes/api_chain.py
# ──────────────────
# NODE — api_chain_node

# Executes the HMS API dependency chain for the FIRST pending slot that
# needs live options.  Results are cached in api_context so each endpoint
# is called at most ONCE per session.

# Chain:
#   city filled   → GET /hospitals?city=          → hospitals list + hospital_id
#   branch filled → GET /departments?hospital_id= → departments list + department_id
#   dept  filled  → GET /doctors?department_id=   → doctors list + doctor_id
#   doctor filled → GET /slots?doctor_id=          → slots list + slot_id

# After this node runs, slot_fill_node reads api_context and builds the
# options payload for the user.

# When all slots are filled (pending=[]), this node resolves ALL IDs and
# stores them in api_context["resolved"] so confirm_booking can use them.
# """
# from __future__ import annotations

# import logging
# from state import AppointmentState
# from api.hms_client import (
#     fetch_hospitals,
#     fetch_departments,
#     fetch_doctors,
#     fetch_time_slots,
#     resolve_id,
# )

# logger = logging.getLogger(__name__)


# async def api_chain_node(state: AppointmentState) -> dict:
#     filled  = state.get("filled_slots", {})
#     pending = state.get("pending_slots", [])
#     cache   = dict(state.get("api_context", {}))

#     try:
#         if not pending:
#             # All slots filled — resolve every ID for the booking call
#             cache = await _resolve_all_ids(filled, cache)
#         else:
#             first = pending[0]
#             cache = await _fetch_for_slot(first, filled, cache)

#     except Exception as exc:
#         logger.error("api_chain_node error: %s", exc)
#         return {
#             "api_context": cache,
#             "response":    {"type": "text", "message": "Sorry, there was an error fetching options. Please try again."},
#             "step":        "api_chain_node",
#         }

#     return {
#         "api_context": cache,
#         "step":        "api_chain_node",
#     }


# # ── Private helpers ───────────────────────────────────────────────────────

# async def _fetch_for_slot(
#     slot: str,
#     filled: dict,
#     cache: dict,
# ) -> dict:
#     """Fetch the options list for exactly one pending slot."""

#     if slot == "branch":
#         if "hospitals" not in cache:
#             cache["hospitals"] = await fetch_hospitals(filled["city"])

#     elif slot == "department":
#         if "hospitals" not in cache:
#             cache["hospitals"] = await fetch_hospitals(filled["city"])
#         h_id = resolve_id(cache["hospitals"], filled["branch"])
#         cache["_hospital_id"] = h_id
#         if "departments" not in cache:
#             cache["departments"] = await fetch_departments(h_id)

#     elif slot == "doctor":
#         # Ensure we have hospital_id
#         if "_hospital_id" not in cache:
#             if "hospitals" not in cache:
#                 cache["hospitals"] = await fetch_hospitals(filled["city"])
#             cache["_hospital_id"] = resolve_id(cache["hospitals"], filled["branch"])
#         if "departments" not in cache:
#             cache["departments"] = await fetch_departments(cache["_hospital_id"])
#         d_id = resolve_id(cache["departments"], filled["department"])
#         cache["_department_id"] = d_id
#         if "doctors" not in cache:
#             cache["doctors"] = await fetch_doctors(d_id)

#     elif slot == "time_slot":
#         # Ensure we have doctor_id
#         if "_doctor_id" not in cache:
#             # Walk the chain if needed
#             if "_hospital_id" not in cache:
#                 if "hospitals" not in cache:
#                     cache["hospitals"] = await fetch_hospitals(filled["city"])
#                 cache["_hospital_id"] = resolve_id(cache["hospitals"], filled["branch"])
#             if "_department_id" not in cache:
#                 if "departments" not in cache:
#                     cache["departments"] = await fetch_departments(cache["_hospital_id"])
#                 cache["_department_id"] = resolve_id(cache["departments"], filled["department"])
#             if "doctors" not in cache:
#                 cache["doctors"] = await fetch_doctors(cache["_department_id"])
#             cache["_doctor_id"] = resolve_id(cache["doctors"], filled["doctor"])
#         if "slots" not in cache:
#             cache["slots"] = await fetch_time_slots(cache["_doctor_id"])

#     return cache


# async def _resolve_all_ids(filled: dict, cache: dict) -> dict:
#     """
#     Resolve every ID needed for POST /appointments.
#     Stores them in cache["resolved"].
#     """
#     if "hospitals" not in cache:
#         cache["hospitals"] = await fetch_hospitals(filled["city"])
#     hospital_id = resolve_id(cache["hospitals"], filled["branch"])

#     if "departments" not in cache:
#         cache["departments"] = await fetch_departments(hospital_id)
#     department_id = resolve_id(cache["departments"], filled["department"])

#     if "doctors" not in cache:
#         cache["doctors"] = await fetch_doctors(department_id)
#     doctor_id = resolve_id(cache["doctors"], filled["doctor"])

#     if "slots" not in cache:
#         cache["slots"] = await fetch_time_slots(doctor_id)
#     slot_id = resolve_id(cache["slots"], filled["time_slot"])

#     cache["resolved"] = {
#         "hospital_id":   hospital_id,
#         "department_id": department_id,
#         "doctor_id":     doctor_id,
#         "slot_id":       slot_id,
#     }
#     return cache

async def api_chain_node(state):
    pending = state.get("pending_slots", [])

    if not pending:
        return {}

    slot = pending[0]

    mock_options = {
        "branch": ["Saket", "Dwarka", "Rajouri Garden"],
        "department": ["Cardiology", "Orthopedic", "Dermatology"],
        "doctor": ["Dr A", "Dr B", "Dr C"],
        "time_slot": ["10 AM", "12 PM", "4 PM"]
    }

    return {
        "response": {
            "type": "slot_options",
            "slot": slot,
            "question": f"Select {slot}",
            "options": mock_options.get(slot, [])
        }
    }